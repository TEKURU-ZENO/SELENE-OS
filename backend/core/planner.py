"""
SELENE OS — Planner (Phase 8 Intelligence Layer)
Generates hierarchical ExecutionPlans strictly constrained to abstract Capabilities.
DOES NOT specify tools directly.
"""

import uuid
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from schemas import ExecutionPlan, ContextBundle, Capability
from services.llm_service import llm_service
import structlog

logger = structlog.get_logger(__name__)

# Constraint Layer injected into the prompt
DEFAULT_CONSTRAINTS = {
    "max_depth": 10,
    "allowed_capabilities": [c.value for c in Capability],
    "environment": "development"
}

class Planner:
    """
    The Executive Planner.
    Reasons in abstract capabilities, objective groups, and success criteria.
    """

    def __init__(self):
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Executive Planner for SELENE OS.
Your objective is to decompose the user's intent into a structured ExecutionPlan.

CRITICAL RULES:
1. You MUST generate hierarchical ObjectiveGroups, containing PlanNodes.
2. You MUST ONLY use the allowed abstract Capabilities. DO NOT invent tools.
3. Every PlanNode MUST define strict, machine-verifiable `success_criteria` (e.g. {{"type": "dom_contains", "expected": "Success"}}).
4. Identify explicit dependencies between nodes.
5. NEVER generate a graph depth exceeding the maximum constraints.

Current Constraints:
{constraints}

Recalled Memory Context:
Episodic: {episodic}
Semantic: {semantic}
Procedural: {procedural}

Repair Context (if this is a revision):
{repair_context}
"""),
            ("user", "Intent to plan: {user_query}")
        ])

    async def generate_plan(
        self, 
        user_query: str, 
        context_bundle: ContextBundle, 
        constraints: Dict[str, Any] = None,
        repair_context: Dict[str, Any] = None
    ) -> ExecutionPlan:
        """
        Generate a strictly structured DAG plan using Pydantic validation.
        """
        logger.info("planner_generating_dag", query=user_query[:30])
        
        active_constraints = constraints or DEFAULT_CONSTRAINTS
        repair_ctx = repair_context or "None (Initial Draft)"

        # Prepare prompt input
        prompt_input = {
            "user_query": user_query,
            "constraints": active_constraints,
            "episodic": context_bundle.episodic,
            "semantic": context_bundle.semantic,
            "procedural": context_bundle.procedural,
            "repair_context": repair_ctx
        }

        # Format prompt
        messages = self._prompt.format_messages(**prompt_input)
        
        # Convert to dictionary format expected by llm_service
        history = [{"role": msg.type, "content": msg.content} for msg in messages]

        # In a real Langchain integration we would use `.with_structured_output(ExecutionPlan)`
        # Here we instruct the LLM Service to use structured output
        
        # For MVP we simulate the LLM outputting the structured schema
        plan_dict = await llm_service.generate_structured(
            history=history,
            response_model=ExecutionPlan
        )
        
        # If llm_service just returned a mock dict, convert it to the object
        if isinstance(plan_dict, dict):
            # inject a plan_id to ensure validity
            if "plan_id" not in plan_dict:
                plan_dict["plan_id"] = str(uuid.uuid4())
            plan = ExecutionPlan.model_validate(plan_dict)
        else:
            plan = plan_dict

        logger.info("planner_dag_generated", plan_id=plan.plan_id, groups=len(plan.groups))
        return plan


# Singleton
planner_engine = Planner()
