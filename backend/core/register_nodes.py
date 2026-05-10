from .node_registry import node_registry
from .graph_nodes import (
    node_intent, node_context, node_planner, node_critic, 
    node_capability_resolution, node_execution, node_validation, 
    node_hitl, node_reflection, node_memory_update
)

# Register all nodes
node_registry.register("intent", node_intent)
node_registry.register("context", node_context)
node_registry.register("planner", node_planner)
node_registry.register("critic", node_critic)
node_registry.register("capability", node_capability_resolution)
node_registry.register("execute", node_execution)
node_registry.register("validation", node_validation)
node_registry.register("hitl", node_hitl)
node_registry.register("reflection", node_reflection)
node_registry.register("memory", node_memory_update)
