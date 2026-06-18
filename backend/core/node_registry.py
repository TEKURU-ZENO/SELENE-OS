"""
SELENE OS — Node Registry
Allows hot-swappable orchestration, experimentation, and plugin nodes.
"""

from typing import Callable, Dict
import structlog

logger = structlog.get_logger(__name__)


class NodeRegistry:
    def __init__(self):
        self._nodes: Dict[str, Callable] = {}

    def register(self, name: str, node_func: Callable) -> None:
        self._nodes[name] = node_func
        logger.debug("graph_node_registered", node_name=name)

    def get(self, name: str) -> Callable:
        func = self._nodes.get(name)
        if not func:
            raise ValueError(f"Node '{name}' not found in registry.")
        return func

# Singleton
node_registry = NodeRegistry()
