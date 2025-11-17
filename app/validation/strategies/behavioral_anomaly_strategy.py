"""
Behavioral anomaly detection validation strategy.

This strategy integrates behavioral anomaly detection into the existing
validation framework, focusing on interaction patterns rather than content quality.
"""

from typing import Any, Dict
from datetime import datetime
import structlog

from ..core import ValidationStrategy, ValidationResult, ValidationLevel
from ...behavioral import InteractionTracker, BaselineManager, TemporalBehaviorAnalyzer, AnomalyDetector
from ...models import AgentRequest, AgentResponse, InteractionBehavior

logger = structlog.get_logger(__name__)


class BehavioralAnomalyStrategy(ValidationStrategy):
    """
    Validation strategy for detecting behavioral anomalies in agent interactions.

    This strategy analyzes interaction patterns, behavioral consistency, and
    temporal changes rather than validating response content quality.
    """

    def __init__(self,
                 interaction_tracker: InteractionTracker = None,
                 baseline_manager: BaselineManager = None,
                 temporal_analyzer: TemporalBehaviorAnalyzer = None,
                 anomaly_threshold: float = 0.7,
                 drift_threshold: float = 0.8):
        """
        Initialize behavioral anomaly strategy.

        Args:
            interaction_tracker: Interaction tracking instance
            baseline_manager: Baseline management instance
            temporal_analyzer: Temporal analysis instance
            anomaly_threshold: Threshold for anomaly detection
            drift_threshold: Threshold for drift detection
        """
        self.interaction_tracker = interaction_tracker or InteractionTracker()
        self.baseline_manager = baseline_manager or BaselineManager()
        self.temporal_analyzer = temporal_analyzer or TemporalBehaviorAnalyzer()

        self.anomaly_detector = AnomalyDetector(
            baseline_manager=self.baseline_manager,
            temporal_analyzer=self.temporal_analyzer,
            anomaly_threshold=anomaly_threshold,
            drift_threshold=drift_threshold
        )

    def validate(self, output: Any, context: Dict[str, Any]) -> ValidationResult:
        """
        Validate agent behavior patterns for anomalies.

        Args:
            output: Agent response (AgentResponse or string)
            context: Validation context containing session info

        Returns:
            ValidationResult: Behavioral anomaly validation results
        """
        try:
            # Extract behavioral context
            session_id = context.get("session_id", "unknown")

            # Get current behavior from context or extract from output
            current_behavior = self._extract_current_behavior(output, context)
            if not current_behavior:
                return ValidationResult(
                    passed=True,
                    confidence=0.5,
                    errors=[],
                    warnings=["Unable to extract behavioral metrics"],
                    validation_level=ValidationLevel.BEHAVIORAL,
                    metadata={"reason": "insufficient_behavioral_data"}
                )

            # Get session behavioral history
            session_behaviors = self.interaction_tracker.get_recent_behaviors(session_id, count=50)

            # Perform comprehensive anomaly detection
            anomaly_results = self.anomaly_detector.detect_anomalies(
                session_id=session_id,
                current_behavior=current_behavior,
                session_behaviors=session_behaviors
            )

            # Convert anomaly results to validation results
            return self._convert_to_validation_result(anomaly_results)

        except Exception as e:
            logger.error("Behavioral anomaly validation failed",
                        session_id=context.get("session_id", "unknown"),
                        error=str(e))

            return ValidationResult(
                passed=False,
                confidence=0.0,
                errors=[f"Behavioral validation error: {str(e)}"],
                warnings=[],
                validation_level=ValidationLevel.BEHAVIORAL,
                metadata={"error": str(e)}
            )

    def _extract_current_behavior(self, output: Any, context: Dict[str, Any]) -> InteractionBehavior:
        """
        Extract current interaction behavior from output and context.

        Args:
            output: Agent response
            context: Validation context

        Returns:
            InteractionBehavior: Current behavior metrics or None
        """
        session_id = context.get("session_id", "unknown")

        # If we have request and response in context, use them
        request = context.get("request")
        response = context.get("response")

        if request and response and hasattr(response, 'processing_time_ms'):
            # Extract from AgentRequest/AgentResponse objects
            start_time = context.get("response_start_time", 0)
            return self.interaction_tracker.track_interaction(
                session_id=session_id,
                request=request,
                response=response,
                start_time=start_time
            )

        # Fallback: create behavior from available context
        response_text = str(output) if output else ""
        processing_time = context.get("processing_time_ms", 0)
        conversation_history = context.get("conversation_history", [])

        return InteractionBehavior(
            session_id=session_id,
            response_latency_ms=processing_time,
            message_length=len(response_text),
            conversation_turns=len(conversation_history),
            clarification_frequency=self._calculate_clarification_frequency(response_text),
            topic_switches=0,  # Cannot determine from single response
            confidence_expressions=self._count_confidence_expressions(response_text),
            timestamp=context.get("timestamp", None) or datetime.now()
        )

    def _convert_to_validation_result(self, anomaly_results: Dict[str, Any]) -> ValidationResult:
        """
        Convert anomaly detection results to validation result format.

        Args:
            anomaly_results: Results from anomaly detector

        Returns:
            ValidationResult: Formatted validation results
        """
        overall_score = anomaly_results.get("overall_anomaly_score", 0.0)
        confidence = anomaly_results.get("confidence", 1.0)
        anomalies = anomaly_results.get("anomalies_detected", [])

        # Determine if validation passed
        passed = overall_score < 0.7  # Configurable threshold

        # Build error messages from detected anomalies
        errors = []
        warnings = []

        for anomaly in anomalies:
            anomaly_type = anomaly.get("type", "unknown")
            score = anomaly.get("score", 0.0)
            description = anomaly.get("description", "Behavioral anomaly detected")

            if score >= 0.8:
                errors.append(f"{description} (score: {score:.2f})")
            else:
                warnings.append(f"{description} (score: {score:.2f})")

        # Add recommendations as warnings
        recommendations = anomaly_results.get("recommendations", [])
        for rec in recommendations:
            if rec not in warnings:
                warnings.append(f"Recommendation: {rec}")

        # Build metadata
        metadata = {
            "overall_anomaly_score": overall_score,
            "anomaly_count": len(anomalies),
            "anomaly_scores": anomaly_results.get("anomaly_scores", {}),
            "confidence": confidence,
            "session_id": anomaly_results.get("session_id"),
            "detection_timestamp": str(anomaly_results.get("timestamp"))
        }

        logger.debug("Behavioral anomaly validation completed",
                    session_id=anomaly_results.get("session_id"),
                    passed=passed,
                    overall_score=overall_score,
                    anomaly_count=len(anomalies),
                    confidence=confidence)

        return ValidationResult(
            passed=passed,
            confidence=confidence,
            errors=errors,
            warnings=warnings,
            validation_level=ValidationLevel.BEHAVIORAL,
            metadata=metadata
        )

    def _calculate_clarification_frequency(self, response_text: str) -> float:
        """Simple clarification frequency calculation."""
        import re

        clarification_patterns = [
            r'\b(could you|can you|please)\s+(clarify|explain)',
            r'\b(what do you mean|unclear)',
            r'\?',  # Questions
        ]

        clarification_count = 0
        response_lower = response_text.lower()

        for pattern in clarification_patterns:
            matches = re.findall(pattern, response_lower)
            clarification_count += len(matches)

        # Normalize by response length
        words = len(response_text.split())
        return clarification_count / max(words / 10, 1)  # Per 10 words

    def _count_confidence_expressions(self, response_text: str) -> int:
        """Count confidence expressions in response."""
        import re

        confidence_patterns = [
            r'\b(I think|I believe|probably|likely|maybe)',
            r'\b(definitely|certainly|absolutely|sure)',
            r'\b(not sure|uncertain|might be)',
        ]

        confidence_count = 0
        response_lower = response_text.lower()

        for pattern in confidence_patterns:
            matches = re.findall(pattern, response_lower)
            confidence_count += len(matches)

        return confidence_count


class InteractionConsistencyStrategy(ValidationStrategy):
    """
    Validation strategy focused on interaction consistency within a session.
    """

    def __init__(self, interaction_tracker: InteractionTracker = None):
        """Initialize interaction consistency strategy."""
        self.interaction_tracker = interaction_tracker or InteractionTracker()

    def validate(self, output: Any, context: Dict[str, Any]) -> ValidationResult:
        """
        Validate interaction consistency for the session.

        Args:
            output: Agent response
            context: Validation context

        Returns:
            ValidationResult: Consistency validation results
        """
        try:
            session_id = context.get("session_id", "unknown")

            # Get session metrics
            session_metrics = self.interaction_tracker.get_session_metrics(session_id)
            interaction_count = session_metrics.get("interaction_count", 0)

            if interaction_count < 3:
                # Not enough data for consistency analysis
                return ValidationResult(
                    passed=True,
                    confidence=0.5,
                    errors=[],
                    warnings=["Insufficient interactions for consistency analysis"],
                    validation_level=ValidationLevel.BEHAVIORAL,
                    metadata={"interaction_count": interaction_count}
                )

            # Get recent behaviors for consistency analysis
            recent_behaviors = self.interaction_tracker.get_recent_behaviors(session_id, count=10)

            # Calculate consistency score
            temporal_analyzer = TemporalBehaviorAnalyzer()
            consistency_score = temporal_analyzer.calculate_consistency_score(recent_behaviors)

            # Determine if validation passed
            passed = consistency_score >= 0.6  # 60% consistency threshold
            confidence = min(interaction_count / 10.0, 1.0)  # Higher confidence with more data

            errors = []
            warnings = []

            if not passed:
                errors.append(f"Low interaction consistency detected (score: {consistency_score:.2f})")
            elif consistency_score < 0.8:
                warnings.append(f"Moderate consistency issues (score: {consistency_score:.2f})")

            metadata = {
                "consistency_score": consistency_score,
                "interaction_count": interaction_count,
                "session_metrics": session_metrics
            }

            return ValidationResult(
                passed=passed,
                confidence=confidence,
                errors=errors,
                warnings=warnings,
                validation_level=ValidationLevel.BEHAVIORAL,
                metadata=metadata
            )

        except Exception as e:
            logger.error("Interaction consistency validation failed",
                        session_id=context.get("session_id", "unknown"),
                        error=str(e))

            return ValidationResult(
                passed=False,
                confidence=0.0,
                errors=[f"Consistency validation error: {str(e)}"],
                warnings=[],
                validation_level=ValidationLevel.BEHAVIORAL,
                metadata={"error": str(e)}
            )