"""
SELENE OS — Core Data Schemas (Phase 15 Platform Ecosystem)
Pydantic models defining strict data contracts across all system boundaries.

🔧 UPDATES:
- PluginManifest & PluginTrustClassification (Controlled Extensibility).
- OrganizationalMemoryTier (Cognitive Governance).
- SharedCognitiveWorkflow (Platform Collaboration).
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict
from datetime import datetime, time as datetime_time
from enum import Enum
import uuid

# ══════════════════════════════════════════════════════════════════
# ENUMS & STATE MACHINES
# ══════════════════════════════════════════════════════════════════

class TaskState(str, Enum):
    PENDING = "pending"
    LEASED = "leased"
    EXECUTING = "executing"
    WAITING_HITL = "waiting_hitl"
    VALIDATING = "validating"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    CHECKPOINT_REACHED = "checkpoint_reached"
    SUCCESS = "success"
    FAILED = "failed"

class SuggestionStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    IGNORED = "ignored"
    DISMISSED = "dismissed"
    MODIFIED = "modified"
    DEFERRED = "deferred"

class ProactivityTier(str, Enum):
    PASSIVE = "passive"       
    SUGGESTIVE = "suggestive" 
    ASSISTED = "assisted"     
    AUTONOMOUS = "autonomous" 

class CognitivePresenceState(str, Enum):
    PASSIVE = "passive"
    AVAILABLE = "available"
    FOCUSED = "focused"
    DO_NOT_DISTURB = "do_not_disturb"

class MemoryTier(str, Enum):
    EPHEMERAL = "ephemeral"             
    LOCAL_PERSISTENT = "local_persistent" 
    SYNCED_COGNITIVE = "synced_cognitive" 

class OrganizationalMemoryTier(str, Enum):
    """Prevents cognitive contamination across scopes."""
    PERSONAL = "personal"    # user-only
    TEAM = "team"            # shared workspace
    ORG = "org"              # company-wide
    PUBLIC = "public"        # plugin-defined

class IntentType(str, Enum):
    TASK = "task"
    NEWS = "news"
    ANALYSIS = "analysis"
    CASUAL = "casual"
    EXPLORE = "explore"

class ModeType(str, Enum):
    GLOBAL = "GLOBAL"
    HYBRID = "HYBRID"
    PERSONAL = "PERSONAL"

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"
    TEMPORAL = "temporal"
    NATIVE_CONTEXT = "native_context"

class SafetyAction(str, Enum):
    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"
    RESPOND = "respond"

class EventType(str, Enum):
    EXECUTION_LOG = "execution_log"
    MEMORY_UPDATE = "memory_update"
    TOOL_STATUS = "tool_status"
    INTERRUPT = "interrupt"
    RESPONSE_STREAM = "response_stream"
    SYSTEM_STATE = "system_state"
    PROACTIVE_SUGGESTION = "proactive_suggestion"
    NATIVE_CONTEXT_SIGNAL = "native_context_signal"

class Capability(str, Enum):
    NAVIGATE_WEB = "navigate_web"
    READ_DOCUMENT = "read_document"
    MODIFY_SYSTEM = "modify_system"
    FIND_INFORMATION = "find_information"
    INTERACT_UI = "interact_ui"
    EXECUTE_CODE = "execute_code"
    NOTIFY_USER = "notify_user"
    PLUGIN_CAPABILITY = "plugin_capability" # dynamic extension

class SafeCommand(str, Enum):
    RUN_GIT_STATUS = "run_git_status"
    RUN_TESTS = "run_tests"

class FilePermissionMode(str, Enum):
    READ_ONLY = "read_only"
    WRITE_ALLOWED = "write_allowed"
    TEMP_ONLY = "temp_only"


class ArtifactSensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    EPHEMERAL = "ephemeral"

class ReplayFidelity(str, Enum):
    FULL = "full"
    SUMMARY = "summary"
    REDACTED = "redacted"

class ArtifactRef(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    sensitivity: ArtifactSensitivity = ArtifactSensitivity.INTERNAL
    replay_fidelity: ReplayFidelity = ReplayFidelity.FULL
    hash: str
    size_bytes: int
    uri: Optional[str] = None

# ══════════════════════════════════════════════════════════════════
# DISTRIBUTED EVENT BUS SCHEMAS
# ══════════════════════════════════════════════════════════════════

class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = Field(default="default_tenant")
    session_id: str
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None
    type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any]


# ══════════════════════════════════════════════════════════════════
# PLATFORM & PLUGIN SCHEMAS (PHASE 15)
# ══════════════════════════════════════════════════════════════════

class PluginTrustClassification(BaseModel):
    """Cognitive App Security for third-party extensions."""
    risk_level: RiskLevel = RiskLevel.MEDIUM
    verification_status: str = "unverified" # "verified", "certified", "unverified"
    permission_scope: List[str] = Field(default_factory=list)
    memory_scope: List[OrganizationalMemoryTier] = Field(default_factory=list)
    execution_scope: List[str] = Field(default_factory=list)

class PluginManifest(BaseModel):
    plugin_id: str
    version: str
    capabilities: List[Dict[str, Any]] = Field(default_factory=list)
    trust_classification: PluginTrustClassification
    requires_approval: bool = True

class SharedCognitiveWorkflow(BaseModel):
    """Reusable cognitive infrastructure as software."""
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    author: str
    target_tier: OrganizationalMemoryTier = OrganizationalMemoryTier.TEAM
    planning_template: Dict[str, Any]
    hitl_checkpoints: List[str]
    reflection_policies: Dict[str, Any]
    telemetry_expectations: List[str]


# ══════════════════════════════════════════════════════════════════
# NATIVE CONTEXT & CONNECTOR SCHEMAS
# ══════════════════════════════════════════════════════════════════

class ContextCategory(str, Enum):
    ACTIVE_WINDOW = "active_window"         
    WORKFLOW_INTENT = "workflow_intent"     
    BEHAVIORAL_PATTERN = "behavioral_pattern"
    PROCEDURAL_PREF = "procedural_pref"     

class NativeContextEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    app_source: str
    category: ContextCategory
    semantic_event: str 
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
class ConnectorPermission(str, Enum):
    OBSERVE = "observe"     
    SUGGEST = "suggest"     
    PREPARE = "prepare"     
    EXECUTE = "execute"     
    PERSIST = "persist"     

class ConnectorManifest(BaseModel):
    connector_id: str
    capabilities: List[Capability] = Field(default_factory=list)
    emitted_events: List[str] = Field(default_factory=list)
    requested_permissions: List[ConnectorPermission] = Field(default_factory=list)


# ══════════════════════════════════════════════════════════════════
# MEMORY & TRUST SCHEMAS
# ══════════════════════════════════════════════════════════════════

class TrustControls(BaseModel):
    tenant_id: str
    proactivity_tier: ProactivityTier = ProactivityTier.SUGGESTIVE
    max_suggestions_per_day: int = 5
    quiet_hours_start: datetime_time = Field(default_factory=lambda: datetime_time(22, 0))
    quiet_hours_end: datetime_time = Field(default_factory=lambda: datetime_time(8, 0))
    allow_autonomous_execution: bool = False
    connector_permissions: Dict[str, List[ConnectorPermission]] = Field(default_factory=dict)
    default_memory_tier: MemoryTier = MemoryTier.LOCAL_PERSISTENT
    org_tier_clearance: OrganizationalMemoryTier = OrganizationalMemoryTier.PERSONAL

class MemoryMetadata(BaseModel):
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    recency_score: float = Field(default=1.0, ge=0.0, le=1.0)
    access_count: int = Field(default=0)
    source: str = Field(default="system")
    tags: List[str] = Field(default_factory=list)
    memory_tier: MemoryTier = MemoryTier.LOCAL_PERSISTENT
    org_tier: OrganizationalMemoryTier = OrganizationalMemoryTier.PERSONAL

class BaseMemory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = Field(default="default_tenant")
    memory_type: MemoryType
    content: Any
    metadata: MemoryMetadata = Field(default_factory=MemoryMetadata)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)

class EpisodicMemory(BaseMemory):
    memory_type: MemoryType = MemoryType.EPISODIC
    content: str
    event_type: str = Field(default="conversation")

class SemanticMemory(BaseMemory):
    memory_type: MemoryType = MemoryType.SEMANTIC
    content: str
    fact_hash: Optional[str] = None

class ProceduralMemory(BaseMemory):
    memory_type: MemoryType = MemoryType.PROCEDURAL
    content: Dict[str, Any]
    trigger_context: str

class WorkingMemory(BaseMemory):
    memory_type: MemoryType = MemoryType.WORKING
    session_id: str
    content: Dict[str, Any]

class TemporalMemory(BaseMemory):
    memory_type: MemoryType = MemoryType.TEMPORAL
    content: Dict[str, Any] 
    trigger_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    last_reinforced_at: datetime = Field(default_factory=datetime.utcnow)
    decay_rate: float = 0.05 

class PendingIntent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    intent_description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    status: TaskState = TaskState.PENDING
    context_refs: List[str] = Field(default_factory=list)

class ContextBundle(BaseModel):
    tenant_id: str = Field(default="default_tenant")
    session_id: str
    episodic: List[str] = Field(default_factory=list)
    semantic: List[str] = Field(default_factory=list)
    procedural: List[Dict[str, Any]] = Field(default_factory=list)
    temporal: List[Dict[str, Any]] = Field(default_factory=list)
    pending_intents: List[str] = Field(default_factory=list)
    native_context: List[NativeContextEvent] = Field(default_factory=list)
    compression_ratio: float = 1.0


# ══════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE
# ══════════════════════════════════════════════════════════════════

class IntentResult(BaseModel):
    intent: IntentType
    mode: ModeType
    confidence: float = Field(ge=0.0, le=1.0)
    needs_clarification: bool = False
    clarification_prompt: Optional[str] = None

class ChatRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=10000)
    tenant_id: str = Field(default="default_tenant")
    mode: str = Field(default="text")
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ══════════════════════════════════════════════════════════════════
# EXECUTION CONTEXT & RECEIPTS
# ══════════════════════════════════════════════════════════════════

class ExecutionContext(BaseModel):
    tenant_id: str = Field(default="default_tenant")
    user_id: str = Field(default="default_user")
    session_id: str
    trace_id: str
    permissions: List[str] = Field(default_factory=list)
    active_memory_id: Optional[str] = None
    environment: str = Field(default="development")
    file_permission_mode: FilePermissionMode = FilePermissionMode.TEMP_ONLY

class ExecutionReceipt(BaseModel):
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = Field(default="default_tenant")
    parent_execution_id: Optional[str] = None
    checkpoint_id: Optional[str] = None
    
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    source_type: str = "worker" # "mcp", "native", "worker"
    source_name: str = "internal"
    
    tool: str
    capability: Optional[Capability] = None
    status: TaskState
    duration_ms: float
    
    receipt_hash: str = ""
    parent_receipt_hash: Optional[str] = None
    
    replay_supported: bool = True
    idempotent: bool = False
    validation_required: bool = False
    
    result: Any
    result_summary: Dict[str, Any] = Field(default_factory=dict)
    
    artifacts: List[ArtifactRef] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)
    
    policy_decisions: List[str] = Field(default_factory=list)
    hitl_triggered: bool = False
    
    validation_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
    rollback_token: Optional[str] = None
    error_details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StepLog(BaseModel):
    node_id: str
    action: Optional[str] = None
    status: ExecutionStatus
    message: str

class ExecutionResultNode(BaseModel):
    node_id: str
    status: ExecutionStatus
    receipt: Optional[ExecutionReceipt] = None

class ExecutionState(BaseModel):
    plan_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_node: Optional[str] = None
    completed_nodes: List[str] = Field(default_factory=list)
    failed_nodes: List[str] = Field(default_factory=list)
    results: List[ExecutionResultNode] = Field(default_factory=list)
    logs: List[StepLog] = Field(default_factory=list)
    total_duration_ms: float = 0.0


# ══════════════════════════════════════════════════════════════════
# HIERARCHICAL PLAN SCHEMAS
# ══════════════════════════════════════════════════════════════════

class ExecutionCheckpoint(BaseModel):
    action: str
    requires_confirmation: bool = True
    rollback_available: bool = False
    reason: str

class SuccessCriterion(BaseModel):
    type: str  
    expected: str
    required: bool = True

class PlanNode(BaseModel):
    id: str
    capability: Capability
    objective: str
    dependencies: List[str] = Field(default_factory=list)
    success_criteria: List[SuccessCriterion] = Field(default_factory=list)
    params: Dict[str, Any] = Field(default_factory=dict)
    status: TaskState = TaskState.PENDING
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4()))
    affinity_group: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    checkpoint: Optional[ExecutionCheckpoint] = None

class ObjectiveGroup(BaseModel):
    id: str
    objective: str
    nodes: List[PlanNode]

class ExecutionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = Field(default="default_tenant")
    objective: str
    groups: List[ObjectiveGroup]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ══════════════════════════════════════════════════════════════════
# PROACTIVE COGNITION & ATTENTION SCHEMAS
# ══════════════════════════════════════════════════════════════════

class AttentionScore(BaseModel):
    urgency: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    attention_cost: float = Field(ge=0.0, le=1.0)
    interruption_sensitivity: float = Field(default=0.5, ge=0.0, le=1.0)
    final_score: float = Field(ge=0.0, le=1.0)

class ProactiveSuggestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    title: str
    description: str
    trigger_source: str
    proposed_plan: Optional[ExecutionPlan] = None
    attention_score: AttentionScore
    status: SuggestionStatus = SuggestionStatus.PROPOSED
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════
# VALIDATION & CRITIC
# ══════════════════════════════════════════════════════════════════

class ValidationResult(BaseModel):
    success: bool
    passed_criteria: List[str] = Field(default_factory=list)
    failed_criteria: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

class CriticIssue(BaseModel):
    severity: RiskLevel
    node_id: Optional[str] = None
    message: str
    suggestion: Optional[str] = None

class CriticVerdict(BaseModel):
    approved: bool
    issues: List[CriticIssue] = Field(default_factory=list)
    suggested_repairs: List[str] = Field(default_factory=list)
    risk_score: float = Field(ge=0.0, le=1.0)
    critic_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    estimated_execution_cost: int = 0
    static_checks_passed: bool = True
    cognitive_checks_passed: bool = True


# ══════════════════════════════════════════════════════════════════
# TELEMETRY & META-COGNITION SCHEMAS
# ══════════════════════════════════════════════════════════════════

class PlannerTelemetry(BaseModel):
    plan_id: str
    tenant_id: str = Field(default="default_tenant")
    session_id: str
    dag_size: int
    repair_count: int = 0
    final_risk_score: float = 0.0
    execution_success_rate: float = 0.0
    failed_capabilities: List[Capability] = Field(default_factory=list)

class ProceduralUpdate(BaseModel):
    tenant_id: str = Field(default="default_tenant")
    category: str
    trigger_context: str
    recommendation: str
    evidence: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
    recurrence_count: int = Field(default=1)
    reinforcement_score: float = Field(default=1.0, ge=0.0, le=1.0)
    last_reinforced_at: datetime = Field(default_factory=datetime.utcnow)

class OperationalReflection(BaseModel):
    execution_id: str
    tool_failure: Optional[str] = None
    recovery_successful: bool = False
    validation_mismatch: bool = False

class TacticalReflection(BaseModel):
    pattern: str
    frequency: int
    related_operational_ids: List[str] = Field(default_factory=list)

class StrategicReflection(BaseModel):
    procedural_updates: List[ProceduralUpdate] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

class PlanningPreferences(BaseModel):
    preferred_capabilities: Dict[str, str] = Field(default_factory=dict)
    avoid_patterns: List[str] = Field(default_factory=list)
    success_biases: List[str] = Field(default_factory=list)

class LearningAuditEntry(BaseModel):
    update_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = Field(default="default_tenant")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    procedural_update: ProceduralUpdate
    action_taken: str
    reason: str


# ══════════════════════════════════════════════════════════════════
# SCENARIO & METRICS SCHEMAS
# ══════════════════════════════════════════════════════════════════

class ScenarioResult(BaseModel):
    scenario_id: str
    success: bool
    planner_quality_score: float = Field(ge=0.0, le=1.0)
    validation_success_rate: float = Field(ge=0.0, le=1.0)
    reflection_quality_score: float = Field(ge=0.0, le=1.0)
    interrupt_correctness: float = Field(ge=0.0, le=1.0)
    failure_reason: Optional[str] = None

class CognitiveHealthMetrics(BaseModel):
    avg_dag_depth: float
    planner_repair_rate: float
    critic_rejection_rate: float
    tool_success_rate: float
    timeout_distribution: Dict[str, int]
    accepted_learnings_count: int
    rejected_learnings_count: int
    contradiction_frequency: float
    hitl_interrupt_frequency: float
    hitl_modification_rate: float


# ══════════════════════════════════════════════════════════════════
# TOOL METADATA
# ══════════════════════════════════════════════════════════════════

class ToolMetadata(BaseModel):
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    rollback_supported: bool = False

class ToolDefinition(BaseModel):
    name: str
    description: str
    agent: str
    metadata: ToolMetadata = Field(default_factory=ToolMetadata)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
