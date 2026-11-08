"""
SELENE OS — Research Workflow Pack v1
A reusable cognitive workflow for deep research tasks.
Gathers information from multiple sources, synthesizes findings,
and drafts a structured report — all with governance-enforced HITL
before any external writes (e.g., drafting to Notion).
"""

from typing import Dict, Any, List
from schemas import (
    SharedCognitiveWorkflow, OrganizationalMemoryTier,
    Capability, ExecutionCheckpoint, RiskLevel
)
import structlog

logger = structlog.get_logger(__name__)


def get_research_workflow() -> SharedCognitiveWorkflow:
    """
    Returns the Research Workflow pack.
    Triggered when the user provides a research question or asks SELENE
    to investigate a topic, technology, or decision space.
    """
    return SharedCognitiveWorkflow(
        name="Research Workflow v1",
        author="system",
        target_tier=OrganizationalMemoryTier.TEAM,

        # ── 1. The Planning Template (The "What") ──────────────
        planning_template={
            "objective": "Decompose a research question into sub-questions, gather diverse sources, and synthesize a structured report.",
            "expected_capabilities": [
                Capability.FIND_INFORMATION, # Web search, documentation lookup
                Capability.READ_DOCUMENT,    # Read papers, articles, docs (Notion read-only)
                Capability.PLUGIN_CAPABILITY # Draft report to Notion (HITL-gated, beta only)
            ],
            "default_nodes": [
                {
                    "step": "Decompose Question",
                    "action": "Break the research objective into 3-5 specific sub-questions that, when answered, fully address the objective."
                },
                {
                    "step": "Gather Primary Sources",
                    "action": "Search for authoritative sources for each sub-question. Prioritize official documentation and peer-reviewed content."
                },
                {
                    "step": "Gather Secondary Sources",
                    "action": "Find community perspectives, case studies, and practical examples that complement primary sources."
                },
                {
                    "step": "Identify Contradictions",
                    "action": "Flag where sources disagree or where the evidence is ambiguous. Do not resolve contradictions autonomously."
                },
                {
                    "step": "Synthesize Findings",
                    "action": "Draft a structured report with: Summary, Key Findings (per sub-question), Evidence Quality Assessment, Open Questions, and Recommended Actions."
                },
            ]
        },

        # ── 2. HITL Checkpoints ────────────────────────────────
        hitl_checkpoints=[
            "before_finalizing_source_list",    # User validates sources before deep read
            "before_drafting_report",            # User reviews findings before synthesis
            "before_writing_to_notion",          # All external writes require approval (beta)
        ],

        # ── 3. Reflection Policies ─────────────────────────────
        reflection_policies={
            "focus_areas": [
                "Were the sources sufficiently diverse and authoritative?",
                "Did the synthesis faithfully represent source positions without ungrounded claims or drift?",
                "Were contradictions correctly identified and presented to the user?",
                "Did the user add significant new sources not found by SELENE?"
            ],
            "procedural_update_threshold": 0.80
        },

        # ── 4. Telemetry ───────────────────────────────────────
        telemetry_expectations=[
            "source_diversity_score",
            "user_source_addition_rate",
            "report_hitl_modification_rate",
            "time_to_synthesis",
        ]
    )
