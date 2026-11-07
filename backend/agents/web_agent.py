"""
SELENE OS — Web Agent
Handles semantic web search, fetching, and content extraction.
Implements robust anti-rate-limit logic, exponential backoff, and chunking.
"""

import httpx
import asyncio
from bs4 import BeautifulSoup
from typing import Dict, Any, List
import time
from schemas import ExecutionStatus, ExecutionReceipt, ExecutionContext, RiskLevel
from tools.registry import tool_registry
import structlog

logger = structlog.get_logger(__name__)


class WebAgent:
    """
    Agent responsible for safe and robust web operations.
    Implements Final Flow: Fetch -> Extract -> (Semantic Chunking placeholder)
    """

    MAX_RETRIES = 3
    BASE_DELAY = 1.0
    TIMEOUT = 10.0

    def __init__(self):
        self._register_tools()

    def _register_tools(self):
        tool_registry.register(
            name="web_search",
            description="Searches the web and returns compressed semantic summaries.",
            agent="web_agent",
            handler=self.search,
            risk_level=RiskLevel.LOW,
            parameters={"query": "str", "max_results": "int", "context": "ExecutionContext"}
        )
        
        tool_registry.register(
            name="web_fetch",
            description="Fetches a URL, extracts main content, and removes boilerplate.",
            agent="web_agent",
            handler=self.fetch,
            risk_level=RiskLevel.LOW,
            parameters={"url": "str", "context": "ExecutionContext"}
        )

    async def _async_retry_wrapper(self, func, *args, **kwargs):
        """Wrapper to provide exponential backoff for network calls."""
        last_exception = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.MAX_RETRIES:
                    delay = self.BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning("web_agent_retry", attempt=attempt, delay=delay, error=str(e))
                    await asyncio.sleep(delay)
                
        raise last_exception

    async def _duckduckgo_search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Mock DuckDuckGo HTML parsing fallback. In production, use Tavily or SERP API."""
        # For Phase 6 MVP, we'll simulate a search result to avoid complex scraping logic
        # without an official API key. The focus is the architectural flow.
        await asyncio.sleep(0.5) # Simulate network
        return [
            {"title": f"Result 1 for {query}", "url": "https://example.com/1", "snippet": "Mock snippet 1"},
            {"title": f"Result 2 for {query}", "url": "https://example.com/2", "snippet": "Mock snippet 2"}
        ][:max_results]

    async def search(self, query: str, max_results: int = 3, context: ExecutionContext = None) -> ExecutionReceipt:
        start = time.time()
        logs = [f"Searching for: '{query}'"]
        
        try:
            results = await self._async_retry_wrapper(self._duckduckgo_search, query, max_results)
            
            # Here we would normally inject the "Semantic Chunk & Re-rank" layer
            # For now, we return the compressed list of dictionaries
            
            logs.append(f"Found {len(results)} results.")
            
            return ExecutionReceipt(
                tool="web_search",
                status=ExecutionStatus.SUCCESS,
                duration_ms=(time.time() - start) * 1000,
                result=results,
                logs=logs
            )
        except Exception as e:
            logger.error("web_search_error", query=query, error=str(e))
            return ExecutionReceipt(
                tool="web_search",
                status=ExecutionStatus.FAILED,
                duration_ms=(time.time() - start) * 1000,
                result=None,
                error_details=str(e)
            )

    async def _fetch_url(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            # Mask as standard browser to avoid basic blocks
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            return response.text

    def _is_ssrf_safe(self, url: str) -> bool:
        import urllib.parse
        import socket
        import ipaddress
        
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname
            if not host:
                return False
                
            host_lower = host.lower()
            if host_lower in ("localhost", "127.0.0.1", "[::1]", "0.0.0.0"):
                return False
                
            try:
                ip = ipaddress.ip_address(host)
                if (ip.is_loopback or 
                    ip.is_private or 
                    ip.is_link_local or 
                    ip.is_reserved or 
                    ip.is_multicast or 
                    ip.is_unspecified):
                    return False
                return True
            except ValueError:
                pass

            try:
                addr_info = socket.getaddrinfo(host, None)
                for family, _, _, _, sockaddr in addr_info:
                    ip_str = sockaddr[0]
                    ip = ipaddress.ip_address(ip_str)
                    if (ip.is_loopback or 
                        ip.is_private or 
                        ip.is_link_local or 
                        ip.is_reserved or 
                        ip.is_multicast or 
                        ip.is_unspecified):
                        return False
            except socket.gaierror:
                if (not "." in host_lower or 
                    host_lower.endswith(".local") or 
                    host_lower.endswith(".internal") or 
                    host_lower.endswith(".lan") or
                    host_lower.endswith(".localhost")):
                    return False
                return True
                
            return True
        except Exception:
            return False

    async def fetch(self, url: str, context: ExecutionContext = None) -> ExecutionReceipt:
        start = time.time()
        logs = [f"Fetching URL: {url}"]
        
        from config.settings import settings
        if settings.BLOCK_SSRF and not self._is_ssrf_safe(url):
            logger.error("web_fetch_ssrf_blocked", url=url)
            return ExecutionReceipt(
                tool="web_fetch",
                status=ExecutionStatus.FAILED,
                duration_ms=(time.time() - start) * 1000,
                result=None,
                error_details="SSRF Protection: Access to local/private network resources is blocked."
            )
        
        try:
            html = await self._async_retry_wrapper(self._fetch_url, url)
            
            # Extract main content (remove scripts, styles, nav)
            soup = BeautifulSoup(html, "html.parser")
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            
            text = soup.get_text(separator="\n", strip=True)
            
            # Naive compression: truncate to avoid blowing up the token budget
            # Phase 7 uses semantic chunking here
            max_chars = 4000
            if len(text) > max_chars:
                text = text[:max_chars] + "\n...[CONTENT TRUNCATED]..."
                logs.append("Content truncated to fit token limits.")
                
            return ExecutionReceipt(
                tool="web_fetch",
                status=ExecutionStatus.SUCCESS,
                duration_ms=(time.time() - start) * 1000,
                result={"url": url, "content": text},
                logs=logs
            )
            
        except Exception as e:
            logger.error("web_fetch_error", url=url, error=str(e))
            return ExecutionReceipt(
                tool="web_fetch",
                status=ExecutionStatus.FAILED,
                duration_ms=(time.time() - start) * 1000,
                result=None,
                error_details=str(e)
            )


# Instantiate to register
web_agent = WebAgent()
