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