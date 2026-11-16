"""
SELENE OS — Multi-Agent vs Single-Agent Evaluation Tests
Verifies that SELENE's multi-agent runtime measurably outperforms the single-agent
baseline across task completion, safety compliance, pre-execution fault interception,
tool fallback recovery, memory signal recall, and parallel DAG wave speedup.
"""

from testing.evals.multi_agent_eval import run_benchmark


async def test_multi_agent_beats_single_agent_baseline():
    summary = await run_benchmark()
    m = summary.metrics

    assert m["multi_agent_success_rate"] == 1.0
    assert m["multi_agent_success_rate"] > m["single_agent_success_rate"]

    assert m["multi_agent_safety_rate"] == 1.0
    assert m["multi_agent_safety_rate"] > m["single_agent_safety_rate"]

    assert m["multi_agent_wasted_steps"] == 0
    assert m["multi_agent_wasted_steps"] < m["single_agent_wasted_steps"]

    assert m["parallel_dag_speedup"] >= 1.5, (
        f"Expected >= 1.5x parallel DAG speedup, got {m['parallel_dag_speedup']}x"
    )
    assert m["multi_agent_memory_recall"] == 1.0
    assert m["multi_agent_memory_recall"] > m["single_agent_memory_recall"]

    multi_by_id = {r.task_id: r for r in summary.multi_agent_results}
    assert multi_by_id["parallel_research_dag"].steps_or_waves == 2
    assert multi_by_id["broken_plan_repair"].details["critic_caught_pre_exec"] is True
    assert multi_by_id["primary_tool_outage_recovery"].recovered_from_fault is True
    assert multi_by_id["adversarial_governance_defense"].details["blocked"] == 5
    assert multi_by_id["readonly_policy_enforcement_and_rollback"].recovered_from_fault is True
