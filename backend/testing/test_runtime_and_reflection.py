"""
SELENE OS — Distributed Runtime, Reflection, Memory Compression & EventBus Tests
Covers DistributedTaskQueue leases/heartbeats/HITL states, RecoveryManager dead lease
revocation, Operational -> Tactical -> Strategic reflection + LearningPolicy gating,
ContextCompressor filtering/deduplication, and EventBus pub/sub delivery.
"""

import time
import uuid

from core.event_bus import event_bus
from memory.context_compressor import context_compressor
from reflection.learning_policy import learning_policy
from reflection.operational import operational_reflection
from reflection.strategic import strategic_reflection
from reflection.tactical import tactical_reflection
from runtime.recovery_manager import recovery_manager
from runtime.task_queue import DistributedTaskQueue
from schemas import (
    Capability,
    EpisodicMemory,
    EventType,
    ExecutionReceipt,
    ExecutionStatus,
    MemoryMetadata,
    PlanNode,
    ProceduralMemory,
    ProceduralUpdate,
    SemanticMemory,
    TaskState,
    ValidationResult,
)


def test_task_queue_and_recovery_manager_lease_lifecycle():
    queue = DistributedTaskQueue()
    tenant = f"tenant_{uuid.uuid4().hex[:6]}"

    read_node = PlanNode(id="n_read", capability=Capability.READ_DOCUMENT, objective="Read doc")
    hitl_node = PlanNode(
        id="n_hitl",
        capability=Capability.MODIFY_SYSTEM,
        objective="Modify file",
        requires_confirmation=True,
    )

    job_read = queue.enqueue_task(read_node, tenant_id=tenant, trace_id="tr_1")
    job_hitl = queue.enqueue_task(hitl_node, tenant_id=tenant, trace_id="tr_2")
    assert job_read != job_hitl

    # HITL node should not be claimed while WAITING_HITL
    claimed = queue.claim_task(tenant, worker_id="w_1", capability_group=[Capability.READ_DOCUMENT.value, Capability.MODIFY_SYSTEM.value])
    assert claimed is not None
    assert claimed["job_id"] == job_read
    assert claimed["status"] == TaskState.LEASED.value

    # Heartbeat extends lease
    prev_exp = queue._leases[job_read]["expires_at"]
    assert queue.heartbeat(job_read) is True
    assert queue._leases[job_read]["expires_at"] >= prev_exp

    # Simulate dead lease and verify revocation via RecoveryManager helper / queue API
    queue._leases[job_read]["expires_at"] = time.time() - 10.0
    dead = queue.get_dead_leases()
    assert job_read in dead

    # Run RecoveryManager against global task_queue as well
    from runtime.task_queue import task_queue
    g_job = task_queue.enqueue_task(read_node, tenant_id=tenant, trace_id="tr_g")
    task_queue.claim_task(tenant, worker_id="w_g", capability_group=[Capability.READ_DOCUMENT.value])
    task_queue._leases[g_job]["expires_at"] = time.time() - 5.0
    recovery_manager.recover_dead_leases()
    assert g_job not in task_queue._leases


async def test_reflection_pipeline_and_learning_policy_gates():
    # Two failed receipts for the same tool should trigger Tactical -> Strategic ProceduralUpdate
    r1 = ExecutionReceipt(tool="web_search", status=ExecutionStatus.FAILED, duration_ms=10.0, result=None, error_details="timeout")
    r2 = ExecutionReceipt(tool="web_search", status=ExecutionStatus.FAILED, duration_ms=12.0, result=None, error_details="timeout")
    v_fail = ValidationResult(success=False, failed_criteria=["results_nonempty"], confidence=0.2)

    op1 = operational_reflection.analyze(r1, v_fail)
    op2 = operational_reflection.analyze(r2, v_fail)
    assert op1.tool_failure is not None and op1.validation_mismatch is True

    tactical_list = tactical_reflection.aggregate([op1, op2])
    assert len(tactical_list) == 1
    assert tactical_list[0].pattern == "web_search_consistent_failure"
    assert tactical_list[0].frequency == 2

    strategic = await strategic_reflection.reflect(tactical_list)
    assert len(strategic.procedural_updates) == 1

    approved, rejections = learning_policy.evaluate(strategic.procedural_updates, existing_memory=[])
    assert len(approved) == 1
    assert len(rejections) == 0

    # Verify LearningPolicy rejects low confidence, low recurrence, and contradictions
    low_conf = ProceduralUpdate(
        category="tool_preference",
        trigger_context="ctx_a",
        recommendation="Use fallback",
        evidence=["e1"],
        confidence=0.5,
        recurrence_count=3,
    )
    low_rec = ProceduralUpdate(
        category="tool_preference",
        trigger_context="ctx_b",
        recommendation="Use fallback",
        evidence=["e1"],
        confidence=0.95,
        recurrence_count=1,
    )
    contradicting = ProceduralUpdate(
        category="tool_preference",
        trigger_context="web_search_consistent_failure",
        recommendation="Keep using web_search anyway",
        evidence=["e2"],
        confidence=0.95,
        recurrence_count=3,
    )
    app2, rej2 = learning_policy.evaluate([low_conf, low_rec, contradicting], existing_memory=approved)
    assert app2 == []
    assert len(rej2) == 3


def test_context_compressor_filtering_and_deduplication():
    ep_noise = EpisodicMemory(content="heartbeat", metadata=MemoryMetadata(importance=0.1))
    ep_signal = EpisodicMemory(content="critical outage observed", metadata=MemoryMetadata(importance=0.8))

    sem1 = SemanticMemory(content="Postgres uses port 5432", fact_hash="hash_pg", metadata=MemoryMetadata(source="docs"))
    sem_dup = SemanticMemory(content="Postgres uses port 5432", fact_hash="hash_pg", metadata=MemoryMetadata(source="docs"))

    proc_low = ProceduralMemory(content={"step": "ignore"}, trigger_context="low", metadata=MemoryMetadata(importance=0.4))
    proc_high = ProceduralMemory(content={"step": "verify_lock"}, trigger_context="release", metadata=MemoryMetadata(importance=0.9))

    bundle = context_compressor.compress(
        session_id="comp_sess",
        episodic=[ep_noise, ep_signal],
        semantic=[sem1, sem_dup],
        procedural=[proc_low, proc_high],
    )
    assert len(bundle.episodic) == 1 and "critical outage observed" in bundle.episodic[0]
    assert len(bundle.semantic) == 1 and "Source: docs" in bundle.semantic[0]
    assert len(bundle.procedural) == 1 and bundle.procedural[0]["step"] == "verify_lock"
    assert bundle.compression_ratio == 0.5


async def test_event_bus_pubsub_and_history():
    session_id = f"eb_sess_{uuid.uuid4().hex[:8]}"
    queue = await event_bus.subscribe(session_id)
    try:
        published = event_bus.publish(session_id, EventType.SYSTEM_STATE, {"status": "ok"})
        received = await queue.get()
        assert received.id == published.id
        assert received.payload["status"] == "ok"
        assert len(event_bus.get_history(session_id)) == 1
    finally:
        event_bus.unsubscribe(session_id, queue)
        event_bus.clear_history(session_id)
