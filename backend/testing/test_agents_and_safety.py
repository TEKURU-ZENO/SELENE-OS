"""
SELENE OS — Agents, Safety Layer, Policy Engine & Attention Budget Tests
Covers FileAgent sandboxing/path traversal/permissions/rollback, OSAgent command
whitelist, SafetyLayer classification & plan annotation, PolicyEngine checkpoints,
and AttentionBudgetManager quiet hours and fatigue adaptation.
"""

import os
import shutil
import uuid
from datetime import time as dt_time

from agents.file_agent import WORKSPACE_ROOT, SecurityViolation, file_agent
from agents.os_agent import os_agent
from core.attention_budget import attention_budget
from safety.policy_engine import policy_engine
from safety.safety_layer import safety_layer
from schemas import (
    AttentionScore,
    Capability,
    ExecutionContext,
    ExecutionStatus,
    FilePermissionMode,
    ProactiveSuggestion,
    RiskLevel,
    SafeCommand,
    SuggestionStatus,
    TrustControls,
)


async def test_file_agent_sandbox_permissions_and_rollback():
    tmp_rel = f"test_file_agent_{uuid.uuid4().hex[:8]}"
    tmp_abs = os.path.join(WORKSPACE_ROOT, tmp_rel)
    os.makedirs(tmp_abs, exist_ok=True)

    try:
        # 1. Path traversal must be rejected
        try:
            file_agent._resolve_safe_path("../../etc/passwd")
            assert False, "Expected SecurityViolation on path traversal"
        except SecurityViolation:
            pass

        # 2. READ_ONLY denies write_file
        ro_ctx = ExecutionContext(session_id="fa_ro", file_permission_mode=FilePermissionMode.READ_ONLY)
        denied = await file_agent.write_file(f"{tmp_rel}/blocked.txt", "data", context=ro_ctx)
        assert denied.status == ExecutionStatus.FAILED
        assert "READ_ONLY" in (denied.error_details or "")

        # 3. TEMP_ONLY writes with .tmp suffix
        tmp_ctx = ExecutionContext(session_id="fa_tmp", file_permission_mode=FilePermissionMode.TEMP_ONLY)
        tmp_res = await file_agent.write_file(f"{tmp_rel}/scratch.txt", "temp_body", context=tmp_ctx)
        assert tmp_res.status == ExecutionStatus.SUCCESS
        assert os.path.exists(os.path.join(WORKSPACE_ROOT, f"{tmp_rel}/scratch.txt.tmp"))

        # 4. WRITE_ALLOWED + overwrite produces rollback token & backup file
        rw_ctx = ExecutionContext(session_id="fa_rw", file_permission_mode=FilePermissionMode.WRITE_ALLOWED)
        target = f"{tmp_rel}/notes.txt"
        first = await file_agent.write_file(target, "v1_original", context=rw_ctx)
        assert first.status == ExecutionStatus.SUCCESS
        assert first.rollback_token is None

        second = await file_agent.write_file(target, "v2_updated", context=rw_ctx)
        assert second.status == ExecutionStatus.SUCCESS
        assert second.rollback_token is not None

        read_back = await file_agent.read_file(target, context=ro_ctx)
        assert read_back.status == ExecutionStatus.SUCCESS
        assert read_back.result == "v2_updated"

        # Verify missing file fails gracefully
        missing = await file_agent.read_file(f"{tmp_rel}/missing.txt", context=ro_ctx)
        assert missing.status == ExecutionStatus.FAILED
    finally:
        shutil.rmtree(tmp_abs, ignore_errors=True)


async def test_os_agent_whitelist_enforcement():
    class BogusCommand:
        value = "rm_rf_root"

    denied = await os_agent.execute_safe_command(BogusCommand())
    assert denied.status == ExecutionStatus.FAILED
    assert "not authorized" in (denied.error_details or "")

    # Verify SafeCommand.RUN_GIT_STATUS executes cleanly without shell=True
    res = await os_agent.execute_safe_command(SafeCommand.RUN_GIT_STATUS)
    assert res.status == ExecutionStatus.SUCCESS
    assert res.result["exit_code"] == 0


def test_safety_layer_classification_and_audit():
    blocked = safety_layer.classify_action("format_disk")
    assert blocked.blocked is True
    assert blocked.risk_level == RiskLevel.CRITICAL

    risky = safety_layer.classify_action("file_write")
    assert risky.blocked is False
    assert risky.requires_confirmation is True
    assert risky.risk_level == RiskLevel.HIGH

    safe = safety_layer.classify_action("file_read")
    assert safe.blocked is False
    assert safe.requires_confirmation is False
    assert safe.risk_level == RiskLevel.LOW


def test_policy_engine_checkpoints():
    dev_ctx = ExecutionContext(session_id="pe_dev", environment="development")
    prod_ctx = ExecutionContext(session_id="pe_prod", environment="production")

    assert policy_engine.evaluate(Capability.MODIFY_SYSTEM, dev_ctx, "write file").requires_confirmation is True
    assert policy_engine.evaluate(Capability.EXECUTE_CODE, dev_ctx, "run tests").requires_confirmation is True
    assert policy_engine.evaluate(Capability.READ_DOCUMENT, dev_ctx, "read doc") is None

    assert policy_engine.evaluate(Capability.INTERACT_UI, dev_ctx, "click button") is None
    assert policy_engine.evaluate(Capability.INTERACT_UI, prod_ctx, "click button").requires_confirmation is True


def test_attention_budget_quiet_hours_and_fatigue():
    tenant = f"tenant_{uuid.uuid4().hex[:6]}"
    # Quiet hours spanning full 24h window around current time
    quiet_controls = TrustControls(
        tenant_id=tenant,
        quiet_hours_start=dt_time(0, 0),
        quiet_hours_end=dt_time(23, 59),
    )
    assert attention_budget.calculate_attention_score(tenant, 0.5, 0.8, 0.2, quiet_controls) == 0.0
    assert attention_budget.calculate_attention_score(tenant, 0.95, 0.95, 0.1, quiet_controls) > 0.0

    # Non-quiet controls to check fatigue updates
    active_controls = TrustControls(
        tenant_id=tenant,
        quiet_hours_start=dt_time(23, 59),
        quiet_hours_end=dt_time(23, 58),
    )
    attention_budget._user_fatigue[tenant] = 0.5
    s_dismissed = ProactiveSuggestion(
        tenant_id=tenant,
        title="Suggest",
        description="Desc",
        trigger_source="test",
        attention_score=AttentionScore(urgency=0.6, confidence=0.8, attention_cost=0.2, final_score=0.5),
        status=SuggestionStatus.DISMISSED,
    )
    attention_budget.record_suggestion_lifecycle(tenant, s_dismissed)
    assert attention_budget._user_fatigue[tenant] == 0.7

    s_accepted = ProactiveSuggestion(
        tenant_id=tenant,
        title="Suggest",
        description="Desc",
        trigger_source="test",
        attention_score=AttentionScore(urgency=0.6, confidence=0.8, attention_cost=0.2, final_score=0.5),
        status=SuggestionStatus.ACCEPTED,
    )
    attention_budget.record_suggestion_lifecycle(tenant, s_accepted)
    assert abs(attention_budget._user_fatigue[tenant] - 0.6) < 1e-6
    assert 0.0 <= attention_budget.calculate_attention_score(tenant, 0.8, 0.9, 0.1, active_controls) <= 1.0
