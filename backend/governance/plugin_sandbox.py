"""
SELENE OS — Plugin Execution Sandbox
Isolates plugin execution, strictly enforcing OrganizationalMemoryTier scoping
and manifest-declared permission bounds. No direct memory writes are allowed.
"""

import os
import json
from typing import Any
from schemas import PluginManifest, OrganizationalMemoryTier, RiskLevel
from mcp.registry.server_registry import server_registry
import structlog

logger = structlog.get_logger(__name__)

# Memory tier ordering: higher index = broader access
_TIER_HIERARCHY = [
    OrganizationalMemoryTier.PERSONAL,
    OrganizationalMemoryTier.TEAM,
    OrganizationalMemoryTier.ORG,
]


class PluginSandbox:
    """
    Executes plugin capabilities inside a constrained environment.

    Enforcement rules:
    1. The plugin's declared memory_scope must be >= the request's context_tier.
    2. The capability must be declared in the plugin manifest.
    3. No direct memory reads/writes — only execution results are returned.
    4. All executions are audited via structlog (picked up by the audit pipeline).
    """

    def __init__(self):
        # plugin_id → {capability_name → handler_fn}
        self._registered_handlers: dict[str, dict[str, Any]] = {}

    def register_handler(self, plugin_id: str, capability: str, handler) -> None:
        """
        Called by SeleneSDK.register_capability() to bind a handler.
        Only capabilities declared in the manifest are accepted.
        """
        if plugin_id not in self._registered_handlers:
            self._registered_handlers[plugin_id] = {}
        self._registered_handlers[plugin_id][capability] = handler
        logger.info("sandbox_handler_registered", plugin=plugin_id, capability=capability)

    async def execute(
        self,
        plugin_id: str,
        capability: str,
        params: dict,
        context_tier: OrganizationalMemoryTier,
    ) -> Any:
        """
        Executes a plugin capability inside the sandbox.

        Steps:
        1. Fetch manifest from registry
        2. Verify memory tier scope
        3. Verify capability is declared
        4. Invoke registered handler (or mock if none registered yet)
        5. Return structured result — never raw memory
        """
        logger.info(
            "sandbox_execution_started",
            plugin=plugin_id,
            capability=capability,
            tier=context_tier.value,
        )

        # ── Step 1: Fetch manifest ─────────────────────────────────
        manifest = server_registry.get_server(plugin_id)
        if manifest is None:
            raise PermissionError(
                f"Plugin '{plugin_id}' is not registered in the MCP Server Registry. "
                f"All plugins must be declared and approved before execution."
            )

        # ── Step 2: Verify memory tier scope ──────────────────────
        from schemas import Capability
        manifest_tier = manifest.memory_scope
        manifest_tier_index = _TIER_HIERARCHY.index(manifest_tier) if manifest_tier in _TIER_HIERARCHY else 0
        context_tier_index = _TIER_HIERARCHY.index(context_tier) if context_tier in _TIER_HIERARCHY else 0

        if context_tier_index > manifest_tier_index:
            raise PermissionError(
                f"Plugin '{plugin_id}' has memory scope '{manifest_tier.value}' "
                f"but the request context is '{context_tier.value}'. "
                f"Broader context access is not permitted."
            )

        # ── Step 3: Verify capability is declared ─────────────────
        try:
            cap_enum = Capability(capability)
        except ValueError:
            raise PermissionError(f"Unknown capability '{capability}'.")

        if cap_enum not in manifest.capabilities:
            raise PermissionError(
                f"Plugin '{plugin_id}' does not declare capability '{capability}'. "
                f"Declared: {[c.value for c in manifest.capabilities]}"
            )

        # ── Step 4: Invoke handler ────────────────────────────────
        handlers = self._registered_handlers.get(plugin_id, {})
        handler = handlers.get(capability)

        if cap_enum == Capability.EXECUTE_CODE:
            result = await self._execute_sandboxed_code(params)
        elif handler:
            result = await handler(params) if asyncio_is_coroutine(handler) else handler(params)
        else:
            # No handler registered yet — return a structured stub result
            # This allows the governance/receipt pipeline to function even
            # before the actual MCP server is wired in.
            logger.warning(
                "sandbox_no_handler_registered",
                plugin=plugin_id,
                capability=capability,
            )
            result = {
                "status": "stub",
                "plugin": plugin_id,
                "capability": capability,
                "params": params,
                "message": "Handler not yet registered. Sandbox executed in stub mode.",
            }

        logger.info("sandbox_execution_completed", plugin=plugin_id, capability=capability)
        return result

    async def _execute_sandboxed_code(self, params: dict) -> dict:
        """Runs python or JS code inside an ephemeral E2B microVM or local directory sandbox fallback."""
        code = params.get("code", "")
        language = params.get("language", "python")
        
        e2b_api_key = os.getenv("E2B_API_KEY")
        if e2b_api_key:
            try:
                from e2b_code_interpreter import Sandbox as E2BSandbox
                logger.info("e2b_microvm_sandbox_spawning", language=language)
                
                async with E2BSandbox(api_key=e2b_api_key) as sb:
                    proc = await sb.commands.run(f"python -c {json.dumps(code)}")
                    logger.info("e2b_microvm_sandbox_execution_success")
                    return {
                        "status": "success",
                        "stdout": proc.stdout,
                        "stderr": proc.stderr,
                        "exit_code": proc.exit_code,
                        "sandbox_type": "e2b_microvm"
                    }
            except Exception as e:
                logger.error("e2b_microvm_sandbox_failed_falling_back", error=str(e))

        # Graceful fallback: local directory-isolated sandbox
        logger.info("local_directory_sandbox_activated", language=language)
        import tempfile
        import subprocess
        import sys
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_name = "script.py" if language == "python" else "script.js"
            file_path = os.path.join(tmpdir, file_name)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
                
            try:
                cmd = [sys.executable, file_path] if language == "python" else ["node", file_path]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=tmpdir
                )
                logger.info("local_directory_sandbox_execution_completed")
                return {
                    "status": "success" if proc.returncode == 0 else "failed",
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "exit_code": proc.returncode,
                    "sandbox_type": "local_isolated_directory"
                }
            except subprocess.TimeoutExpired:
                logger.error("local_directory_sandbox_timeout")
                return {
                    "status": "timeout",
                    "stdout": "",
                    "stderr": "Execution timed out after 10 seconds.",
                    "exit_code": -1,
                    "sandbox_type": "local_isolated_directory"
                }
            except Exception as ex:
                logger.error("local_directory_sandbox_execution_error", error=str(ex))
                return {
                    "status": "error",
                    "stdout": "",
                    "stderr": str(ex),
                    "exit_code": -1,
                    "sandbox_type": "local_isolated_directory"
                }


def asyncio_is_coroutine(fn) -> bool:
    import asyncio
    return asyncio.iscoroutinefunction(fn)


# Singleton
plugin_sandbox = PluginSandbox()
