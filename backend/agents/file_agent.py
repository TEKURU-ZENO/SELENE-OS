"""
SELENE OS — File Agent
Handles secure, sandboxed file operations.
Implements rollback tokens via .bak files for safe mutation.
"""

import os
import shutil
import uuid
from typing import Dict, Any, List
from schemas import ExecutionStatus, ExecutionReceipt, ExecutionContext, FilePermissionMode, RiskLevel
from tools.registry import tool_registry
import structlog

logger = structlog.get_logger(__name__)

# Sandbox configuration
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../workspace"))
os.makedirs(WORKSPACE_ROOT, exist_ok=True)


class SecurityViolation(Exception):
    pass


class FileAgent:
    """
    Agent responsible for safe file operations.
    """

    def __init__(self):
        self._register_tools()

    def _register_tools(self):
        tool_registry.register(
            name="file_read",
            description="Reads the contents of a file within the sandbox.",
            agent="file_agent",
            handler=self.read_file,
            risk_level=RiskLevel.LOW,
            parameters={"path": "str", "context": "ExecutionContext"}
        )
        
        tool_registry.register(
            name="file_write",
            description="Writes content to a file within the sandbox. Supports rollback.",
            agent="file_agent",
            handler=self.write_file,
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            rollback_supported=True,
            parameters={"path": "str", "content": "str", "context": "ExecutionContext"}
        )

    def _resolve_safe_path(self, relative_path: str) -> str:
        """Ensure the path resolves to within the WORKSPACE_ROOT sandbox."""
        # Strip leading slashes to prevent absolute path injection
        clean_path = relative_path.lstrip("/\\")
        abs_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, clean_path))
        
        if not abs_path.startswith(WORKSPACE_ROOT):
            logger.warning("sandbox_violation_attempt", requested_path=relative_path, resolved=abs_path)
            raise SecurityViolation("Path traversal denied. Access outside workspace is forbidden.")
            
        return abs_path

    async def read_file(self, path: str, context: ExecutionContext = None) -> ExecutionReceipt:
        """Reads a file securely."""
        import time
        start = time.time()
        
        try:
            safe_path = self._resolve_safe_path(path)
            
            if not os.path.exists(safe_path):
                raise FileNotFoundError(f"File not found: {path}")
                
            with open(safe_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return ExecutionReceipt(
                tool="file_read",
                status=ExecutionStatus.SUCCESS,
                duration_ms=(time.time() - start) * 1000,
                result=content,
                logs=[f"Successfully read {len(content)} bytes from {path}"]
            )
            
        except Exception as e:
            logger.error("file_read_error", path=path, error=str(e))
            return ExecutionReceipt(
                tool="file_read",
                status=ExecutionStatus.FAILED,
                duration_ms=(time.time() - start) * 1000,
                result=None,
                error_details=str(e)
            )

    async def write_file(self, path: str, content: str, context: ExecutionContext = None) -> ExecutionReceipt:
        """Writes a file securely with rollback support."""
        import time
        start = time.time()
        
        # Enforce file permission mode
        if context and context.file_permission_mode == FilePermissionMode.READ_ONLY:
            return ExecutionReceipt(
                tool="file_write",
                status=ExecutionStatus.FAILED,
                duration_ms=(time.time() - start) * 1000,
                result=None,
                error_details="Execution context enforces READ_ONLY mode. Write denied."
            )
            
        try:
            safe_path = self._resolve_safe_path(path)
            
            # Temporary handling if context demands it
            if context and context.file_permission_mode == FilePermissionMode.TEMP_ONLY:
                safe_path = safe_path + ".tmp"
            
            rollback_token = None
            logs = []
            
            # Create backup if file exists for rollback
            if os.path.exists(safe_path):
                rollback_token = f"rb_{uuid.uuid4().hex}"
                backup_path = f"{safe_path}.{rollback_token}.bak"
                shutil.copy2(safe_path, backup_path)
                logs.append(f"Created backup for rollback: {backup_path}")
            
            # Write new content
            os.makedirs(os.path.dirname(safe_path), exist_ok=True)
            with open(safe_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logs.append(f"Successfully wrote {len(content)} bytes to {path}")
                
            return ExecutionReceipt(
                tool="file_write",
                status=ExecutionStatus.SUCCESS,
                duration_ms=(time.time() - start) * 1000,
                result={"path": path, "bytes_written": len(content)},
                logs=logs,
                rollback_token=rollback_token
            )
            
        except Exception as e:
            logger.error("file_write_error", path=path, error=str(e))
            return ExecutionReceipt(
                tool="file_write",
                status=ExecutionStatus.FAILED,
                duration_ms=(time.time() - start) * 1000,
                result=None,
                error_details=str(e)
            )


# Instantiate to register tools
file_agent = FileAgent()
