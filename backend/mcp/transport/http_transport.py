"""
SELENE OS — HTTP MCP Transport
Concrete transport for MCP servers exposed over HTTP/REST.
Used as the secondary transport and for remote MCP servers.
"""

import httpx
import json
from typing import Dict, Any
from mcp.transport.base_transport import BaseTransport
import structlog

logger = structlog.get_logger(__name__)


class HttpTransport(BaseTransport):
    """
    HTTP-based MCP transport. Sends JSON-RPC requests as HTTP POST to the
    MCP server's base URL. Uses httpx for async HTTP with connection pooling.
    """

    def __init__(self, base_url: str, headers: Dict[str, str] | None = None, timeout: int = 30):
        """
        Args:
            base_url: Root URL of the MCP HTTP server (e.g., "http://localhost:9000")
            headers:  Optional auth headers (Authorization, X-API-Key, etc.)
            timeout:  Request timeout in seconds (default 30)
        """
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> bool:
        """Creates the httpx client and validates connectivity with a health ping."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                **self._headers,
            },
            timeout=self._timeout,
        )
        try:
            resp = await self._client.get("/health")
            ok = resp.status_code < 400
            if ok:
                logger.info("http_transport_connected", base_url=self._base_url)
            else:
                logger.warning("http_transport_health_failed", status=resp.status_code)
            return ok
        except httpx.ConnectError:
            logger.error("http_transport_unreachable", base_url=self._base_url)
            return False
        except Exception as e:
            logger.error("http_transport_connect_error", error=str(e))
            return False

    async def disconnect(self) -> None:
        """Closes the httpx client connection pool."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("http_transport_disconnected", base_url=self._base_url)

    async def send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends a JSON-RPC 2.0 POST request to /rpc and returns the result.
        Raises on HTTP errors or JSON-RPC error responses.
        """
        if not self._client:
            raise ConnectionError("HttpTransport: client not connected")

        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": method,
            "params": params,
        }

        try:
            response = await self._client.post("/rpc", json=payload)
            response.raise_for_status()
        except httpx.TimeoutException:
            logger.error("http_request_timeout", method=method, url=self._base_url)
            raise TimeoutError(f"MCP HTTP request '{method}' timed out")
        except httpx.HTTPStatusError as e:
            logger.error("http_request_status_error", method=method, status=e.response.status_code)
            raise RuntimeError(f"MCP HTTP {e.response.status_code}: {e.response.text[:200]}")

        data = response.json()
        if "error" in data:
            error = data["error"]
            logger.error("http_mcp_error", method=method, error=error)
            raise RuntimeError(f"MCP Error {error.get('code')}: {error.get('message')}")

        logger.debug("http_request_success", method=method)
        return data.get("result", {})

    async def emit_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Fire-and-forget POST — no response body expected."""
        if not self._client:
            return
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        try:
            await self._client.post("/notify", json=payload)
        except Exception as e:
            logger.warning("http_notification_failed", method=method, error=str(e))
