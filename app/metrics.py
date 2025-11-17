from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps

# Agent response metrics
agent_requests_total = Counter(
    'agent_requests_total',
    'Total number of agent requests',
    ['failure_type', 'status']
)

agent_response_duration = Histogram(
    'agent_response_duration_seconds',
    'Time spent processing agent requests',
    ['failure_type']
)

# Failure-specific counters for your 11 failure modes
failure_injections_total = Counter(
    'failure_injections_total',
    'Total number of failure injections by type',
    ['failure_mode', 'scenario']
)

# Performance counters
token_consumption_total = Counter(
    'token_consumption_total',
    'Total tokens consumed',
    ['model', 'type']  # type: prompt/completion
)

# System health metrics
active_connections = Gauge(
    'active_connections',
    'Number of active database connections'
)

redis_connection_status = Gauge(
    'redis_connection_status',
    'Redis connection status (1=healthy, 0=unhealthy)'
)

# Agent service info
agent_service_info = Info(
    'agent_service_info',
    'Information about the agent service'
)

# Output validation metrics
validation_checks_total = Counter(
    'validation_checks_total',
    'Total number of validation checks performed',
    ['validation_level', 'strategy', 'result']  # result: passed/failed
)

validation_confidence_score = Histogram(
    'validation_confidence_score',
    'Distribution of validation confidence scores',
    ['validation_level']
)

validation_errors_total = Counter(
    'validation_errors_total',
    'Total number of validation errors by type',
    ['error_type', 'strategy']
)

validation_processing_duration = Histogram(
    'validation_processing_duration_seconds',
    'Time spent on validation processing',
    ['validation_level']
)

# Behavioral anomaly detection metrics
behavioral_anomaly_score = Histogram(
    'behavioral_anomaly_score',
    'Distribution of behavioral anomaly scores',
    ['anomaly_type', 'session_type']
)

interaction_consistency_score = Histogram(
    'interaction_consistency_score',
    'Agent interaction consistency over time',
    ['session_id']
)

conversation_flow_disruptions = Counter(
    'conversation_flow_disruptions_total',
    'Number of conversation flow disruptions detected',
    ['disruption_type']
)

behavioral_drift_score = Histogram(
    'behavioral_drift_score',
    'Behavioral drift detection scores',
    ['drift_type', 'time_window']
)

baseline_establishment_total = Counter(
    'baseline_establishment_total',
    'Number of behavioral baselines established',
    ['session_type']
)

baseline_update_total = Counter(
    'baseline_update_total',
    'Number of behavioral baseline updates',
    ['update_reason']
)


class MetricsCollector:
    def __init__(self):
        self.start_time = time.time()

    def record_agent_request(self, failure_type: str, status: str, duration: float):
        """Record metrics for an agent request"""
        agent_requests_total.labels(failure_type=failure_type, status=status).inc()
        agent_response_duration.labels(failure_type=failure_type).observe(duration)

    def record_failure_injection(self, failure_mode: str, scenario: str):
        """Record when a failure is injected"""
        failure_injections_total.labels(failure_mode=failure_mode, scenario=scenario).inc()

    def record_token_usage(self, model: str, prompt_tokens: int, completion_tokens: int):
        """Record token consumption"""
        token_consumption_total.labels(model=model, type='prompt').inc(prompt_tokens)
        token_consumption_total.labels(model=model, type='completion').inc(completion_tokens)

    def update_system_health(self, db_connections: int, redis_healthy: bool):
        """Update system health metrics"""
        active_connections.set(db_connections)
        redis_connection_status.set(1 if redis_healthy else 0)

    def record_validation_check(self, validation_level: str, strategy: str,
                               passed: bool, confidence: float, duration: float,
                               errors: list = None):
        """Record validation check metrics"""
        result = "passed" if passed else "failed"

        # Record the validation check
        validation_checks_total.labels(
            validation_level=validation_level,
            strategy=strategy,
            result=result
        ).inc()

        # Record confidence score
        validation_confidence_score.labels(validation_level=validation_level).observe(confidence)

        # Record processing time
        validation_processing_duration.labels(validation_level=validation_level).observe(duration)

        # Record specific errors
        if errors:
            for error in errors:
                # Extract error type from error message (simple classification)
                error_type = self._classify_validation_error(error)
                validation_errors_total.labels(
                    error_type=error_type,
                    strategy=strategy
                ).inc()

    def _classify_validation_error(self, error_message: str) -> str:
        """Classify validation errors into types for metrics"""
        error_lower = error_message.lower()

        if "inappropriate" in error_lower or "profanity" in error_lower:
            return "inappropriate_content"
        elif "empty" in error_lower:
            return "empty_output"
        elif "quality" in error_lower:
            return "low_quality"
        elif "confidence" in error_lower or "overconfident" in error_lower:
            return "confidence_issue"
        elif "coherence" in error_lower or "gibberish" in error_lower:
            return "coherence_issue"
        elif "format" in error_lower or "structure" in error_lower:
            return "format_issue"
        else:
            return "other"

    def record_behavioral_anomaly(self, session_id: str, anomaly_type: str,
                                 score: float, session_type: str = "standard"):
        """Record behavioral anomaly detection metrics."""
        behavioral_anomaly_score.labels(
            anomaly_type=anomaly_type,
            session_type=session_type
        ).observe(score)

    def record_interaction_consistency(self, session_id: str, consistency_score: float):
        """Record interaction consistency metrics."""
        interaction_consistency_score.labels(session_id=session_id).observe(consistency_score)

    def record_conversation_flow_disruption(self, disruption_type: str):
        """Record conversation flow disruption."""
        conversation_flow_disruptions.labels(disruption_type=disruption_type).inc()

    def record_behavioral_drift(self, drift_type: str, drift_score: float, time_window: int):
        """Record behavioral drift detection."""
        behavioral_drift_score.labels(
            drift_type=drift_type,
            time_window=str(time_window)
        ).observe(drift_score)

    def record_baseline_establishment(self, session_type: str = "standard"):
        """Record behavioral baseline establishment."""
        baseline_establishment_total.labels(session_type=session_type).inc()

    def record_baseline_update(self, update_reason: str):
        """Record behavioral baseline update."""
        baseline_update_total.labels(update_reason=update_reason).inc()

    def increment_counter(self, metric_name: str, labels: dict = None):
        """Generic counter increment method for behavioral monitoring."""
        if labels is None:
            labels = {}

        if metric_name == 'interaction_total':
            # Map to existing validation counter with behavioral type
            validation_checks_total.labels(
                validation_level='behavioral',
                strategy='behavioral_monitoring',
                result='passed'
            ).inc()
        elif metric_name == 'conversation_flow_disruptions_total':
            disruption_type = labels.get('disruption_type', 'unknown')
            conversation_flow_disruptions.labels(disruption_type=disruption_type).inc()

    def observe_histogram(self, metric_name: str, value: float, labels: dict = None):
        """Generic histogram observation method for behavioral monitoring."""
        if labels is None:
            labels = {}

        if metric_name == 'interaction_latency':
            behavioral_anomaly_score.labels(
                anomaly_type='response_latency',
                session_type='behavioral'
            ).observe(value)
        elif metric_name == 'message_length_histogram':
            behavioral_anomaly_score.labels(
                anomaly_type='message_length',
                session_type='behavioral'
            ).observe(value)
        elif metric_name == 'interaction_consistency_score':
            session_id = labels.get('session_id', 'unknown')
            behavioral_anomaly_score.labels(
                anomaly_type='consistency',
                session_type=session_id
            ).observe(value)


# Global metrics collector instance
metrics_collector = MetricsCollector()


def track_agent_performance(failure_type: str = "none"):
    """Decorator to track agent performance metrics"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                metrics_collector.record_agent_request(failure_type, status, duration)

        return wrapper

    return decorator