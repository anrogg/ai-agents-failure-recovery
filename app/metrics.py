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