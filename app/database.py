import os
import asyncio
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, Boolean, DateTime, Numeric, JSON, Index
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
import structlog

logger = structlog.get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agent_user:agent_password@localhost:5432/agent_failures")
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class AgentInteraction(Base):
    __tablename__ = "agent_interactions"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    request_data = Column(JSON, nullable=False)
    response_data = Column(JSON)
    status = Column(String(50), nullable=False, index=True)
    natural_status = Column(String(50), nullable=False, index=True)  # What LLM actually produced
    failure_mode = Column(String(100), index=True)
    failure_injection_applied = Column(Boolean, default=False, index=True)
    natural_response = Column(Text)  # Original LLM response before injection
    processing_time_ms = Column(Integer)
    token_count = Column(Integer)
    model_used = Column(String(100))


class FailureScenario(Base):
    __tablename__ = "failure_scenarios"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    failure_type = Column(String(100), nullable=False)
    config = Column(JSON, nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"
    
    id = Column(Integer, primary_key=True)
    interaction_id = Column(Integer, nullable=False, index=True)
    recovery_strategy = Column(String(100), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    success = Column(Boolean, nullable=False, index=True)
    recovery_data = Column(JSON)
    notes = Column(Text)


class AgentStateSnapshot(Base):
    __tablename__ = "agent_state_snapshots"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False, index=True)
    snapshot_type = Column(String(50), nullable=False, index=True)
    state_data = Column(JSON, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    metric_type = Column(String(100), nullable=False, index=True)
    metric_value = Column(Numeric(10,2), nullable=False)
    threshold_value = Column(Numeric(10,2))
    exceeded_threshold = Column(Boolean, default=False, index=True)
    metric_metadata = Column(JSON)


class InteractionBehaviorLog(Base):
    __tablename__ = "interaction_behaviors"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False, index=True)
    interaction_id = Column(Integer)  # Foreign key to agent_interactions
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Behavioral metrics
    response_latency_ms = Column(Integer, nullable=False)
    message_length = Column(Integer, nullable=False)
    conversation_turns = Column(Integer, nullable=False)
    clarification_frequency = Column(Numeric(5,3), nullable=False)
    topic_switches = Column(Integer, nullable=False)
    confidence_expressions = Column(Integer, nullable=False)

    # Anomaly detection results
    anomaly_score = Column(Numeric(5,3))
    baseline_deviation = Column(Numeric(5,3))
    drift_score = Column(Numeric(5,3))

    # Metadata
    interaction_metadata = Column(JSON)


class BehavioralBaseline(Base):
    __tablename__ = "behavioral_baselines"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)

    # Baseline metrics
    avg_response_latency = Column(Numeric(10,2), nullable=False)
    typical_message_length_min = Column(Integer, nullable=False)
    typical_message_length_max = Column(Integer, nullable=False)
    normal_clarification_rate = Column(Numeric(5,3), nullable=False)
    standard_conversation_depth = Column(Integer, nullable=False)
    confidence_pattern = Column(JSON, nullable=False)

    # Metadata
    interaction_count = Column(Integer, nullable=False)
    established_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BehavioralAnomalyLog(Base):
    __tablename__ = "behavioral_anomalies"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False, index=True)
    interaction_id = Column(Integer)  # Foreign key to agent_interactions
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Anomaly details
    anomaly_type = Column(String(100), nullable=False, index=True)
    anomaly_score = Column(Numeric(5,3), nullable=False)
    confidence = Column(Numeric(5,3), nullable=False)

    # Detection details
    detection_method = Column(String(100), nullable=False)
    contributing_factors = Column(JSON)
    recommendations = Column(JSON)

    # Resolution
    resolved = Column(Boolean, default=False, index=True)
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime(timezone=True))


async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def close_db():
    await engine.dispose()
    logger.info("Database connection closed")


async def get_db_session():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()