import os
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from enum import Enum


class FailureType(str, Enum):
    OUTPUT_QUALITY = "output_quality"
    BEHAVIORAL = "behavioral" 
    INTEGRATION = "integration"
    RESOURCE = "resource"


class FailureMode(str, Enum):
    HALLUCINATION = "hallucination"
    INCORRECT_REASONING = "incorrect_reasoning"
    OFF_TOPIC = "off_topic"
    INFINITE_LOOP = "infinite_loop"
    REFUSING_PROGRESS = "refusing_progress"
    API_TIMEOUT = "api_timeout"
    AUTH_ERROR = "auth_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TOKEN_LIMIT = "token_limit"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    RATE_LIMITING = "rate_limiting"


class InteractionStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


class AgentRequest(BaseModel):
    session_id: str
    message: str
    context: Optional[Dict[str, Any]] = None
    failure_mode: Optional[FailureMode] = None
    max_tokens: Optional[int] = 2000
    model: str = Field(default_factory=lambda: os.getenv("AI_MODEL", "gpt-3.5-turbo"))


class AgentResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    session_id: str
    response: str
    status: InteractionStatus
    natural_status: InteractionStatus  # What LLM actually produced
    failure_mode: Optional[FailureMode] = None
    failure_injection_applied: bool = False
    natural_response: Optional[str] = None  # Original LLM response before injection
    processing_time_ms: int
    token_count: int
    model_used: str
    metadata: Optional[Dict[str, Any]] = None


class FailureScenario(BaseModel):
    name: str
    description: str
    failure_type: FailureType
    config: Dict[str, Any]
    enabled: bool = True


class RecoveryAttempt(BaseModel):
    interaction_id: int
    recovery_strategy: str
    attempt_number: int
    success: bool
    recovery_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class SystemMetric(BaseModel):
    metric_type: str
    metric_value: float
    threshold_value: Optional[float] = None
    exceeded_threshold: bool = False
    metadata: Optional[Dict[str, Any]] = None


class AgentState(BaseModel):
    session_id: str
    conversation_history: List[Dict[str, Any]]
    context: Dict[str, Any]
    failure_count: int = 0
    recovery_count: int = 0
    last_interaction: Optional[datetime] = None


class InteractionBehavior(BaseModel):
    """Behavioral metrics for a single agent interaction."""
    session_id: str
    response_latency_ms: int
    message_length: int
    conversation_turns: int
    clarification_frequency: float
    topic_switches: int
    confidence_expressions: int
    timestamp: datetime
    anomaly_score: Optional[float] = None
    baseline_deviation: Optional[float] = None


class BehavioralBaseline(BaseModel):
    """Established normal behavior patterns for a session."""
    session_id: str
    avg_response_latency: float
    typical_message_length_range: Tuple[int, int]
    normal_clarification_rate: float
    standard_conversation_depth: int
    confidence_pattern: Dict[str, float]
    interaction_count: int
    established_at: datetime
    last_updated: datetime


class ConversationFlowMetrics(BaseModel):
    """Metrics describing conversation flow characteristics."""
    session_id: str
    flow_consistency_score: float
    topic_coherence_score: float
    engagement_level: float
    turn_taking_pattern: List[int]
    response_rhythm_score: float


class DriftScore(BaseModel):
    """Behavioral drift detection results."""
    session_id: str
    drift_score: float
    drift_type: str
    time_window_hours: int
    confidence: float
    detected_at: datetime
    contributing_factors: List[str]


class PatternAnalysis(BaseModel):
    """Analysis of interaction patterns."""
    session_id: str
    pattern_type: str
    pattern_strength: float
    repetition_count: int
    last_occurrence: datetime
    pattern_metadata: Dict[str, Any]