import os
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
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