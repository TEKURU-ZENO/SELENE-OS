"""
SELENE OS — Debugging Workflow Pack v1
A reusable cognitive workflow for systematic debugging sessions.
Bridges VSCode diagnostics, GitHub context, and code execution
to reduce debugging cognitive load without reducing agency.
"""

from typing import Dict, Any, List
from schemas import (
    SharedCognitiveWorkflow, OrganizationalMemoryTier,
    Capability, ExecutionCheckpoint, RiskLevel
)
import structlog

logger = structlog.get_logger(__name__)


def get_debugging_workflow() -> SharedCognitiveWorkflow:
    """
    Returns the Debugging Workflow pack.
    Triggered when SELENE detects a 'diagnostics_present' context signal
    from the VSCode connector or when the user asks to debug something.
    """
    return SharedCognitiveWorkflow(
        name="Debugging Workflow v1",
        author="system",
        target_tier=OrganizationalMemoryTier.PERSONAL,

        # ── 1. The Planning Template (The "What") ──────────────
        planning_template={
            "objective": "Systematically diagnose and propose a fix for a reported error or failing test.",
            "expected_capabilities": [
                Capability.READ_DOCUMENT,    # Read stack traces, error logs, source files
                Capability.FIND_INFORMATION, # Search for similar issues, documentation
                Capability.EXECUTE_CODE,     # Run failing test in isolation
            ],
            "default_nodes": [
                {
                    "step": "Gather Error Context",
                    "action": "Collect the stack trace, error message, and relevant file snippets from VSCode diagnostics."
                },
                {
                    "step": "Analyze Root Cause",
                    "action": "Identify the most likely root cause from the error context and codebase structure."
                },
                {
                    "step": "Search for Prior Art",
                    "action": "Search GitHub issues and documentation for similar reported problems."
                },
                {
                    "step": "Propose Fix",
                    "action": "Draft a specific, minimal code change that addresses the root cause."
                },
                {
                    "step": "Validate Fix",
                    "action": "Run the affected test suite to confirm the proposed fix resolves the failure."
                },
            ]
        },

        # ── 2. HITL Checkpoints ────────────────────────────────
        hitl_checkpoints=[
            "before_running_test_suite",     # Execution consent for code runs
            "before_proposing_code_change",  # Human reviews the fix before it's surfaced
        ],

        # ── 3. Reflection Policies ─────────────────────────────
        reflection_policies={
            "focus_areas": [
                "Was the root cause correctly identified on the first attempt?",
                "Did the proposed fix require multiple iterations?",
                "Were any test runs triggered unnecessarily?",
                "Did the user modify the proposed fix significantly?"
            ],
            "procedural_update_threshold": 0.85
        },

        # ── 4. Telemetry ───────────────────────────────────────
        telemetry_expectations=[
            "time_to_root_cause_identification",
            "fix_iteration_count",
            "test_run_success_rate",
            "hitl_fix_modification_rate",
        ]
    )
