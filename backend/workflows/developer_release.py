"""
SELENE OS — Developer Release Workflow Pack v1
A gold-standard, reusable cognitive workflow that bridges cross-app continuity
(VSCode, GitHub, Slack) to reduce cognitive friction without reducing human agency.
"""

from typing import Dict, Any, List
from schemas import (
    SharedCognitiveWorkflow, OrganizationalMemoryTier, 
    Capability, ExecutionCheckpoint, RiskLevel
)
import structlog

logger = structlog.get_logger(__name__)


def get_developer_release_workflow() -> SharedCognitiveWorkflow:
    """
    Returns the gold-standard Developer Release Workflow.
    This dictates how SELENE anticipates and assists during a release cycle.
    """
    return SharedCognitiveWorkflow(
        name="Developer Release Workflow v1",
        author="system",
        target_tier=OrganizationalMemoryTier.TEAM,
        
        # ── 1. The Planning Template (The "What") ──────────────
        planning_template={
            "objective": "Prepare and execute a feature release spanning VSCode, GitHub, and Slack.",
            "expected_capabilities": [
                Capability.READ_DOCUMENT,      # Read code diffs
                Capability.PLUGIN_CAPABILITY,  # GitHub PR / Slack messaging
                Capability.EXECUTE_CODE        # Run tests/lints
            ],
            "default_nodes": [
                {
                    "step": "Analyze Diffs",
                    "action": "Summarize changed modules from the active branch."
                },
                {
                    "step": "Draft Release Notes",
                    "action": "Generate user-facing release notes based on the PR."
                },
                {
                    "step": "Reviewer Notification",
                    "action": "Draft a Slack message to reviewers."
                },
                {
                    "step": "Deployment Checklist",
                    "action": "Verify CI/CD pipeline status."
                }
            ]
        },
        
        # ── 2. The Trust & Agency Gates (The "HITL") ────────────
        hitl_checkpoints=[
            "before_posting_slack_message",
            "before_creating_github_pr",
            "before_initiating_deployment"
        ],
        
        # ── 3. Reflection Policies (The "Learning") ─────────────
        reflection_policies={
            "focus_areas": [
                "Did the reviewer request changes that the release notes missed?",
                "Was the Slack message tone appropriate?",
                "Did the CI/CD checklist catch an actual failure?"
            ],
            "procedural_update_threshold": 0.8  # High confidence needed to update habits
        },
        
        # ── 4. Observability & Telemetry (The "Audit") ──────────
        telemetry_expectations=[
            "time_to_approval",
            "hitl_modification_count",  # Did the user edit the drafted Slack message?
            "deployment_success_rate"
        ]
    )

