"""
SELENE OS — Stdio MCP Transport
Concrete transport that spawns an MCP server subprocess and communicates
via JSON-RPC 2.0 over stdin/stdout. This is the primary transport for
local MCP servers (GitHub, VSCode, Filesystem).
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from mcp.transport.base_transport import BaseTransport
import structlog

logger = structlog.get_logger(__name__)


class StdioTransport(BaseTransport):
    """
    Subprocess-based MCP transport. Spawns a server process and communicates
    via newline-delimited JSON-RPC over its stdin/stdout pipes.
    """

    def __init__(self, command: list[str], env: Optional[Dict[str, str]] = None):
        """
        Args:
            command: The command to spawn the MCP server process.
                     Example: ["npx", "-y", "@modelcontextprotocol/server-github"]
            env:     Optional environment variables for the subprocess.
        """
        self._command = command
        self._env = env
        self._process: Optional[asyncio.subprocess.Process] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        """Spawns the MCP server subprocess and starts the reader loop."""
        try:
            self._process = await asyncio.create_subprocess_exec(
                *self._command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._env,
            )
            # Start background reader loop
            self._reader_task = asyncio.create_task(self._reader_loop())
            logger.info("stdio_transport_connected", command=self._command[0], pid=self._process.pid)
            return True
        except FileNotFoundError:
            logger.error("stdio_transport_command_not_found", command=self._command)
            return False
        except Exception as e:
            logger.error("stdio_transport_connect_failed", error=str(e))
            return False

    async def disconnect(self) -> None:
        """Terminates the subprocess and cancels the reader loop."""
        if self._reader_task:
            self._reader_task.cancel()
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
        logger.info("stdio_transport_disconnected")

    async def send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends a JSON-RPC request and awaits the response.
        Uses a per-request asyncio.Future for correlation.
        """
        if not self._process or self._process.returncode is not None:
            raise ConnectionError("StdioTransport: process not running")

        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        line = json.dumps(payload) + "\n"
        self._process.stdin.write(line.encode())
        await self._process.stdin.drain()

        logger.debug("stdio_request_sent", method=method, request_id=request_id)

        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            logger.error("stdio_request_timeout", method=method, request_id=request_id)
            raise TimeoutError(f"MCP request '{method}' timed out after 30s")

    async def emit_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Fire-and-forget: no response expected."""
        if not self._process or self._process.returncode is not None:
            return

        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        line = json.dumps(payload) + "\n"
        self._process.stdin.write(line.encode())
        await self._process.stdin.drain()

    async def _reader_loop(self) -> None:
        """Background task: reads newline-delimited JSON from the subprocess stdout."""
        try:
            while self._process and self._process.returncode is None:
                raw_line = await self._process.stdout.readline()
                if not raw_line:
                    break

                line = raw_line.decode().strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("stdio_invalid_json", raw=line[:200])
                    continue

                request_id = message.get("id")
                if request_id and request_id in self._pending_requests:
                    future = self._pending_requests.pop(request_id)
                    if "error" in message:
                        future.set_exception(
                            RuntimeError(f"MCP Error: {message['error']}")
                        )
                    else:
                        future.set_result(message.get("result", {}))
                else:
                    # Unsolicited notification from server
                    logger.debug("stdio_server_notification", method=message.get("method"))

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("stdio_reader_loop_error", error=str(e))
            # Resolve all pending futures with the error
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(e)
            self._pending_requests.clear()
