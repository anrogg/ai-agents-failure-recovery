"""
Core anomaly detection logic for behavioral analysis.

This module provides the main anomaly detection algorithms and scoring
for behavioral pattern analysis.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import structlog

from ..models import InteractionBehavior, BehavioralBaseline
from .baseline_manager import BaselineManager
from .temporal_analyzer import TemporalBehaviorAnalyzer

logger = structlog.get_logger(__name__)


class AnomalyDetector:
    """Core behavioral anomaly detection engine."""

    def __init__(self,
                 baseline_manager: BaselineManager,
                 temporal_analyzer: TemporalBehaviorAnalyzer,
                 anomaly_threshold: float = 0.7,
                 drift_threshold: float = 0.8):
        """
        Initialize anomaly detector.

        Args:
            baseline_manager: Baseline management instance
            temporal_analyzer: Temporal analysis instance
            anomaly_threshold: Threshold for anomaly detection
            drift_threshold: Threshold for drift detection
        """
        self.baseline_manager = baseline_manager
        self.temporal_analyzer = temporal_analyzer
        self.anomaly_threshold = anomaly_threshold
        self.drift_threshold = drift_threshold

    def detect_anomalies(self,
                        session_id: str,
                        current_behavior: InteractionBehavior,
                        session_behaviors: List[InteractionBehavior],
                        recent_responses: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Comprehensive anomaly detection for a session.

        Args:
            session_id: Session identifier
            current_behavior: Current interaction behavior
            session_behaviors: Historical behaviors for the session

        Returns:
            Dict: Comprehensive anomaly analysis results
        """
        anomaly_results = {
            "session_id": session_id,
            "timestamp": datetime.now(),
            "anomalies_detected": [],
            "anomaly_scores": {},
            "overall_anomaly_score": 0.0,
            "confidence": 0.0,
            "recommendations": []
        }

        # 1. Baseline deviation detection
        baseline_anomaly = self._detect_baseline_anomaly(current_behavior, session_behaviors)
        if baseline_anomaly:
            anomaly_results["anomalies_detected"].append(baseline_anomaly)
            anomaly_results["anomaly_scores"]["baseline_deviation"] = baseline_anomaly["score"]

        # 2. Temporal drift detection
        drift_anomaly = self._detect_drift_anomaly(session_behaviors)
        if drift_anomaly:
            anomaly_results["anomalies_detected"].append(drift_anomaly)
            anomaly_results["anomaly_scores"]["temporal_drift"] = drift_anomaly["score"]

        # 3. Pattern-based anomaly detection
        pattern_anomaly = self._detect_pattern_anomaly(session_behaviors)
        if pattern_anomaly:
            anomaly_results["anomalies_detected"].append(pattern_anomaly)
            anomaly_results["anomaly_scores"]["pattern_anomaly"] = pattern_anomaly["score"]

        # 4. Statistical anomaly detection
        statistical_anomaly = self._detect_statistical_anomaly(current_behavior, session_behaviors)
        if statistical_anomaly:
            anomaly_results["anomalies_detected"].append(statistical_anomaly)
            anomaly_results["anomaly_scores"]["statistical_anomaly"] = statistical_anomaly["score"]

        # 5. Loop detection
        if recent_responses:
            loop_anomaly = self._detect_loop_anomaly(recent_responses)
            if loop_anomaly:
                anomaly_results["anomalies_detected"].append(loop_anomaly)
                anomaly_results["anomaly_scores"]["response_loop"] = loop_anomaly["score"]

        # Calculate overall anomaly score
        if anomaly_results["anomaly_scores"]:
            anomaly_results["overall_anomaly_score"] = max(anomaly_results["anomaly_scores"].values())

        # Calculate confidence based on data availability
        anomaly_results["confidence"] = self._calculate_confidence(session_behaviors)

        # Generate recommendations
        anomaly_results["recommendations"] = self._generate_recommendations(anomaly_results)

        logger.info("Anomaly detection completed",
                   session_id=session_id,
                   anomalies_count=len(anomaly_results["anomalies_detected"]),
                   overall_score=anomaly_results["overall_anomaly_score"],
                   confidence=anomaly_results["confidence"])

        return anomaly_results

    def _detect_baseline_anomaly(self,
                                current_behavior: InteractionBehavior,
                                session_behaviors: List[InteractionBehavior]) -> Optional[Dict[str, Any]]:
        """Detect anomalies based on established baseline."""
        baseline = self.baseline_manager.get_baseline(current_behavior.session_id)

        if not baseline:
            # Try to establish baseline if we have enough data
            if len(session_behaviors) >= self.baseline_manager.min_interactions:
                baseline = self.baseline_manager.establish_baseline(
                    current_behavior.session_id, session_behaviors
                )

            if not baseline:
                return None

        deviation_score = self.baseline_manager.detect_deviation(current_behavior, baseline)

        if deviation_score >= self.anomaly_threshold:
            return {
                "type": "baseline_deviation",
                "score": deviation_score,
                "description": f"Behavior deviates significantly from established baseline",
                "details": {
                    "current_latency": current_behavior.response_latency_ms,
                    "baseline_latency": baseline.avg_response_latency,
                    "current_length": current_behavior.message_length,
                    "baseline_length_range": baseline.typical_message_length_range,
                    "current_clarification": current_behavior.clarification_frequency,
                    "baseline_clarification": baseline.normal_clarification_rate
                }
            }

        return None

    def _detect_drift_anomaly(self, session_behaviors: List[InteractionBehavior]) -> Optional[Dict[str, Any]]:
        """Detect temporal drift anomalies."""
        if len(session_behaviors) < 4:
            return None

        drift_score = self.temporal_analyzer.detect_behavioral_drift(session_behaviors)

        if drift_score.drift_score >= self.drift_threshold:
            return {
                "type": "temporal_drift",
                "score": drift_score.drift_score,
                "description": f"Significant behavioral drift detected: {drift_score.drift_type}",
                "details": {
                    "drift_type": drift_score.drift_type,
                    "time_window_hours": drift_score.time_window_hours,
                    "confidence": drift_score.confidence,
                    "contributing_factors": drift_score.contributing_factors
                }
            }

        return None

    def _detect_pattern_anomaly(self, session_behaviors: List[InteractionBehavior]) -> Optional[Dict[str, Any]]:
        """Detect pattern-based anomalies."""
        patterns = self.temporal_analyzer.identify_interaction_patterns(session_behaviors)

        # Look for problematic patterns
        for pattern in patterns:
            if pattern.pattern_strength > 0.8 and pattern.pattern_type in ["clarification_trend"]:
                return {
                    "type": "pattern_anomaly",
                    "score": pattern.pattern_strength,
                    "description": f"Problematic interaction pattern detected: {pattern.pattern_type}",
                    "details": {
                        "pattern_type": pattern.pattern_type,
                        "pattern_strength": pattern.pattern_strength,
                        "repetition_count": pattern.repetition_count,
                        "metadata": pattern.pattern_metadata
                    }
                }

        return None

    def _detect_statistical_anomaly(self,
                                   current_behavior: InteractionBehavior,
                                   session_behaviors: List[InteractionBehavior]) -> Optional[Dict[str, Any]]:
        """Detect statistical anomalies using outlier detection."""
        if len(session_behaviors) < 3:
            return None

        # Analyze each metric for outliers
        anomalies = []

        # Response latency outlier detection
        latencies = [b.response_latency_ms for b in session_behaviors]
        if self._is_outlier(current_behavior.response_latency_ms, latencies):
            anomalies.append("response_latency")

        # Message length outlier detection
        lengths = [b.message_length for b in session_behaviors]
        if self._is_outlier(current_behavior.message_length, lengths):
            anomalies.append("message_length")

        # Clarification frequency outlier detection
        clarifications = [b.clarification_frequency for b in session_behaviors]
        if self._is_outlier(current_behavior.clarification_frequency, clarifications):
            anomalies.append("clarification_frequency")

        if anomalies:
            # Calculate composite anomaly score
            anomaly_score = len(anomalies) / 4.0  # Normalize by number of metrics

            return {
                "type": "statistical_anomaly",
                "score": anomaly_score,
                "description": f"Statistical outliers detected in: {', '.join(anomalies)}",
                "details": {
                    "outlier_metrics": anomalies,
                    "current_values": {
                        "latency": current_behavior.response_latency_ms,
                        "length": current_behavior.message_length,
                        "clarification": current_behavior.clarification_frequency,
                        "confidence": current_behavior.confidence_expressions
                    }
                }
            }

        return None

    def _detect_loop_anomaly(self, recent_responses: List[str]) -> Optional[Dict[str, Any]]:
        """Detect response loop anomalies."""
        loop_result = self.temporal_analyzer.detect_response_loops(recent_responses)

        if loop_result:
            return {
                "type": "response_loop",
                "score": loop_result["confidence"],
                "description": f"Response loop detected: {loop_result['loop_type']}",
                "details": loop_result
            }

        return None

    def _is_outlier(self, value: float, historical_values: List[float], threshold: float = 2.0) -> bool:
        """
        Detect if a value is a statistical outlier using modified Z-score.

        Args:
            value: Current value to check
            historical_values: Historical values for comparison
            threshold: Z-score threshold for outlier detection

        Returns:
            bool: True if value is an outlier
        """
        if len(historical_values) < 3:
            return False

        # Calculate median and median absolute deviation
        sorted_values = sorted(historical_values)
        median = sorted_values[len(sorted_values) // 2]

        deviations = [abs(v - median) for v in historical_values]
        mad = sorted(deviations)[len(deviations) // 2]

        if mad == 0:
            return False

        # Modified Z-score
        modified_z_score = 0.6745 * (value - median) / mad

        return abs(modified_z_score) > threshold

    def _calculate_confidence(self, session_behaviors: List[InteractionBehavior]) -> float:
        """Calculate confidence in anomaly detection based on data availability."""
        # More data = higher confidence
        data_confidence = min(len(session_behaviors) / 20.0, 1.0)

        # Recent data = higher confidence
        if session_behaviors:
            latest_behavior = session_behaviors[-1]
            time_since_latest = datetime.now() - latest_behavior.timestamp
            recency_confidence = max(0.0, 1.0 - (time_since_latest.total_seconds() / (24 * 3600)))
        else:
            recency_confidence = 0.0

        return (data_confidence + recency_confidence) / 2.0

    def _generate_recommendations(self, anomaly_results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on anomaly results."""
        recommendations = []

        if anomaly_results["overall_anomaly_score"] >= 0.8:
            recommendations.append("High anomaly score detected - immediate investigation recommended")

        for anomaly in anomaly_results["anomalies_detected"]:
            if anomaly["type"] == "baseline_deviation":
                recommendations.append("Monitor agent performance for consistency issues")
            elif anomaly["type"] == "temporal_drift":
                recommendations.append("Check for gradual degradation in agent behavior over time")
            elif anomaly["type"] == "pattern_anomaly":
                recommendations.append("Investigate repetitive problematic interaction patterns")
            elif anomaly["type"] == "statistical_anomaly":
                recommendations.append("Review outlier behaviors for potential system issues")
            elif anomaly["type"] == "response_loop":
                recommendations.append("Agent appears stuck in response loop - restart or reset session")

        if anomaly_results["confidence"] < 0.5:
            recommendations.append("Low confidence in results - collect more behavioral data")

        if not recommendations:
            recommendations.append("No significant anomalies detected - continue monitoring")

        return recommendations

    def update_thresholds(self, anomaly_threshold: float, drift_threshold: float) -> None:
        """Update anomaly detection thresholds."""
        self.anomaly_threshold = anomaly_threshold
        self.drift_threshold = drift_threshold

        logger.info("Updated anomaly detection thresholds",
                   anomaly_threshold=anomaly_threshold,
                   drift_threshold=drift_threshold)