"""
Behavioral Monitoring Service - Service Layer for Behavioral Anomaly Detection

This service orchestrates behavioral tracking, anomaly detection, metrics recording,
and database persistence while keeping core behavioral logic classes pure.
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from ..models import AgentRequest, AgentResponse, InteractionBehavior
from ..metrics import MetricsCollector
from ..database import AsyncSession, InteractionBehaviorLog, BehavioralAnomalyLog, BehavioralBaseline
from .interaction_tracker import InteractionTracker
from .baseline_manager import BaselineManager
from .temporal_analyzer import TemporalBehaviorAnalyzer
from .anomaly_detector import AnomalyDetector

logger = structlog.get_logger(__name__)


class BehavioralMonitoringService:
    """
    Service layer for behavioral monitoring.

    Orchestrates pure behavioral logic classes with infrastructure concerns
    like metrics collection and database persistence using existing database infrastructure.
    """

    def __init__(self,
                 metrics_collector: Optional[MetricsCollector] = None,
                 db_session: Optional[AsyncSession] = None):
        """
        Initialize behavioral monitoring service.

        Args:
            metrics_collector: Prometheus metrics collector
            db_session: Database session for persistence (uses existing database.py infrastructure)
        """
        self.metrics_collector = metrics_collector
        self.db_session = db_session

        # Initialize pure behavioral logic components
        self.interaction_tracker = InteractionTracker()
        self.baseline_manager = BaselineManager()
        self.temporal_analyzer = TemporalBehaviorAnalyzer()
        self.anomaly_detector = AnomalyDetector(
            baseline_manager=self.baseline_manager,
            temporal_analyzer=self.temporal_analyzer
        )

        # Configuration from environment
        self.metrics_enabled = os.getenv('BEHAVIORAL_METRICS_ENABLED', 'true').lower() == 'true'
        self.db_persistence_enabled = os.getenv('BEHAVIORAL_DB_PERSISTENCE_ENABLED', 'true').lower() == 'true'

    async def process_interaction(self,
                                session_id: str,
                                request: AgentRequest,
                                response: AgentResponse,
                                start_time: float) -> Dict[str, Any]:
        """
        Complete behavioral monitoring pipeline for a single interaction.

        Args:
            session_id: Session identifier
            request: Agent request
            response: Agent response
            start_time: When processing started

        Returns:
            Dict containing behavioral analysis results
        """
        try:
            # 1. Track interaction behavior (pure logic)
            behavior = self.interaction_tracker.track_interaction(
                session_id, request, response, start_time
            )

            # 2. Get session history for anomaly detection
            session_behaviors = self.interaction_tracker.get_recent_behaviors(session_id)
            recent_responses = self.interaction_tracker.get_recent_responses(session_id)

            # 3. Detect anomalies (pure logic)
            anomaly_results = self.anomaly_detector.detect_anomalies(
                session_id, behavior, session_behaviors, recent_responses
            )

            # 4. Infrastructure concerns (metrics & persistence)
            if self.metrics_enabled and self.metrics_collector:
                await self._record_metrics(behavior, anomaly_results)

            if self.db_persistence_enabled and self.db_session:
                await self._persist_data(behavior, anomaly_results)

            # 5. Return comprehensive results
            return {
                "behavior": behavior.model_dump(),
                "anomaly_results": anomaly_results,
                "session_metrics": self.interaction_tracker.get_session_metrics(session_id),
                "monitoring_metadata": {
                    "metrics_recorded": self.metrics_enabled and self.metrics_collector is not None,
                    "data_persisted": self.db_persistence_enabled and self.db_session is not None,
                    "processing_timestamp": datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error("Behavioral monitoring failed",
                        session_id=session_id,
                        error=str(e))
            # Return minimal safe response
            return {
                "behavior": None,
                "anomaly_results": {"anomalies_detected": [], "overall_anomaly_score": 0.0},
                "session_metrics": {},
                "monitoring_metadata": {"error": str(e)}
            }

    async def _record_metrics(self, behavior: InteractionBehavior, anomaly_results: Dict[str, Any]) -> None:
        """Record behavioral metrics to Prometheus using existing MetricsCollector."""
        try:
            # Record interaction metrics
            self.metrics_collector.increment_counter('interaction_total', {
                'session_type': 'behavioral'
            })

            # Record response latency
            self.metrics_collector.observe_histogram('interaction_latency',
                                                   behavior.response_latency_ms / 1000.0,
                                                   {'metric_type': 'response_latency'})

            # Record message length
            self.metrics_collector.observe_histogram('message_length_histogram',
                                                   behavior.message_length,
                                                   {'metric_type': 'message_length'})

            # Record behavioral consistency
            self.metrics_collector.observe_histogram('interaction_consistency_score',
                                                   1.0 - behavior.clarification_frequency,
                                                   {'session_id': behavior.session_id[:8]})

            # Record topic switches
            if behavior.topic_switches > 0:
                self.metrics_collector.increment_counter('conversation_flow_disruptions_total', {
                    'disruption_type': 'topic_switch'
                })

            # Record anomaly metrics
            if anomaly_results["anomalies_detected"]:
                for anomaly in anomaly_results["anomalies_detected"]:
                    self.metrics_collector.record_behavioral_anomaly(
                        session_id=behavior.session_id,
                        anomaly_type=anomaly["type"],
                        score=anomaly["score"]
                    )

                    # Specific disruption counters
                    if anomaly["type"] == "response_loop":
                        loop_type = anomaly.get("details", {}).get("loop_type", "unknown")
                        self.metrics_collector.record_conversation_flow_disruption(f"loop_{loop_type}")
                    elif anomaly["type"] == "baseline_deviation":
                        self.metrics_collector.record_conversation_flow_disruption("baseline_deviation")
                    elif anomaly["type"] == "temporal_drift":
                        drift_type = anomaly.get("details", {}).get("drift_type", "unknown")
                        self.metrics_collector.record_behavioral_drift(drift_type, anomaly["score"], 1)

            logger.debug("Recorded behavioral metrics",
                        session_id=behavior.session_id,
                        anomaly_count=len(anomaly_results["anomalies_detected"]))

        except Exception as e:
            logger.warning("Failed to record behavioral metrics",
                          session_id=behavior.session_id,
                          error=str(e))

    async def _persist_data(self, behavior: InteractionBehavior, anomaly_results: Dict[str, Any]) -> None:
        """Persist behavioral data using existing database.py infrastructure."""
        try:
            # Persist interaction behavior using existing InteractionBehaviorLog model
            behavior_record = InteractionBehaviorLog(
                session_id=behavior.session_id,
                timestamp=behavior.timestamp,
                response_latency_ms=behavior.response_latency_ms,
                message_length=behavior.message_length,
                conversation_turns=behavior.conversation_turns,
                clarification_frequency=float(behavior.clarification_frequency),
                topic_switches=behavior.topic_switches,
                confidence_expressions=behavior.confidence_expressions,
                # Store anomaly score if available
                anomaly_score=float(anomaly_results["overall_anomaly_score"]) if anomaly_results["overall_anomaly_score"] else None,
                metadata={
                    'tracked_at': behavior.timestamp.isoformat(),
                    'service_version': '1.0',
                    'monitoring_service': 'BehavioralMonitoringService'
                }
            )
            self.db_session.add(behavior_record)

            # Persist anomalies using existing BehavioralAnomalyLog model
            if anomaly_results["anomalies_detected"]:
                for anomaly in anomaly_results["anomalies_detected"]:
                    anomaly_record = BehavioralAnomalyLog(
                        session_id=behavior.session_id,
                        timestamp=anomaly_results["timestamp"],
                        anomaly_type=anomaly["type"],
                        anomaly_score=float(anomaly["score"]),
                        confidence=float(anomaly_results["confidence"]),
                        detection_method="service_layer_multi_tier",
                        contributing_factors=anomaly.get("details", {}),
                        recommendations=anomaly_results["recommendations"],
                        resolved=False  # Will be updated by ops team
                    )
                    self.db_session.add(anomaly_record)

            # Persist/update baseline using existing BehavioralBaseline model
            await self._update_baseline_if_needed(behavior)

            logger.debug("Queued behavioral data for database persistence",
                        session_id=behavior.session_id,
                        anomaly_count=len(anomaly_results["anomalies_detected"]))

        except Exception as e:
            logger.warning("Failed to persist behavioral data",
                          session_id=behavior.session_id,
                          error=str(e))

    async def _update_baseline_if_needed(self, behavior: InteractionBehavior) -> None:
        """Update behavioral baseline using existing BehavioralBaseline model."""
        try:
            session_behaviors = self.interaction_tracker.get_recent_behaviors(behavior.session_id)

            # Check if we should establish/update baseline
            if len(session_behaviors) >= self.baseline_manager.min_interactions:
                baseline = self.baseline_manager.establish_baseline(
                    behavior.session_id, session_behaviors
                )

                if baseline:
                    # Use existing BehavioralBaseline model structure
                    db_baseline = BehavioralBaseline(
                        session_id=baseline.session_id,
                        avg_response_latency=float(baseline.avg_response_latency),
                        typical_message_length_min=baseline.typical_message_length_range[0],
                        typical_message_length_max=baseline.typical_message_length_range[1],
                        normal_clarification_rate=float(baseline.normal_clarification_rate),
                        standard_conversation_depth=baseline.standard_conversation_depth,
                        confidence_pattern=baseline.confidence_pattern,
                        interaction_count=len(session_behaviors)
                    )

                    # Upsert baseline (update if exists, insert if not)
                    self.db_session.merge(db_baseline)

        except Exception as e:
            logger.warning("Failed to update baseline",
                          session_id=behavior.session_id,
                          error=str(e))

    def get_session_analysis(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive behavioral analysis for a session."""
        try:
            session_metrics = self.interaction_tracker.get_session_metrics(session_id)
            recent_behaviors = self.interaction_tracker.get_recent_behaviors(session_id)
            baseline = self.baseline_manager.get_baseline(session_id)

            return {
                "session_id": session_id,
                "metrics": session_metrics,
                "recent_behaviors": [b.model_dump() for b in recent_behaviors],
                "baseline": baseline.model_dump() if baseline else None,
                "analysis_timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error("Failed to get session analysis",
                        session_id=session_id,
                        error=str(e))
            return {"error": str(e)}

    def clear_session_data(self, session_id: str) -> None:
        """Clear in-memory behavioral data for a session (database data persists)."""
        self.interaction_tracker.clear_session_data(session_id)
        # Note: Database data persists according to retention policies

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get status of behavioral monitoring service."""
        return {
            "service_active": True,
            "metrics_enabled": self.metrics_enabled,
            "db_persistence_enabled": self.db_persistence_enabled,
            "tracked_sessions": len(self.interaction_tracker.get_all_session_ids()),
            "baseline_count": len(self.baseline_manager.baselines),
            "configuration": {
                "min_interactions_for_baseline": self.baseline_manager.min_interactions,
                "anomaly_threshold": self.anomaly_detector.anomaly_threshold,
                "drift_threshold": self.anomaly_detector.drift_threshold
            },
            "database_integration": {
                "uses_existing_models": True,
                "behavior_log_table": "interaction_behaviors",
                "anomaly_log_table": "behavioral_anomalies",
                "baseline_table": "behavioral_baselines"
            }
        }