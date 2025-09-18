-- Agent Failure Recovery Database Schema

-- Table to track all agent requests and responses
CREATE TABLE agent_interactions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    request_data JSONB NOT NULL,
    response_data JSONB,
    status VARCHAR(50) NOT NULL, -- 'success', 'failure', 'timeout', 'error'
    natural_status VARCHAR(50) NOT NULL, -- What LLM actually produced
    failure_mode VARCHAR(100), -- type of failure if applicable
    failure_injection_applied BOOLEAN DEFAULT FALSE,
    natural_response TEXT, -- Original LLM response before injection
    processing_time_ms INTEGER,
    token_count INTEGER,
    model_used VARCHAR(100)
);

-- Table to track failure injection scenarios
CREATE TABLE failure_scenarios (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    failure_type VARCHAR(100) NOT NULL, -- 'output_quality', 'behavioral', 'integration', 'resource'
    config JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table to track recovery attempts
CREATE TABLE recovery_attempts (
    id SERIAL PRIMARY KEY,
    interaction_id INTEGER REFERENCES agent_interactions(id),
    recovery_strategy VARCHAR(100) NOT NULL,
    attempt_number INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN NOT NULL,
    recovery_data JSONB,
    notes TEXT
);

-- Table to track agent state snapshots for recovery
CREATE TABLE agent_state_snapshots (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    snapshot_type VARCHAR(50) NOT NULL, -- 'checkpoint', 'pre_failure', 'post_recovery'
    state_data JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table to track system metrics and resource usage
CREATE TABLE system_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metric_type VARCHAR(100) NOT NULL, -- 'memory', 'cpu', 'token_usage', 'api_calls'
    metric_value DECIMAL(10,2) NOT NULL,
    threshold_value DECIMAL(10,2),
    exceeded_threshold BOOLEAN DEFAULT false,
    metric_metadata JSONB
);

-- Insert some default failure scenarios
INSERT INTO failure_scenarios (name, description, failure_type, config) VALUES
('hallucination_mode', 'Agent provides confident but false information', 'output_quality', '{"probability": 0.3, "types": ["fake_facts", "non_existent_features", "false_citations"]}'),
('infinite_loop', 'Agent gets stuck in repetitive behavior patterns', 'behavioral', '{"trigger_keywords": ["clarify", "can you explain"], "max_iterations": 3}'),
('api_timeout', 'Simulate external API timeouts and failures', 'integration', '{"timeout_probability": 0.2, "services": ["external_api", "database"], "delay_range": [5, 30]}'),
('token_exhaustion', 'Simulate hitting token limits during processing', 'resource', '{"token_limit": 1000, "exhaustion_probability": 0.15}'),
('reasoning_failure', 'Agent provides logically inconsistent responses', 'output_quality', '{"contradiction_probability": 0.25, "logic_error_types": ["false_premise", "invalid_conclusion"]}'),
('stuck_pattern', 'Agent refuses to progress without perfect information', 'behavioral', '{"perfectionism_threshold": 0.9, "clarification_loop_limit": 5}');

-- Create indexes for better query performance
CREATE INDEX idx_session_id ON agent_interactions(session_id);
CREATE INDEX idx_timestamp ON agent_interactions(timestamp);
CREATE INDEX idx_status ON agent_interactions(status);
CREATE INDEX idx_natural_status ON agent_interactions(natural_status);
CREATE INDEX idx_failure_mode ON agent_interactions(failure_mode);
CREATE INDEX idx_failure_injection_applied ON agent_interactions(failure_injection_applied);
CREATE INDEX idx_interaction_id ON recovery_attempts(interaction_id);
CREATE INDEX idx_strategy ON recovery_attempts(recovery_strategy);
CREATE INDEX idx_success ON recovery_attempts(success);
CREATE INDEX idx_snapshot_session_id ON agent_state_snapshots(session_id);
CREATE INDEX idx_snapshot_type ON agent_state_snapshots(snapshot_type);
CREATE INDEX idx_snapshot_timestamp ON agent_state_snapshots(timestamp);
CREATE INDEX idx_metric_type ON system_metrics(metric_type);
CREATE INDEX idx_metric_timestamp ON system_metrics(timestamp);
CREATE INDEX idx_exceeded_threshold ON system_metrics(exceeded_threshold);
CREATE INDEX idx_interactions_session_status ON agent_interactions(session_id, status);
CREATE INDEX idx_interactions_failure_timestamp ON agent_interactions(failure_mode, timestamp);
CREATE INDEX idx_recovery_attempts_composite ON recovery_attempts(interaction_id, recovery_strategy, success);

-- Create a view for failure analysis
CREATE VIEW failure_analysis AS
SELECT 
    ai.session_id,
    ai.timestamp,
    ai.failure_mode,
    ai.processing_time_ms,
    ai.token_count,
    COUNT(ra.id) as recovery_attempts,
    BOOL_OR(ra.success) as recovery_successful,
    AVG(ra.attempt_number) as avg_attempts_to_recovery
FROM agent_interactions ai
LEFT JOIN recovery_attempts ra ON ai.id = ra.interaction_id
WHERE ai.status = 'failure'
GROUP BY ai.id, ai.session_id, ai.timestamp, ai.failure_mode, ai.processing_time_ms, ai.token_count;

-- Create a view for system health monitoring
CREATE VIEW system_health AS
SELECT 
    metric_type,
    AVG(metric_value) as avg_value,
    MAX(metric_value) as max_value,
    COUNT(*) FILTER (WHERE exceeded_threshold = true) as threshold_violations,
    COUNT(*) as total_measurements
FROM system_metrics 
WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '1 hour'
GROUP BY metric_type;