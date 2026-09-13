"""
SELENE OS — GitHub Connector
Polls the GitHub REST API to emit semantic NativeContextEvents about
active PRs, CI status, and repo activity. All raw data is abstracted
into semantic signals before entering the Native Context Layer.

The connector NEVER writes to memory directly. It only emits events
that the NativeContextRuntime ingests and decays via half-life logic.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import List, Optional

import httpx
import structlog

from connectors.base_connector import BaseConnector
from schemas import (
    NativeContextEvent,
    ConnectorManifest,
    ContextCategory,
    Capability,
    OrganizationalMemoryTier,
    RiskLevel,
)

logger = structlog.get_logger(__name__)


class GitHubConnector(BaseConnector):
    """
    Polls GitHub REST API for active PRs, CI check runs, and review requests.
    Transforms raw API responses into semantic NativeContextEvents.

    Context signals emitted:
    - "active_pr_detected"       (ACTIVE_WINDOW, 30min half-life)
    - "ci_failing"               (WORKFLOW_INTENT, 4hr half-life)
    - "review_requested"         (WORKFLOW_INTENT, 4hr half-life)
    - "pr_merged"                (BEHAVIORAL_PATTERN, 2day half-life)
    """

    def __init__(self, github_token: str, repo: str, tenant_id: str):
        """
        Args:
            github_token: GitHub Personal Access Token (PAT) with repo scope.
            repo:         Repository in "owner/repo" format.
            tenant_id:    SELENE tenant identifier for context scoping.
        """
        manifest = ConnectorManifest(
            connector_id="github_connector",
            name="GitHub Context Connector",
            version="1.0.0",
            capabilities=[Capability.READ_DOCUMENT, Capability.FIND_INFORMATION],
            memory_scope=OrganizationalMemoryTier.TEAM,
            risk_level=RiskLevel.LOW,
        )
        super().__init__(manifest)
        self._token = github_token
        self._repo = repo
        self._tenant_id = tenant_id
        self._api_base = "https://api.github.com"

    async def poll_context(self) -> List[NativeContextEvent]:
        """
        Fetches GitHub data and converts it into semantic NativeContextEvents.
        Never returns raw API payloads — only abstracted semantic signals.
        """
        events: List[NativeContextEvent] = []

        async with httpx.AsyncClient(
            base_url=self._api_base,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15.0,
        ) as client:
            # ── Active PRs ────────────────────────────────────────
            pr_events = await self._poll_pull_requests(client)
            events.extend(pr_events)

            # ── CI Check Runs ─────────────────────────────────────
            ci_events = await self._poll_check_runs(client)
            events.extend(ci_events)

        logger.info(
            "github_context_polled",
            repo=self._repo,
            events_emitted=len(events),
        )
        return events

    async def execute_capability(self, capability_name: str, params: dict):
        """
        Executes a GitHub action (e.g., create a draft PR comment).
        All write actions are HITL-gated at the Policy Gate level —
        this method only dispatches if governance has already approved.
        """
        async with httpx.AsyncClient(
            base_url=self._api_base,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        ) as client:
            if capability_name == "create_pr_comment":
                pr_number = params.get("pr_number")
                body = params.get("body", "")
                resp = await client.post(
                    f"/repos/{self._repo}/issues/{pr_number}/comments",
                    json={"body": body},
                )
                resp.raise_for_status()
                return {"comment_id": resp.json().get("id"), "status": "created"}

            elif capability_name == "get_pr_diff":
                pr_number = params.get("pr_number")
                resp = await client.get(
                    f"/repos/{self._repo}/pulls/{pr_number}",
                    headers={"Accept": "application/vnd.github.diff"},
                )
                resp.raise_for_status()
                return {"diff": resp.text[:4000]}  # Cap at 4KB to avoid context bloat

            else:
                raise NotImplementedError(f"GitHub capability '{capability_name}' not implemented.")

    # ── Internal polling helpers ──────────────────────────────────

    async def _poll_pull_requests(self, client: httpx.AsyncClient) -> List[NativeContextEvent]:
        events = []
        try:
            resp = await client.get(
                f"/repos/{self._repo}/pulls",
                params={"state": "open", "per_page": 5},
            )
            resp.raise_for_status()
            prs = resp.json()

            for pr in prs:
                events.append(NativeContextEvent(
                    tenant_id=self._tenant_id,
                    app_source="github",
                    semantic_event="active_pr_detected",
                    category=ContextCategory.ACTIVE_WINDOW,
                    payload={
                        "pr_number": pr.get("number"),
                        "title": pr.get("title", "")[:120],
                        "author": pr.get("user", {}).get("login"),
                        "branch": pr.get("head", {}).get("ref"),
                        "draft": pr.get("draft", False),
                    },
                    timestamp=datetime.now(timezone.utc),
                ))

                # Check if review is requested from this user
                reviewers = pr.get("requested_reviewers", [])
                if reviewers:
                    events.append(NativeContextEvent(
                        tenant_id=self._tenant_id,
                        app_source="github",
                        semantic_event="review_requested",
                        category=ContextCategory.WORKFLOW_INTENT,
                        payload={
                            "pr_number": pr.get("number"),
                            "reviewers": [r.get("login") for r in reviewers],
                        },
                        timestamp=datetime.now(timezone.utc),
                    ))

        except httpx.HTTPStatusError as e:
            logger.warning("github_pr_poll_failed", status=e.response.status_code)
        except Exception as e:
            logger.warning("github_pr_poll_error", error=str(e))

        return events

    async def _poll_check_runs(self, client: httpx.AsyncClient) -> List[NativeContextEvent]:
        events = []
        try:
            # Get the default branch's latest commit SHA
            resp = await client.get(f"/repos/{self._repo}")
            resp.raise_for_status()
            default_branch = resp.json().get("default_branch", "main")

            resp = await client.get(f"/repos/{self._repo}/commits/{default_branch}")
            resp.raise_for_status()
            sha = resp.json().get("sha", "")

            # Get check runs for that commit
            resp = await client.get(f"/repos/{self._repo}/commits/{sha}/check-runs")
            resp.raise_for_status()
            check_runs = resp.json().get("check_runs", [])

            failing = [r for r in check_runs if r.get("conclusion") in ("failure", "timed_out")]
            if failing:
                events.append(NativeContextEvent(
                    tenant_id=self._tenant_id,
                    app_source="github",
                    semantic_event="ci_failing",
                    category=ContextCategory.WORKFLOW_INTENT,
                    payload={
                        "failing_checks": [r.get("name") for r in failing],
                        "sha": sha[:8],
                        "branch": default_branch,
                    },
                    timestamp=datetime.now(timezone.utc),
                ))

        except httpx.HTTPStatusError as e:
            logger.warning("github_ci_poll_failed", status=e.response.status_code)
        except Exception as e:
            logger.warning("github_ci_poll_error", error=str(e))

        return events
