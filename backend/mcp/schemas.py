"""
SELENE OS — MCP Contracts & Schemas
Defines the strict boundaries and legal contracts for external MCP servers.
"""

from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Any, Optional
from enum import Enum
from schemas import Capability, RiskLevel, OrganizationalMemoryTier

class TransportType(str, Enum):
    STDIO = "stdio"
    WEBSOCKET = "websocket"
    HTTP = "http"

class TrustClassification(str, Enum):
    VERIFIED_SAFE = "verified_safe"  # audited + low-risk
    TRUSTED = "trusted"              # approved internal
    RESTRICTED = "restricted"        # limited contexts
    EXPERIMENTAL = "experimental"    # isolated only
    BLOCKED = "blocked"              # denied

class ExecutionMode(str, Enum):
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"

class MCPServerManifest(BaseModel):
    """The foundational contract for any MCP server connecting to SELENE."""
    server_id: str
    name: str
    version: str

    transport: TransportType

    capabilities: List[Capability]

    trust_classification: TrustClassification

    risk_level: RiskLevel

    memory_scope: OrganizationalMemoryTier

    allowed_contexts: List[str]

    requires_hitl: bool

    supports_replay: bool = True
    
    supports_idempotency: bool = False

    enabled: bool = True


class MCPToolDescriptor(BaseModel):
    """Normalizes the tools exposed by the MCP server into SELENE capabilities."""
    tool_name: str

    capability: Capability

    input_schema: Dict[str, Any]

    output_schema: Dict[str, Any]

    requires_confirmation: bool

    execution_mode: ExecutionMode

    timeout_seconds: int = 30
