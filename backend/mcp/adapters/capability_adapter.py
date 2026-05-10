"""
SELENE OS — Capability Adapter
The Translation Brain. Completely isolates the Planner from knowing that MCP exists.
Abstract Capabilities go in -> Concrete, scored MCP tools come out.
"""

from typing import List, Optional, Dict, Any
from schemas import Capability
from mcp.registry.server_registry import server_registry
from mcp.adapters.scoring import scoring_engine
import structlog

logger = structlog.get_logger(__name__)

class CapabilityAdapter:
    
    def resolve_capability(self, capability: Capability, active_contexts: List[str]) -> Optional[Dict[str, Any]]:
        """
        Dynamically finds the best MCP tool for a requested Capability.
        """
        candidates = []
        
        # 1. Discover capabilities across all registered servers
        for manifest in server_registry.list_servers():
            if capability in manifest.capabilities:
                # Mock finding the specific tool descriptor on the server
                # In reality, this would query the registry for the specific MCPToolDescriptor
                candidates.append({
                    "server": manifest,
                    "tool_id": f"{manifest.server_id}_{capability.value}_impl" 
                })

        if not candidates:
            logger.warning("capability_unresolved", capability=capability.value)
            return None

        # 2. Score candidates adaptively
        scored_candidates = []
        for c in candidates:
            score = scoring_engine.evaluate_tool(
                tool_id=c["tool_id"], 
                descriptor=None, 
                manifest=c["server"], 
                active_context_types=active_contexts
            )
            scored_candidates.append({
                "candidate": c,
                "score": score
            })

        # 3. Sort by highest final score
        scored_candidates.sort(key=lambda x: x["score"].final_score, reverse=True)
        best_match = scored_candidates[0]

        logger.info(
            "capability_resolved", 
            capability=capability.value, 
            chosen_tool=best_match["candidate"]["tool_id"], 
            score=best_match["score"].final_score
        )

        return best_match["candidate"]

capability_adapter = CapabilityAdapter()
