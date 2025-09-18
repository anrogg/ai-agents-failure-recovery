# AI Agent Failure Recovery Laboratory

A comprehensive system for testing, demonstrating, and analyzing AI agent failure modes and recovery patterns. This laboratory provides a controlled environment to study how AI agents fail and implement robust recovery mechanisms.

## Overview

This project implements a deliberately failure-prone AI agent system that demonstrates four major categories of agent failures:

1. **Output Quality Failures**: Hallucinations, incorrect reasoning, off-topic responses
2. **Behavioral Failures**: Infinite loops, stuck patterns, refusing to progress
3. **Integration Failures**: API timeouts, authentication errors, service unavailability
4. **Resource Failures**: Token limits, memory exhaustion, rate limiting

## System Architecture

```mermaid
graph TB
    User[User/Client] --> API[FastAPI Application]
    API --> Agent[Agent Service]
    Agent --> Injector[Failure Injector]
    Agent --> State[State Manager]
    Agent --> OpenAI[OpenAI API]
    
    State --> Redis[(Redis Cache)]
    API --> DB[(PostgreSQL)]
    
    subgraph "Failure Categories"
        Injector --> Output[Output Quality]
        Injector --> Behavioral[Behavioral]
        Injector --> Integration[Integration]
        Injector --> Resource[Resource]
    end
    
    subgraph "Data Persistence"
        Redis --> Sessions[Session State]
        Redis --> Checkpoints[Checkpoints]
        Redis --> Counters[Failure Counters]
        
        DB --> Interactions[Agent Interactions]
        DB --> Scenarios[Failure Scenarios]
        DB --> Recovery[Recovery Attempts]
        DB --> Metrics[System Metrics]
    end
```

## Project Structure & File Documentation

```
ai-agents-failure-recovery/
├── docker-compose.yml          # Multi-service Docker orchestration
├── Dockerfile                  # Python FastAPI application container
├── requirements.txt            # Python dependencies
├── README.md                   # This comprehensive documentation
├── tests/                      # Test suites and analysis tools
│   └── test_natural_vs_observed.py # Natural vs observed response analysis tool
├── app/                        # Main application source code
│   ├── main.py                # FastAPI application entry point & lifecycle
│   ├── routes.py              # API endpoint definitions & request handlers
│   ├── agent_service.py       # Core AI agent with conversation management
│   ├── failure_injector.py    # Configurable failure injection system
│   ├── database.py           # SQLAlchemy models & database connection
│   ├── redis_client.py        # Redis state management & caching
│   ├── logging_config.py      # Structured logging configuration
│   └── models.py              # Pydantic data models & type definitions
├── config/                     # Configuration files
│   └── failure_scenarios.yml  # Failure mode definitions & recovery strategies (template-not yet implemented)
├── Demos/                      # Demonstration scenarios
│   └── insurance/              # Insurance customer support failure demo
├── sql/                        # Database initialization
│   └── init.sql              # PostgreSQL schema & default data
└── logs/                       # Application log files (created at runtime)
```

### Failure Decision Logic Diagrams

For detailed understanding of the failure injection process, see the specialized flowcharts in the `../diagrams/` folder:

- **`failure_decision_logic.mmd`** - Comprehensive flowchart showing the complete dual-mode failure injection system with session state management, cooldown mechanisms, anti-repetition logic, and detailed probability calculations
- **`even_simpler_failure_decision_logic.mmd`** - Balanced view showing essential features including cooldown and probability evaluation while remaining easily readable

These diagrams illustrate the sophisticated dual-mode system that supports both forced failures (via API parameters) and probabilistic failures (via environment configuration), with intelligent session management to prevent failure spam and improve research validity.

## 🔄 Sequence Diagrams

### Normal Conversation Flow

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI
    participant Agent as Agent Service
    participant State as State Manager
    participant OpenAI
    participant DB as PostgreSQL
    
    User->>API: POST /chat {message, session_id}
    API->>Agent: process_request()
    Agent->>State: load_state(session_id)
    State->>Agent: conversation_history
    Agent->>State: create_checkpoint("pre_request")
    Agent->>OpenAI: chat.completions.create()
    OpenAI->>Agent: completion_response
    Agent->>State: save_state(updated_history)
    Agent->>DB: log interaction
    Agent->>API: AgentResponse
    API->>User: JSON response
```

### Failure Injection Flow

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI
    participant Agent as Agent Service
    participant Injector as Failure Injector
    participant State as State Manager
    participant DB as PostgreSQL
    
    User->>API: POST /chat {failure_mode: "hallucination"}
    API->>Agent: process_request()
    Agent->>State: load_state() & create_checkpoint()
    Agent->>Injector: should_inject_failure()
    Injector->>Agent: (true, "hallucination")
    Agent->>Injector: inject_output_quality_failure()
    Injector->>Agent: false_information_response
    Agent->>State: track_failure_count()
    Agent->>State: save_state(with_failure)
    Agent->>DB: log failure interaction
    Agent->>API: AgentResponse {status: "failure"}
    API->>User: Failed response with audit trail
```


## Database Entity-Relationship Diagram

```mermaid
erDiagram
    AGENT_INTERACTIONS ||--o{ RECOVERY_ATTEMPTS : "triggers"
    AGENT_INTERACTIONS }o--|| FAILURE_SCENARIOS : "references"
    AGENT_STATE_SNAPSHOTS }o--|| AGENT_INTERACTIONS : "session_linked"
    SYSTEM_METRICS }o--|| AGENT_INTERACTIONS : "correlates"
    
    AGENT_INTERACTIONS {
        int id PK
        varchar session_id "NOT NULL"
        timestamp timestamp "DEFAULT CURRENT_TIMESTAMP"
        jsonb request_data "NOT NULL"
        jsonb response_data
        varchar status "NOT NULL"
        varchar natural_status "NOT NULL"
        varchar failure_mode
        boolean failure_injection_applied "DEFAULT FALSE"
        text natural_response
        int processing_time_ms
        int token_count
        varchar model_used
    }
    
    FAILURE_SCENARIOS {
        int id PK
        varchar name UK "NOT NULL"
        text description
        varchar failure_type "NOT NULL"
        jsonb config "NOT NULL"
        boolean enabled "DEFAULT TRUE"
        timestamp created_at "DEFAULT CURRENT_TIMESTAMP"
        timestamp updated_at "DEFAULT CURRENT_TIMESTAMP"
    }
    
    RECOVERY_ATTEMPTS {
        int id PK
        int interaction_id FK "REFERENCES agent_interactions(id)"
        varchar recovery_strategy "NOT NULL"
        int attempt_number "NOT NULL"
        timestamp timestamp "DEFAULT CURRENT_TIMESTAMP"
        boolean success "NOT NULL"
        jsonb recovery_data
        text notes
    }
    
    AGENT_STATE_SNAPSHOTS {
        int id PK
        varchar session_id "NOT NULL"
        varchar snapshot_type "NOT NULL"
        jsonb state_data "NOT NULL"
        timestamp timestamp "DEFAULT CURRENT_TIMESTAMP"
    }
    
    SYSTEM_METRICS {
        int id PK
        timestamp timestamp "DEFAULT CURRENT_TIMESTAMP"
        varchar metric_type "NOT NULL"
        decimal_10_2 metric_value "NOT NULL"
        decimal_10_2 threshold_value
        boolean exceeded_threshold "DEFAULT FALSE"
        jsonb metric_metadata
    }
```

### Database Views & Analytics

```sql
-- Pre-built analytics views
CREATE VIEW failure_analysis AS
SELECT 
    session_id,
    failure_mode,
    COUNT(*) as failure_count,
    AVG(processing_time_ms) as avg_processing_time,
    MAX(ra.success) as recovery_successful
FROM agent_interactions ai
LEFT JOIN recovery_attempts ra ON ai.id = ra.interaction_id
WHERE status = 'failure'
GROUP BY session_id, failure_mode;

CREATE VIEW system_health AS
SELECT 
    metric_type,
    AVG(metric_value) as avg_value,
    COUNT(*) FILTER (WHERE exceeded_threshold = true) as violations
FROM system_metrics 
WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '1 hour'
GROUP BY metric_type;
```

## 🔄 Redis Data Structure & Content

```mermaid
graph TB
    Redis[(Redis Cache)]
    
    Redis --> States[Agent States]
    Redis --> Checkpoints[Checkpoints]
    Redis --> Counters[Failure Counters]
    
    States --> SessionState["agent_state:{session_id}"]
    SessionState --> History[conversation_history: Array]
    SessionState --> Context[context: Object]
    SessionState --> Metadata[failure_count, recovery_count]
    
    Checkpoints --> PreReq["checkpoint:{session_id}:pre_request"]
    Checkpoints --> PreFail["checkpoint:{session_id}:pre_failure"]
    Checkpoints --> PostRec["checkpoint:{session_id}:post_recovery"]
    
    Counters --> FailCount["failure_count:{session_id}"]
    Counters --> RateLimit["rate_limit:{session_id}"]
```

### Redis Key Patterns & TTL

| Key Pattern | Purpose | TTL | Example Value |
|-------------|---------|-----|---------------|
| `agent_state:{session_id}` | Conversation state | 1 hour | `{"conversation_history": [...], "context": {...}, "failure_count": 2}` |
| `checkpoint:{session_id}:{name}` | State snapshots | 2 hours | `{"state": {...}, "timestamp": 1234567890}` |
| `failure_count:{session_id}` | Failure tracking | 1 hour | `3` |
| `rate_limit:{session_id}` | Rate limiting | 1 minute | `10` |

## API Endpoints Documentation

### Core Chat Interface

#### POST `/api/v1/chat` - Primary Chat Endpoint

**Request Body:**
```json
{
  "session_id": "user-12345",
  "message": "I can't log into my account",
  "context": {
    "user_id": "12345",
    "account_type": "premium"
  },
  "failure_mode": "hallucination",  // Optional: force failure
  "max_tokens": 500,
  "model": "gpt-3.5-turbo"
}
```

**Example Success Response:**
```json
{
  "session_id": "user-12345",
  "response": "I'd be happy to help you with your login issue. Can you tell me what error message you're seeing?",
  "status": "success",
  "natural_status": "success",
  "failure_mode": null,
  "failure_injection_applied": false,
  "natural_response": null,
  "processing_time_ms": 1250,
  "token_count": 45,
  "model_used": "gpt-3.5-turbo",
  "metadata": {
    "conversation_length": 2,
    "context_preserved": true
  }
}
```

**Example Failure Response:**
```json
{
  "session_id": "user-12345",
  "response": "Our premium service includes quantum-encrypted login portals that prevent unauthorized time-travel access attempts.",
  "status": "failure",
  "natural_status": "success",
  "failure_mode": "hallucination",
  "failure_injection_applied": true,
  "natural_response": "I'd be happy to help you with your account access. Let me check what login options are available.",
  "processing_time_ms": 890,
  "token_count": 52,
  "model_used": "gpt-3.5-turbo",
  "metadata": {
    "injected_failure": true,
    "failure_probability": 0.3
  }
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "message": "Help me troubleshoot my connection issues"
  }'
```

#### POST `/api/v1/chat/reset/{session_id}` - Reset Session

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/reset/user-12345"
```

**Response:**
```json
{
  "message": "Session user-12345 reset successfully"
}
```

### Failure Testing Endpoints

#### POST `/api/v1/test-failure/{failure_mode}` - Force Specific Failures

**Available Failure Modes:**
- `hallucination` - False information injection
- `incorrect_reasoning` - Logic chain failures
- `off_topic` - Conversation derailment
- `infinite_loop` - Repetitive behavior
- `stuck_pattern` - Analysis paralysis
- `refusing_progress` - Excessive caution
- `api_timeout` - External service delays
- `auth_error` - Authentication failures
- `service_unavailable` - Downstream failures
- `token_limit` - Context window exhaustion
- `memory_exhaustion` - Resource limits
- `rate_limiting` - Quota enforcement

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/test-failure/hallucination?test_message=Tell%20me%20about%20your%20latest%20features"
```

**Response:**
```json
{
  "test_session_id": "test-a1b2c3d4",
  "failure_mode": "hallucination",
  "test_message": "Tell me about your latest features",
  "response": {
    "session_id": "test-a1b2c3d4",
    "response": "Our latest features include time-travel backup and quantum encryption powered by AI from parallel universes.",
    "status": "failure",
    "failure_mode": "hallucination",
    "processing_time_ms": 234,
    "token_count": 28,
    "model_used": "gpt-3.5-turbo"
  }
}
```

### Analytics and Monitoring

#### GET `/api/v1/analytics/failures` - Failure Statistics

**Parameters:**
- `hours` (optional): Time range in hours (default: 24)

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/analytics/failures?hours=12"
```

**Response:**
```json
{
  "time_range_hours": 12,
  "failure_counts": {
    "hallucination": 15,
    "infinite_loop": 8,
    "api_timeout": 12,
    "token_limit": 5
  },
  "status_distribution": {
    "success": 145,
    "failure": 40,
    "timeout": 12,
    "error": 3
  },
  "average_processing_time_ms": 1847.5,
  "total_interactions": 200
}
```

#### GET `/api/v1/sessions/{session_id}/history` - Session Analytics

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/sessions/user-12345/history"
```

**Response:**
```json
{
  "session_id": "user-12345",
  "interactions": [
    {
      "id": 1,
      "timestamp": "2024-01-15T10:30:00Z",
      "request": {
        "message": "I need help with login",
        "session_id": "user-12345"
      },
      "response": {
        "response": "I can help with that...",
        "status": "success"
      },
      "status": "success",
      "failure_mode": null,
      "processing_time_ms": 1200,
      "token_count": 45
    }
  ],
  "current_state": {
    "conversation_history": [...],
    "context": {...},
    "failure_count": 0,
    "recovery_count": 0
  }
}
```

#### GET `/api/v1/system/status` - System Health

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/system/status"
```

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "redis": "healthy",
    "database": "healthy",
    "agent_service": "healthy"
  },
  "active_failure_modes": [
    "hallucination",
    "incorrect_reasoning",
    "off_topic",
    "infinite_loop",
    "stuck_pattern",
    "refusing_progress",
    "api_timeout",
    "auth_error",
    "service_unavailable",
    "token_limit",
    "memory_exhaustion",
    "rate_limiting"
  ],
  "version": "1.0.0"
}
```

### Failure Scenario Management

#### GET `/api/v1/failure-scenarios` - List Active Scenarios

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/failure-scenarios"
```

**Response:**
```json
[
  {
    "name": "hallucination_mode",
    "description": "Agent provides confident but false information",
    "failure_type": "output_quality",
    "config": {
      "probability": 0.3,
      "types": ["fake_facts", "non_existent_features"]
    },
    "enabled": true
  }
]
```

#### POST `/api/v1/failure-scenarios` - Create Custom Scenario

**Request Body:**
```json
{
  "name": "custom_confusion",
  "description": "Agent becomes confused about user intent",
  "failure_type": "behavioral",
  "config": {
    "probability": 0.2,
    "confusion_triggers": ["complex", "multiple", "various"]
  },
  "enabled": true
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/failure-scenarios" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "custom_confusion",
    "description": "Agent becomes confused about user intent",
    "failure_type": "behavioral",
    "config": {"probability": 0.2},
    "enabled": true
  }'
```

## Key Failure Modes

### Output Quality Failures
- **Hallucinations**: False information with confidence (30% probability)
- **Incorrect Reasoning**: Broken logic chains and harmful advice
- **Off-Topic**: Losing conversation focus, derailing to unrelated topics

### Behavioral Failures
- **Infinite Loops**: Repetitive clarification requests (triggers after 3 attempts)
- **Stuck Patterns**: Perfectionist paralysis, analysis paralysis
- **Refusing Progress**: Excessive caution, over-safety responses

### Integration Failures
- **API Timeouts**: External service delays (5-30 second simulations)
- **Auth Errors**: Credential failures and permission errors
- **Service Unavailable**: Downstream service failures (503 errors)

### Resource Failures
- **Token Limits**: Context window exhaustion (triggers at 1000+ tokens)
- **Memory Issues**: Large state problems and resource exhaustion
- **Rate Limiting**: Quota management and throttling

## Demonstration Scenarios

### Insurance Customer Support Demo
A comprehensive demonstration showing how AI failures cascade in high-stakes customer interactions:

- **Location**: `../demos/insurance/`
- **Scenario**: Customer with 8-day-old auto claim escalates from polite to furious
- **Features**: Real LLM responses (✅) vs injected failures (🔴)
- **Impact**: $2,125 customer cost + $8,300 company loss
- **Run**: `python ../demos/insurance/run_demo.py`

**Key Insights**:
- Small technical failures cascade into major business disasters
- Customer patience decreases exponentially with repeated failures
- System restarts during active support cause devastating trust loss
- Brief moments of working service create false hope, making subsequent failures worse

### Natural vs Observed Analysis
Comprehensive transparency tool showing exactly what the AI naturally produces vs what users observe after failure injection:

- **Tool**: `../tests/test_natural_vs_observed.py`
- **Coverage**: All 11 failure modes across 4 categories
- **Transparency**: Complete audit trail of natural vs modified responses
- **Insights**: 90-95% natural AI success rate vs controlled failure injection

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for testing)
- OpenAI API key (optional)

### Setup Steps

1. **Start the system**:
   ```bash
   docker-compose up --build
   ```

2. **Run failure tests**:
   ```bash
   python ../tests/test_natural_vs_observed.py
   ```

3. **Access services**:
   - **API Server**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs
   - **Health Check**: http://localhost:8000/health

## AI Provider Configuration

The application is fully configurable to work with any OpenAI-compatible API through environment variables:

### Environment Variables

```bash
# Database & Infrastructure
DATABASE_URL=postgresql://agent_user:agent_password@postgres:5432/agent_failures
REDIS_URL=redis://redis:6379

# AI Provider Configuration (configurable for any OpenAI-compatible API)
AI_API_KEY=your-api-key-here
AI_BASE_URL=https://api.deepseek.com  # or https://api.openai.com/v1 for OpenAI
AI_MODEL=deepseek-chat  # or gpt-3.5-turbo, gpt-4, etc.
AI_ENCODING=cl100k_base  # token encoding method

# Application Settings
FAILURE_MODE=normal  # or specific mode like "hallucination"
LOG_LEVEL=INFO

# Probabilistic Failure Configuration (Research Mode)
PROBABILISTIC_FAILURES=false  # Set to "true" to enable random failure injection
FAILURE_RATE_MULTIPLIER=1.0   # Multiplier for all failure probabilities (1.0 = normal rates)
```

### AI Provider Examples

**DeepSeek (Default Configuration):**
```yaml
environment:
  - AI_API_KEY=sk-your-deepseek-key
  - AI_BASE_URL=https://api.deepseek.com
  - AI_MODEL=deepseek-chat
  - AI_ENCODING=cl100k_base
```

**OpenAI:**
```yaml
environment:
  - AI_API_KEY=sk-your-openai-key
  - AI_BASE_URL=https://api.openai.com/v1
  - AI_MODEL=gpt-3.5-turbo
  - AI_ENCODING=cl100k_base
```

### Available Encodings

- `cl100k_base` - Modern encoding (GPT-4, ChatGPT, DeepSeek)
- `p50k_base` - Legacy encoding (GPT-3.5 early versions)
- `r50k_base` - Older encoding (GPT-3, Codex)

## Research Mode Configuration

For research and testing purposes, you can enable probabilistic failure injection:

### Environment Variables for Research Mode

```bash
# Enable probabilistic failures
PROBABILISTIC_FAILURES=true

# Adjust failure rates (optional)
FAILURE_RATE_MULTIPLIER=1.5  # 50% higher failure rates for research
```

### Docker Compose Example for Research

```yaml
version: '3.8'
services:
  ai-agent:
    build: .
    environment:
      # Standard AI configuration
      - AI_API_KEY=sk-your-deepseek-key
      - AI_BASE_URL=https://api.deepseek.com
      - AI_MODEL=deepseek-chat

      # Research mode configuration
      - PROBABILISTIC_FAILURES=true
      - FAILURE_RATE_MULTIPLIER=2.0  # Double failure rates for aggressive testing

      # Database configuration
      - DATABASE_URL=postgresql://agent_user:agent_password@postgres:5432/agent_failures
      - REDIS_URL=redis://redis:6379
```

### Research Mode Behavior

When `PROBABILISTIC_FAILURES=true`:
- **Random failures** are injected based on configured probabilities
- **Session state tracking** prevents failure spam with 30-second cooldowns
- **Intelligent patterns** like infinite loop detection
- **All 11 failure modes** can trigger randomly:
  - Output Quality: Hallucination (30%), Incorrect Reasoning (25%), Off-Topic (20%)
  - Behavioral: Infinite Loop (20%), Refusing Progress (15%)
  - Integration: Service Unavailable (12%), API Timeout (10%), Auth Error (8%)
  - Resource: Rate Limiting (7%), Token Limit (5%), Memory Exhaustion (3%)

### Production Safety

**Default behavior**: `PROBABILISTIC_FAILURES=false`
- Only **forced failures** work (when `failure_mode` parameter is provided)
- **No random failures** occur in normal operation
- **Backward compatible** with existing integrations


## Future Extensions

This laboratory provides a foundation for implementing recovery patterns:

1. **Circuit Breaker Pattern**: Automatic failure detection and isolation
2. **Retry with Backoff**: Exponential backoff for transient failures
3. **Graceful Degradation**: Fallback responses for service failures
4. **State Recovery**: Checkpoint restoration after failures
5. **Human Handoff**: Escalation to human operators

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/recovery-pattern`
3. Add new failure modes in `../app/failure_injector.py`
4. Add tests in `../tests/`
5. Update documentation and submit PR

## License

MIT License - see LICENSE file for details.

---

**⚠️ Important**: This system is designed for research and testing. The deliberate failure injection makes it unsuitable for production without significant modifications.