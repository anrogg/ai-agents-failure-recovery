"""
Behavioral baseline management for anomaly detection.

This module establishes and maintains normal behavior patterns for agent sessions,
enabling detection of behavioral deviations and anomalies.
"""

import statistics
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog

from ..models import InteractionBehavior, BehavioralBaseline

logger = structlog.get_logger(__name__)


class BaselineManager:
    """Manages behavioral baselines for agent sessions."""

    def __init__(self, min_interactions: int = 10, update_frequency_hours: int = 6):
        """
        Initialize baseline manager.

        Args:
            min_interactions: Minimum interactions needed to establish baseline
            update_frequency_hours: How often to update existing baselines
        """
        self.min_interactions = min_interactions
        self.update_frequency_hours = update_frequency_hours
        self.baselines: Dict[str, BehavioralBaseline] = {}

    def establish_baseline(
        self,
        session_id: str,
        behaviors: List[InteractionBehavior]
    ) -> Optional[BehavioralBaseline]:
        """
        Establish a behavioral baseline for a session.

        Args:
            session_id: Session identifier
            behaviors: List of interaction behaviors

        Returns:
            Optional[BehavioralBaseline]: Established baseline or None if insufficient data
        """
        if len(behaviors) < self.min_interactions:
            logger.debug("Insufficient interactions for baseline establishment",
                        session_id=session_id,
                        interaction_count=len(behaviors),
                        min_required=self.min_interactions)
            return None

        # Calculate baseline metrics
        response_latencies = [b.response_latency_ms for b in behaviors]
        message_lengths = [b.message_length for b in behaviors]
        clarification_rates = [b.clarification_frequency for b in behaviors]
        conversation_depths = [b.conversation_turns for b in behaviors]
        confidence_expressions = [b.confidence_expressions for b in behaviors]

        # Calculate averages and ranges
        avg_response_latency = statistics.mean(response_latencies)

        # Message length range (min to max for typical range)
        message_lengths_sorted = sorted(message_lengths)
        typical_length_range = (
            message_lengths_sorted[0],
            message_lengths_sorted[-1]
        )

        normal_clarification_rate = statistics.mean(clarification_rates)
        standard_conversation_depth = int(statistics.mean(conversation_depths))

        # Confidence pattern (frequency distribution)
        confidence_pattern = self._analyze_confidence_pattern(confidence_expressions)

        baseline = BehavioralBaseline(
            session_id=session_id,
            avg_response_latency=avg_response_latency,
            typical_message_length_range=typical_length_range,
            normal_clarification_rate=normal_clarification_rate,
            standard_conversation_depth=standard_conversation_depth,
            confidence_pattern=confidence_pattern,
            interaction_count=len(behaviors),
            established_at=datetime.now(),
            last_updated=datetime.now()
        )

        self.baselines[session_id] = baseline

        logger.info("Established behavioral baseline",
                   session_id=session_id,
                   avg_latency=avg_response_latency,
                   typical_length_range=typical_length_range,
                   clarification_rate=normal_clarification_rate,
                   interaction_count=len(behaviors))

        return baseline

    def update_baseline(
        self,
        session_id: str,
        new_behaviors: List[InteractionBehavior]
    ) -> Optional[BehavioralBaseline]:
        """
        Update an existing baseline with new behavior data.

        Args:
            session_id: Session identifier
            new_behaviors: New interaction behaviors

        Returns:
            Optional[BehavioralBaseline]: Updated baseline
        """
        existing_baseline = self.baselines.get(session_id)
        if not existing_baseline:
            return self.establish_baseline(session_id, new_behaviors)

        # Check if update is needed based on time
        time_since_update = datetime.now() - existing_baseline.last_updated
        if time_since_update.total_seconds() < self.update_frequency_hours * 3600:
            return existing_baseline

        # Combine recent behaviors with trend from existing baseline
        # Weight recent data more heavily for adaptive learning
        recent_weight = 0.3  # 30% weight to recent data
        existing_weight = 0.7  # 70% weight to existing baseline

        if new_behaviors:
            # Calculate new metrics
            new_avg_latency = statistics.mean([b.response_latency_ms for b in new_behaviors])
            new_message_lengths = [b.message_length for b in new_behaviors]
            new_clarification_rate = statistics.mean([b.clarification_frequency for b in new_behaviors])
            new_confidence_expressions = [b.confidence_expressions for b in new_behaviors]

            # Update with weighted average
            updated_avg_latency = (
                existing_weight * existing_baseline.avg_response_latency +
                recent_weight * new_avg_latency
            )

            # Update message length range with recent data
            all_lengths = new_message_lengths
            if all_lengths:
                all_lengths_sorted = sorted(all_lengths)
                q1_idx = len(all_lengths_sorted) // 4
                q3_idx = 3 * len(all_lengths_sorted) // 4
                new_length_range = (
                    all_lengths_sorted[q1_idx] if all_lengths_sorted else existing_baseline.typical_message_length_range[0],
                    all_lengths_sorted[q3_idx] if all_lengths_sorted else existing_baseline.typical_message_length_range[1]
                )
                # Blend with existing range
                updated_length_range = (
                    int(existing_weight * existing_baseline.typical_message_length_range[0] +
                        recent_weight * new_length_range[0]),
                    int(existing_weight * existing_baseline.typical_message_length_range[1] +
                        recent_weight * new_length_range[1])
                )
            else:
                updated_length_range = existing_baseline.typical_message_length_range

            updated_clarification_rate = (
                existing_weight * existing_baseline.normal_clarification_rate +
                recent_weight * new_clarification_rate
            )

            # Update confidence pattern
            new_confidence_pattern = self._analyze_confidence_pattern(new_confidence_expressions)
            updated_confidence_pattern = self._blend_confidence_patterns(
                existing_baseline.confidence_pattern,
                new_confidence_pattern,
                existing_weight,
                recent_weight
            )

            updated_baseline = BehavioralBaseline(
                session_id=session_id,
                avg_response_latency=updated_avg_latency,
                typical_message_length_range=updated_length_range,
                normal_clarification_rate=updated_clarification_rate,
                standard_conversation_depth=existing_baseline.standard_conversation_depth,
                confidence_pattern=updated_confidence_pattern,
                interaction_count=existing_baseline.interaction_count + len(new_behaviors),
                established_at=existing_baseline.established_at,
                last_updated=datetime.now()
            )

            self.baselines[session_id] = updated_baseline

            logger.info("Updated behavioral baseline",
                       session_id=session_id,
                       new_avg_latency=updated_avg_latency,
                       new_behaviors_count=len(new_behaviors))

            return updated_baseline

        return existing_baseline

    def detect_deviation(
        self,
        current_behavior: InteractionBehavior,
        baseline: BehavioralBaseline
    ) -> float:
        """
        Detect deviation from behavioral baseline.

        Args:
            current_behavior: Current interaction behavior
            baseline: Established baseline

        Returns:
            float: Deviation score (0.0 = no deviation, 1.0 = maximum deviation)
        """
        deviations = []

        # Response latency deviation
        latency_deviation = abs(current_behavior.response_latency_ms - baseline.avg_response_latency)
        latency_relative_deviation = latency_deviation / max(baseline.avg_response_latency, 1)
        deviations.append(min(latency_relative_deviation, 1.0))

        # Message length deviation
        min_length, max_length = baseline.typical_message_length_range
        if current_behavior.message_length < min_length:
            length_deviation = (min_length - current_behavior.message_length) / max(min_length, 1)
        elif current_behavior.message_length > max_length:
            length_deviation = (current_behavior.message_length - max_length) / max(max_length, 1)
        else:
            length_deviation = 0.0
        deviations.append(min(length_deviation, 1.0))

        # Clarification frequency deviation
        clarification_deviation = abs(
            current_behavior.clarification_frequency - baseline.normal_clarification_rate
        )
        deviations.append(min(clarification_deviation, 1.0))

        # Confidence expression deviation
        baseline_confidence = baseline.confidence_pattern.get('average', 0)
        confidence_deviation = abs(current_behavior.confidence_expressions - baseline_confidence)
        confidence_relative_deviation = confidence_deviation / max(baseline_confidence + 1, 1)
        deviations.append(min(confidence_relative_deviation, 1.0))

        # Overall deviation score (weighted average)
        weights = [0.3, 0.2, 0.3, 0.2]  # latency, length, clarification, confidence
        overall_deviation = sum(d * w for d, w in zip(deviations, weights))

        logger.debug("Calculated behavioral deviation",
                    session_id=current_behavior.session_id,
                    overall_deviation=overall_deviation,
                    latency_deviation=deviations[0],
                    length_deviation=deviations[1],
                    clarification_deviation=deviations[2],
                    confidence_deviation=deviations[3])

        return overall_deviation

    def get_baseline(self, session_id: str) -> Optional[BehavioralBaseline]:
        """Get baseline for a session."""
        return self.baselines.get(session_id)

    def has_baseline(self, session_id: str) -> bool:
        """Check if a session has an established baseline."""
        return session_id in self.baselines

    def remove_baseline(self, session_id: str) -> None:
        """Remove baseline for a session."""
        if session_id in self.baselines:
            del self.baselines[session_id]
            logger.info("Removed behavioral baseline", session_id=session_id)

    def _analyze_confidence_pattern(self, confidence_expressions: List[int]) -> Dict[str, float]:
        """
        Analyze confidence expression patterns.

        Args:
            confidence_expressions: List of confidence expression counts

        Returns:
            Dict: Confidence pattern analysis
        """
        if not confidence_expressions:
            return {"average": 0.0, "variance": 0.0, "max": 0, "min": 0}

        return {
            "average": statistics.mean(confidence_expressions),
            "variance": statistics.variance(confidence_expressions) if len(confidence_expressions) > 1 else 0.0,
            "max": max(confidence_expressions),
            "min": min(confidence_expressions)
        }

    def _blend_confidence_patterns(
        self,
        existing_pattern: Dict[str, float],
        new_pattern: Dict[str, float],
        existing_weight: float,
        new_weight: float
    ) -> Dict[str, float]:
        """Blend two confidence patterns with weights."""
        blended = {}
        for key in existing_pattern:
            if key in new_pattern:
                blended[key] = (
                    existing_weight * existing_pattern[key] +
                    new_weight * new_pattern[key]
                )
            else:
                blended[key] = existing_pattern[key]
        return blended