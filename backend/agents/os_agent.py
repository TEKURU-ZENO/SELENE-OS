"""
SELENE OS — OS Agent
Handles safe system command execution via strict whitelisting.
NEVER allows arbitrary shell execution.
"""

import asyncio
import time
from typing import Dict, Any, List
from schemas import ExecutionStatus, ExecutionReceipt, ExecutionContext, RiskLevel, SafeCommand
from tools.registry import tool_registry
import structlog

logger = structlog.get_logger(__name__)


class OSAgent:
    """
    Agent responsible for highly restricted OS operations.
    Enforces strict mapping from generic capabilities to explicit binaries.
    """

    # The definitive whitelist of allowed commands.
    # Disallows shell injection (shell=False in subprocess)
    SAFE_COMMAND_MAP = {
        SafeCommand.RUN_GIT_STATUS: ["git", "status"],
        SafeCommand.RUN_TESTS: ["pytest"],
        # Add more explicit definitions here, not dynamic strings
    }

    def __init__(self):
        self._register_tools()

    def _register_tools(self):
        tool_registry.register(
            name="system_exec",
            description="Executes a pre-approved safe command.",
            agent="os_agent",
            handler=self.execute_safe_command,
            risk_level=RiskLevel.HIGH, # Still High Risk, requires confirmation
            requires_confirmation=True,
            parameters={"command_type": "SafeCommand", "context": "ExecutionContext"}
        )

    async def execute_safe_command(self, command_type: SafeCommand, context: ExecutionContext = None) -> ExecutionReceipt:
        start = time.time()
        
        # Verify the command is in the whitelist map
        if command_type not in self.SAFE_COMMAND_MAP:
            logger.error("unsafe_command_attempt", command=command_type.value)
            return ExecutionReceipt(
                tool="system_exec",
                status=ExecutionStatus.FAILED,
                duration_ms=(time.time() - start) * 1000,
                result=None,
                error_details=f"Command {command_type.value} is not authorized by the OS Agent policy."
            )

        cmd_args = self.SAFE_COMMAND_MAP[command_type]
        logs = [f"Executing safe command: {' '.join(cmd_args)}"]
        
        try:
            # shell=False is absolutely critical here
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            stdout_str = stdout.decode('utf-8').strip()
            stderr_str = stderr.decode('utf-8').strip()
            
            result_data = {
                "exit_code": process.returncode,
                "stdout": stdout_str,
                "stderr": stderr_str
            }
            
            status = ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.FAILED
            
            logs.append(f"Command exited with code {process.returncode}")
            
            return ExecutionReceipt(
                tool="system_exec",
                status=status,
                duration_ms=(time.time() - start) * 1000,
                result=result_data,
                logs=logs
            )
            
        except Exception as e:
            logger.error("os_agent_error", command=command_type.value, error=str(e))
            return ExecutionReceipt(
                tool="system_exec",
                status=ExecutionStatus.FAILED,
                duration_ms=(time.time() - start) * 1000,
                result=None,
                error_details=str(e)
            )


# Instantiate to register
os_agent = OSAgent()
