# Plugin Sandbox System

## Overview

The SELENE OS Execution Sandbox (Layer 7) provides a secure, isolated environment for the AI agent to execute arbitrary code, run terminal commands, and perform file operations. It is designed around a dual-tier architecture: an **E2B cloud microVM** as the primary secure sandbox, with a **local subprocess fallback** for lightweight or offline execution.

This document outlines the architecture, configuration, security model, and integration of plugins into the SELENE Sandbox.

---

## Architecture: E2B MicroVM + Local Fallback

### E2B MicroVM (Primary Sandbox)
E2B provides instantly booting, firewalled microVMs tailored for AI agents. 
- **Isolation:** Complete network and filesystem isolation from the host OS.
- **Environment:** Pre-configured with Python, Node, and essential build tools.
- **Connectivity:** Securely streamed stdin/stdout via WebSocket to SELENE Layer 7.

### Local Subprocess (Fallback)
If the E2B API is unreachable, or for strictly local deployments without cloud access, SELENE gracefully degrades to a managed local subprocess wrapper.
- **Mechanism:** Python `subprocess.run` with strict timeouts.
- **Limitations:** Runs on the host OS. Relies entirely on Layer 8 (Governance) for safety.

---

## Registering Plugins (Capabilities)

Plugins define actionable tools that the Planner (Layer 4) can invoke. They are categorized by capability type:

1. `WEB_SEARCH`: Scrapes or searches external endpoints.
2. `EXECUTE_CODE`: Runs arbitrary scripts (Python, JS, Bash).
3. `FILE_OPERATION`: Reads/writes files to the workspace.
4. `API_CALL`: Makes structured REST/GraphQL requests.

Plugins are registered in the global registry inside `backend/governance/plugin_sandbox.py`.

---

## E2B Integration Details

To use E2B, you must configure your environment:

1. **Configuration:** Set the `E2B_API_KEY` in your `.env` or system environment variables.
2. **Sandbox Creation:** When `execute_node` in LangGraph triggers, `plugin_sandbox.py` initializes a `Sandbox` instance via the E2B SDK.
3. **Execution:** Code strings or terminal commands are transmitted to the E2B instance.
4. **Timeout Handling:** E2B executions enforce a strict 60-second limit by default to prevent hanging processes.

```python
# Snippet from backend/governance/plugin_sandbox.py
from e2b import Sandbox

def execute_in_cloud(code: str, env_vars: dict = None):
    with Sandbox(api_key=os.getenv("E2B_API_KEY")) as sandbox:
        process = sandbox.process.start(f"python -c '{code}'")
        process.wait(timeout=60)
        return process.stdout, process.stderr
```

---

## Local Fallback Details

If `E2B_API_KEY` is not present, the `LocalSandboxFallback` class is utilized.

- **Timeout:** Defaults to 30 seconds.
- **Capture:** `stdout` and `stderr` are buffered and returned as strings.
- **Security Context:** Runs with the same user privileges as the FastAPI backend.

```python
import subprocess

def execute_locally(cmd: list):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            shell=False # Enforced by governance
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Execution timed out after 30 seconds."
```

---

## Security Model

Layer 8 (Governance) strictly monitors all sandbox inputs, acting as an interceptor before execution:

1. **No `shell=True`:** The local fallback actively prevents the use of `shell=True` in subprocesses to mitigate shell injection attacks.
2. **Command Blocking:** A blacklist of dangerous commands (e.g., `rm -rf`, `mkfs`, `reboot`) is evaluated via regex before execution.
3. **SSRF Protection:** External URLs requested by plugins are checked against a blocklist of internal CIDR ranges (e.g., `169.254.169.254`, `127.0.0.1`) to prevent Server-Side Request Forgery against cloud metadata APIs.
4. **HITL (Human-In-The-Loop) Lock:** High-risk operations (e.g., database drops) trigger a `mutation lock`, pausing the LangGraph state machine until user approval is received via the WebSocket API.

---

## Writing Custom Plugins

You can extend SELENE's capabilities by writing custom plugins. A plugin is essentially a Python class that inherits from `BaseCapability`.

```python
from pydantic import BaseModel
from backend.core.plugin_sandbox import BaseCapability

class LogAnalyzerPlugin(BaseCapability):
    name = "log_analyzer"
    capability_type = "FILE_OPERATION"
    description = "Analyzes server logs for error patterns."
    
    class InputSchema(BaseModel):
        log_path: str
        pattern: str
        
    def execute(self, inputs: InputSchema, sandbox_env: SandboxEnvironment) -> str:
        # Implementation logic goes here
        # E.g. grep the file via sandbox_env.run_cmd(...)
        return "Found 12 matches."
```

---

## Plugin Lifecycle

1. **Register:** Plugin is loaded into the registry at FastAPI startup.
2. **Validate:** Planner matches a step to the plugin; schemas are validated via Pydantic.
3. **Execute:** The plugin runs its logic in either E2B or the local fallback.
4. **Cleanup:** Sandboxes are terminated, temporary files are scrubbed, and the Orchestrator resumes the graph state.

---

## Code References

- **Core Sandbox Logic:** `backend/governance/plugin_sandbox.py`
- **Safety Enforcement:** `backend/governance/safety.py`
- **LangGraph Integration:** `backend/core/graph_nodes.py` (specifically `execute_node`)
