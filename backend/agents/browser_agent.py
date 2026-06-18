"""
SELENE OS — Browser Agent
The flagship execution agent.
Implements Playwright with DOM snapshotting, interaction verification, and DOM memory cache.
"""

import asyncio
import os
import time
import uuid
from typing import Dict, Any, List, Optional
from schemas import ExecutionStatus, ExecutionReceipt, ExecutionContext, RiskLevel
from tools.registry import tool_registry
import structlog

logger = structlog.get_logger(__name__)

ARTIFACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../workspace/artifacts"))
os.makedirs(ARTIFACTS_DIR, exist_ok=True)


class BrowserAgent:
    """
    Playwright-powered browser automation.
    Implements mandatory DOM verification before and after actions.
    """

    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None
        self._dom_cache: Dict[str, Any] = {} # Caches recent DOM trees and selectors
        self._register_tools()

    def _register_tools(self):
        tool_registry.register(
            name="browser_navigate",
            description="Navigates the browser to a URL and captures a DOM snapshot.",
            agent="browser_agent",
            handler=self.navigate,
            risk_level=RiskLevel.LOW,
            parameters={"url": "str", "context": "ExecutionContext"}
        )
        
        tool_registry.register(
            name="browser_click",
            description="Verifies an element exists, clicks it, and verifies state change.",
            agent="browser_agent",
            handler=self.click,
            risk_level=RiskLevel.MEDIUM,
            parameters={"selector": "str", "context": "ExecutionContext"}
        )

    async def _ensure_browser(self):
        """Lazy initialization of the Playwright browser."""
        if not self._browser:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            self._context = await self._browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
            )
            self._page = await self._context.new_page()
            logger.info("browser_initialized")

    async def _capture_dom_state(self, action_name: str) -> str:
        """
        Takes a screenshot and caches the DOM state.
        Crucial for anti-hallucination and receipt artifacts.
        """
        await self._ensure_browser()
        
        timestamp = int(time.time() * 1000)
        screenshot_path = os.path.join(ARTIFACTS_DIR, f"snapshot_{action_name}_{timestamp}.png")
        
        await self._page.screenshot(path=screenshot_path)
        
        # In a full implementation, we'd extract the accessibility tree here
        # For MVP, we cache the HTML length as a basic state hash
        html = await self._page.content()
        self._dom_cache["current_state"] = len(html)
        
        logger.debug("dom_state_captured", path=screenshot_path)
        return screenshot_path

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
                return False
                
            return True
        except Exception:
            return False

    async def navigate(self, url: str, context: ExecutionContext = None) -> ExecutionReceipt:
        start = time.time()
        logs = [f"Navigating to {url}"]
        artifacts = []
        
        from config.settings import settings
        if settings.BLOCK_SSRF and not self._is_ssrf_safe(url):
            logger.error("browser_navigate_ssrf_blocked", url=url)
            return ExecutionReceipt(
                tool="browser_navigate",
                status=ExecutionStatus.FAILED,
                duration_ms=(time.time() - start) * 1000,
                result=None,
                artifacts=artifacts,
                error_details="SSRF Protection: Access to local/private network resources is blocked."
            )
        
        try:
            await self._ensure_browser()
            await self._page.goto(url, wait_until="networkidle")
            
            # Post-action verification
            screenshot = await self._capture_dom_state("navigate")
            artifacts.append(screenshot)
            logs.append(f"Navigation successful. Page title: {await self._page.title()}")
            
            return ExecutionReceipt(
                tool="browser_navigate",
                status=ExecutionStatus.SUCCESS,
                duration_ms=(time.time() - start) * 1000,
                result={"url": url, "title": await self._page.title()},
                artifacts=artifacts,
                logs=logs
            )
            
        except Exception as e:
            logger.error("browser_navigate_error", url=url, error=str(e))
            if self._page:
                err_screenshot = await self._capture_dom_state("error_navigate")
                artifacts.append(err_screenshot)
                
            return ExecutionReceipt(
                tool="browser_navigate",
                status=ExecutionStatus.FAILED,
                duration_ms=(time.time() - start) * 1000,
                result=None,
                artifacts=artifacts,
                error_details=str(e)
            )

    async def click(self, selector: str, context: ExecutionContext = None) -> ExecutionReceipt:
        """
        Implements strict Interaction Verification.
        """
        start = time.time()
        logs = [f"Attempting to click: {selector}"]
        artifacts = []
        
        try:
            await self._ensure_browser()
            
            # 1. Pre-click verification
            element = self._page.locator(selector).first
            
            # Ensure it's visible and interactable before proceeding
            is_visible = await element.is_visible(timeout=3000)
            if not is_visible:
                raise ValueError(f"Element {selector} is not visible in the DOM.")
                
            logs.append("Element verified visible and interactable.")
            
            # Capture state before
            pre_screenshot = await self._capture_dom_state("pre_click")
            artifacts.append(pre_screenshot)
            pre_state = self._dom_cache.get("current_state")
            
            # 2. Action
            await element.click()
            await self._page.wait_for_load_state("domcontentloaded")
            
            # 3. Post-click verification
            post_screenshot = await self._capture_dom_state("post_click")
            artifacts.append(post_screenshot)
            post_state = self._dom_cache.get("current_state")
            
            state_changed = pre_state != post_state
            if state_changed:
                logs.append("State change verified after click.")
            else:
                logs.append("Warning: No significant DOM state change detected after click.")
                
            return ExecutionReceipt(
                tool="browser_click",
                status=ExecutionStatus.SUCCESS,
                duration_ms=(time.time() - start) * 1000,
                result={"selector": selector, "state_changed": state_changed},
                artifacts=artifacts,
                logs=logs
            )
            
        except Exception as e:
            logger.error("browser_click_error", selector=selector, error=str(e))
            if self._page:
                err_screenshot = await self._capture_dom_state("error_click")
                artifacts.append(err_screenshot)
                
            return ExecutionReceipt(
                tool="browser_click",
                status=ExecutionStatus.FAILED,
                duration_ms=(time.time() - start) * 1000,
                result=None,
                artifacts=artifacts,
                error_details=str(e)
            )


# Instantiate to register
browser_agent = BrowserAgent()
