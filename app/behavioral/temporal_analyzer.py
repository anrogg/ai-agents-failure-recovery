"""
Temporal behavioral analysis for drift detection.

This module analyzes behavioral patterns over time to detect gradual shifts
and changes in agent interaction patterns.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import statistics
import structlog

from ..models import InteractionBehavior, ConversationFlowMetrics, DriftScore, PatternAnalysis

logger = structlog.get_logger(__name__)


class TemporalBehaviorAnalyzer:
    """Analyzes behavioral patterns over time windows."""

    def __init__(self):
        pass

    def analyze_conversation_flow(self, behaviors: List[InteractionBehavior]) -> ConversationFlowMetrics:
        """
        Analyze conversation flow characteristics.

        Args:
            behaviors: List of interaction behaviors for analysis

        Returns:
            ConversationFlowMetrics: Flow analysis results
        """
        if not behaviors:
            return ConversationFlowMetrics(
                session_id="",
                flow_consistency_score=0.0,
                topic_coherence_score=0.0,
                engagement_level=0.0,
                turn_taking_pattern=[],
                response_rhythm_score=0.0
            )

        session_id = behaviors[0].session_id

        # Calculate flow consistency (how consistent response patterns are)
        flow_consistency_score = self._calculate_flow_consistency(behaviors)

        # Calculate topic coherence (how well topics are maintained)
        topic_coherence_score = self._calculate_topic_coherence(behaviors)

        # Calculate engagement level
        engagement_level = self._calculate_engagement_level(behaviors)

        # Analyze turn-taking patterns
        turn_taking_pattern = self._analyze_turn_taking(behaviors)

        # Calculate response rhythm score
        response_rhythm_score = self._calculate_response_rhythm(behaviors)

        return ConversationFlowMetrics(
            session_id=session_id,
            flow_consistency_score=flow_consistency_score,
            topic_coherence_score=topic_coherence_score,
            engagement_level=engagement_level,
            turn_taking_pattern=turn_taking_pattern,
            response_rhythm_score=response_rhythm_score
        )

    def detect_behavioral_drift(
        self,
        behaviors: List[InteractionBehavior],
        time_window_hours: int = 24
    ) -> DriftScore:
        """
        Detect behavioral drift over a time window.

        Args:
            behaviors: List of interaction behaviors
            time_window_hours: Time window for drift analysis

        Returns:
            DriftScore: Drift detection results
        """
        if len(behaviors) < 4:  # Need minimum data for drift detection
            return DriftScore(
                session_id=behaviors[0].session_id if behaviors else "",
                drift_score=0.0,
                drift_type="insufficient_data",
                time_window_hours=time_window_hours,
                confidence=0.0,
                detected_at=datetime.now(),
                contributing_factors=["Insufficient data for drift analysis"]
            )

        session_id = behaviors[0].session_id

        # Filter behaviors within time window
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        recent_behaviors = [b for b in behaviors if b.timestamp >= cutoff_time]

        if len(recent_behaviors) < 2:
            return DriftScore(
                session_id=session_id,
                drift_score=0.0,
                drift_type="insufficient_recent_data",
                time_window_hours=time_window_hours,
                confidence=0.0,
                detected_at=datetime.now(),
                contributing_factors=["Insufficient recent data"]
            )

        # Split into early and late periods for comparison
        mid_point = len(recent_behaviors) // 2
        early_behaviors = recent_behaviors[:mid_point]
        late_behaviors = recent_behaviors[mid_point:]

        # Calculate drift in different dimensions
        latency_drift = self._calculate_latency_drift(early_behaviors, late_behaviors)
        length_drift = self._calculate_length_drift(early_behaviors, late_behaviors)
        clarification_drift = self._calculate_clarification_drift(early_behaviors, late_behaviors)
        confidence_drift = self._calculate_confidence_drift(early_behaviors, late_behaviors)

        # Overall drift score
        drift_components = [latency_drift, length_drift, clarification_drift, confidence_drift]
        overall_drift = statistics.mean(drift_components)

        # Determine drift type and contributing factors
        drift_type, contributing_factors = self._analyze_drift_components(
            latency_drift, length_drift, clarification_drift, confidence_drift
        )

        # Calculate confidence based on data amount and consistency
        confidence = min(len(recent_behaviors) / 10.0, 1.0)  # More data = higher confidence

        return DriftScore(
            session_id=session_id,
            drift_score=overall_drift,
            drift_type=drift_type,
            time_window_hours=time_window_hours,
            confidence=confidence,
            detected_at=datetime.now(),
            contributing_factors=contributing_factors
        )

    def identify_interaction_patterns(self, behaviors: List[InteractionBehavior]) -> List[PatternAnalysis]:
        """
        Identify recurring interaction patterns.

        Args:
            behaviors: List of interaction behaviors

        Returns:
            List[PatternAnalysis]: Identified patterns
        """
        patterns = []

        if len(behaviors) < 3:
            return patterns

        session_id = behaviors[0].session_id

        # Identify repetitive response length patterns
        length_pattern = self._identify_length_patterns(behaviors)
        if length_pattern:
            patterns.append(length_pattern)

        # Identify clarification request patterns
        clarification_pattern = self._identify_clarification_patterns(behaviors)
        if clarification_pattern:
            patterns.append(clarification_pattern)

        # Identify confidence expression patterns
        confidence_pattern = self._identify_confidence_patterns(behaviors)
        if confidence_pattern:
            patterns.append(confidence_pattern)

        return patterns

    def calculate_consistency_score(self, behaviors: List[InteractionBehavior]) -> float:
        """
        Calculate overall behavioral consistency score.

        Args:
            behaviors: List of interaction behaviors

        Returns:
            float: Consistency score (0.0 to 1.0)
        """
        if len(behaviors) < 2:
            return 1.0

        # Calculate variance in different dimensions
        latencies = [b.response_latency_ms for b in behaviors]
        lengths = [b.message_length for b in behaviors]
        clarifications = [b.clarification_frequency for b in behaviors]
        confidences = [b.confidence_expressions for b in behaviors]

        # Calculate coefficient of variation for each dimension
        latency_cv = self._coefficient_of_variation(latencies)
        length_cv = self._coefficient_of_variation(lengths)
        clarification_cv = self._coefficient_of_variation(clarifications)
        confidence_cv = self._coefficient_of_variation(confidences)

        # Convert CV to consistency score (lower CV = higher consistency)
        consistency_scores = []
        for cv in [latency_cv, length_cv, clarification_cv, confidence_cv]:
            consistency_scores.append(max(0.0, 1.0 - cv))

        return statistics.mean(consistency_scores)

    def _calculate_flow_consistency(self, behaviors: List[InteractionBehavior]) -> float:
        """Calculate how consistent the conversation flow is."""
        if len(behaviors) < 2:
            return 1.0

        # Analyze response time consistency
        latencies = [b.response_latency_ms for b in behaviors]
        latency_consistency = 1.0 - self._coefficient_of_variation(latencies)

        # Analyze message length consistency
        lengths = [b.message_length for b in behaviors]
        length_consistency = 1.0 - self._coefficient_of_variation(lengths)

        return statistics.mean([latency_consistency, length_consistency])

    def _calculate_topic_coherence(self, behaviors: List[InteractionBehavior]) -> float:
        """Calculate topic coherence based on topic switches."""
        if not behaviors:
            return 1.0

        total_switches = sum(b.topic_switches for b in behaviors)
        total_interactions = len(behaviors)

        # Lower switch rate = higher coherence
        switch_rate = total_switches / total_interactions
        coherence_score = max(0.0, 1.0 - switch_rate)

        return coherence_score

    def _calculate_engagement_level(self, behaviors: List[InteractionBehavior]) -> float:
        """Calculate engagement level based on various metrics."""
        if not behaviors:
            return 0.0

        # Longer messages generally indicate higher engagement
        avg_length = statistics.mean([b.message_length for b in behaviors])
        length_score = min(avg_length / 200.0, 1.0)  # Normalize to 200 chars = full score

        # Lower clarification frequency = better engagement
        avg_clarification = statistics.mean([b.clarification_frequency for b in behaviors])
        clarification_score = max(0.0, 1.0 - avg_clarification)

        return statistics.mean([length_score, clarification_score])

    def _analyze_turn_taking(self, behaviors: List[InteractionBehavior]) -> List[int]:
        """Analyze turn-taking patterns."""
        return [b.conversation_turns for b in behaviors]

    def _calculate_response_rhythm(self, behaviors: List[InteractionBehavior]) -> float:
        """Calculate response rhythm consistency."""
        if len(behaviors) < 2:
            return 1.0

        latencies = [b.response_latency_ms for b in behaviors]
        return 1.0 - self._coefficient_of_variation(latencies)

    def _calculate_latency_drift(self, early: List[InteractionBehavior], late: List[InteractionBehavior]) -> float:
        """Calculate drift in response latency."""
        early_avg = statistics.mean([b.response_latency_ms for b in early])
        late_avg = statistics.mean([b.response_latency_ms for b in late])

        if early_avg == 0:
            return 0.0

        return abs(late_avg - early_avg) / early_avg

    def _calculate_length_drift(self, early: List[InteractionBehavior], late: List[InteractionBehavior]) -> float:
        """Calculate drift in message length."""
        early_avg = statistics.mean([b.message_length for b in early])
        late_avg = statistics.mean([b.message_length for b in late])

        if early_avg == 0:
            return 0.0

        return abs(late_avg - early_avg) / early_avg

    def _calculate_clarification_drift(self, early: List[InteractionBehavior], late: List[InteractionBehavior]) -> float:
        """Calculate drift in clarification frequency."""
        early_avg = statistics.mean([b.clarification_frequency for b in early])
        late_avg = statistics.mean([b.clarification_frequency for b in late])

        return abs(late_avg - early_avg)

    def _calculate_confidence_drift(self, early: List[InteractionBehavior], late: List[InteractionBehavior]) -> float:
        """Calculate drift in confidence expressions."""
        early_avg = statistics.mean([b.confidence_expressions for b in early])
        late_avg = statistics.mean([b.confidence_expressions for b in late])

        if early_avg == 0:
            return abs(late_avg - early_avg)

        return abs(late_avg - early_avg) / (early_avg + 1)

    def _analyze_drift_components(self, latency_drift: float, length_drift: float,
                                clarification_drift: float, confidence_drift: float) -> tuple:
        """Analyze drift components to determine type and factors."""
        drifts = {
            "latency": latency_drift,
            "length": length_drift,
            "clarification": clarification_drift,
            "confidence": confidence_drift
        }

        # Find primary drift type
        max_drift_type = max(drifts, key=drifts.get)
        max_drift_value = drifts[max_drift_type]

        contributing_factors = []
        for drift_type, value in drifts.items():
            if value > 0.2:  # Significant drift threshold
                contributing_factors.append(f"Significant {drift_type} drift: {value:.2f}")

        return max_drift_type, contributing_factors

    def _identify_length_patterns(self, behaviors: List[InteractionBehavior]) -> Optional[PatternAnalysis]:
        """Identify patterns in message length."""
        lengths = [b.message_length for b in behaviors]

        # Simple pattern: check for repetitive length ranges
        length_ranges = []
        for length in lengths:
            if length < 50:
                length_ranges.append("short")
            elif length < 200:
                length_ranges.append("medium")
            else:
                length_ranges.append("long")

        # Count consecutive occurrences
        pattern_strength = self._calculate_pattern_strength(length_ranges)

        if pattern_strength > 0.6:
            return PatternAnalysis(
                session_id=behaviors[0].session_id,
                pattern_type="message_length",
                pattern_strength=pattern_strength,
                repetition_count=len(behaviors),
                last_occurrence=behaviors[-1].timestamp,
                pattern_metadata={"length_distribution": length_ranges}
            )

        return None

    def _identify_clarification_patterns(self, behaviors: List[InteractionBehavior]) -> Optional[PatternAnalysis]:
        """Identify patterns in clarification requests."""
        clarifications = [b.clarification_frequency for b in behaviors]

        # Check for increasing clarification trend
        if len(clarifications) >= 3:
            trend_strength = self._calculate_trend_strength(clarifications)
            if abs(trend_strength) > 0.6:
                return PatternAnalysis(
                    session_id=behaviors[0].session_id,
                    pattern_type="clarification_trend",
                    pattern_strength=abs(trend_strength),
                    repetition_count=len(behaviors),
                    last_occurrence=behaviors[-1].timestamp,
                    pattern_metadata={"trend_direction": "increasing" if trend_strength > 0 else "decreasing"}
                )

        return None

    def _identify_confidence_patterns(self, behaviors: List[InteractionBehavior]) -> Optional[PatternAnalysis]:
        """Identify patterns in confidence expressions."""
        confidences = [b.confidence_expressions for b in behaviors]

        pattern_strength = self._calculate_pattern_strength([str(c) for c in confidences])

        if pattern_strength > 0.5:
            return PatternAnalysis(
                session_id=behaviors[0].session_id,
                pattern_type="confidence_expression",
                pattern_strength=pattern_strength,
                repetition_count=len(behaviors),
                last_occurrence=behaviors[-1].timestamp,
                pattern_metadata={"confidence_levels": confidences}
            )

        return None

    def _coefficient_of_variation(self, values: List[float]) -> float:
        """Calculate coefficient of variation."""
        if not values or len(values) < 2:
            return 0.0

        mean_val = statistics.mean(values)
        if mean_val == 0:
            return 0.0

        std_val = statistics.stdev(values)
        return std_val / mean_val

    def _calculate_pattern_strength(self, sequence: List[str]) -> float:
        """Calculate pattern strength in a sequence."""
        if len(sequence) < 2:
            return 0.0

        # Simple pattern detection: count repeated subsequences
        pattern_count = 0
        total_comparisons = 0

        for i in range(len(sequence) - 1):
            for j in range(i + 1, len(sequence)):
                if sequence[i] == sequence[j]:
                    pattern_count += 1
                total_comparisons += 1

        if total_comparisons == 0:
            return 0.0

        return pattern_count / total_comparisons

    def _calculate_trend_strength(self, values: List[float]) -> float:
        """Calculate trend strength (positive for increasing, negative for decreasing)."""
        if len(values) < 2:
            return 0.0

        # Simple linear trend calculation
        increases = 0
        decreases = 0
        total_changes = 0

        for i in range(1, len(values)):
            if values[i] > values[i-1]:
                increases += 1
            elif values[i] < values[i-1]:
                decreases += 1
            total_changes += 1

        if total_changes == 0:
            return 0.0

        trend_ratio = (increases - decreases) / total_changes
        return trend_ratio

    def detect_response_loops(self, recent_responses: List[str]) -> Optional[Dict[str, Any]]:
        """
        Quick loop detection using exact text matching.

        Args:
            recent_responses: List of recent response texts (newest first)

        Returns:
            Dict: Loop detection results if loop found, None otherwise
        """
        if len(recent_responses) < 3:
            return None

        # Check for exact repetition in last 3 responses
        last_three = recent_responses[-3:]
        if len(set(last_three)) == 1:
            return {
                "loop_type": "exact_repetition",
                "pattern_length": 3,
                "repeated_text": last_three[0][:100],  # First 100 chars for logging
                "confidence": 1.0
            }

        # Check for high similarity in recent responses first (low diversity takes precedence)
        if len(recent_responses) >= 5:
            last_five = recent_responses[-5:]
            unique_responses = set(last_five)
            uniqueness_ratio = len(unique_responses) / len(last_five)

            if uniqueness_ratio < 0.6:  # Less than 60% unique responses
                return {
                    "loop_type": "low_diversity",
                    "pattern_length": 5,
                    "uniqueness_ratio": uniqueness_ratio,
                    "confidence": 1.0 - uniqueness_ratio
                }

        # Check for alternating pattern (A-B-A or similar) only if not low diversity
        if len(recent_responses) >= 4:
            last_four = recent_responses[-4:]
            if last_four[0] == last_four[2] and last_four[1] == last_four[3]:
                return {
                    "loop_type": "alternating_pattern",
                    "pattern_length": 2,
                    "pattern_texts": [last_four[0][:50], last_four[1][:50]],
                    "confidence": 0.9
                }

        return None