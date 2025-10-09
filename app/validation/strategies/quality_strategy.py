"""
Quality validation strategies for AI agent responses.

These strategies validate the quality and usefulness of agent outputs
using lightweight heuristics that don't require external dependencies.
"""

from typing import Dict, Any, List
from datetime import datetime
import re
import structlog

from ..core import ValidationStrategy, ValidationResult, ValidationLevel

logger = structlog.get_logger(__name__)


class QualityScorer:
    """Handles quality scoring calculations using built-in Python features."""

    def __init__(self):
        self.quality_history = []

    def score_helpfulness(self, text: str) -> float:
        """Score how helpful the response appears to be."""
        if not text or len(text.strip()) < 3:
            return 0.0

        text_lower = text.lower()

        # Positive indicators of helpfulness
        helpful_phrases = [
            "i can help", "let me", "here's how", "you can", "try this",
            "i'll", "would you like", "i suggest", "i recommend",
            "here are", "the steps are", "to do this"
        ]

        # Negative indicators
        unhelpful_phrases = [
            "i don't know", "i can't help", "impossible", "not possible",
            "i'm not sure", "i have no idea", "can't do that"
        ]

        helpful_count = sum(1 for phrase in helpful_phrases if phrase in text_lower)
        unhelpful_count = sum(1 for phrase in unhelpful_phrases if phrase in text_lower)

        # Base score from helpful indicators
        helpful_score = min(1.0, helpful_count * 0.3)

        # Penalty for unhelpful indicators (but not fatal if offering alternatives)
        if unhelpful_count > 0:
            # Check if alternatives are offered
            alternative_phrases = ["however", "but", "alternatively", "instead", "contact", "escalate"]
            has_alternatives = any(phrase in text_lower for phrase in alternative_phrases)

            if has_alternatives:
                helpful_score = max(helpful_score, 0.6)  # Partial credit for offering alternatives
            else:
                helpful_score = max(helpful_score - (unhelpful_count * 0.2), 0.1)

        return helpful_score

    def score_consistency(self, text: str) -> float:
        """Score internal consistency of the text."""
        if not text or len(text.strip()) < 10:
            return 1.0

        # Check for obvious contradictions
        text_lower = text.lower()

        # Look for contradictory statements
        contradiction_patterns = [
            (r'\byes\b.*\bno\b', r'\bno\b.*\byes\b'),
            (r'\bcan\b.*\bcannot\b', r'\bcannot\b.*\bcan\b'),
            (r'\bwill\b.*\bwon\'t\b', r'\bwon\'t\b.*\bwill\b'),
            (r'\bis\b.*\bisn\'t\b', r'\bisn\'t\b.*\bis\b')
        ]

        consistency_score = 1.0

        for pattern1, pattern2 in contradiction_patterns:
            if (re.search(pattern1, text_lower) or re.search(pattern2, text_lower)):
                # Only penalize if they're close together (likely contradiction)
                words = text_lower.split()
                if len(words) < 50:  # Short text with contradictions is more problematic
                    consistency_score *= 0.7
                    break

        return consistency_score

    def score_relevance(self, text: str, context: Dict[str, Any]) -> float:
        """Score relevance to the context/conversation."""
        if not text:
            return 0.0

        # Simple relevance scoring based on context clues
        relevance_score = 0.7  # Default moderate relevance

        # Check if response acknowledges the question/context
        acknowledgment_phrases = [
            "regarding", "about your", "for your", "to answer",
            "you asked", "your question", "your request"
        ]

        text_lower = text.lower()
        if any(phrase in text_lower for phrase in acknowledgment_phrases):
            relevance_score = min(1.0, relevance_score + 0.2)

        # Check for generic responses that might not be relevant
        generic_phrases = [
            "thank you for contacting", "is there anything else",
            "i'm here to help", "how can i assist"
        ]

        if any(phrase in text_lower for phrase in generic_phrases) and len(text) < 100:
            relevance_score *= 0.8  # Slight penalty for generic short responses

        return relevance_score

    def calculate_overall_quality(self, text: str, context: Dict[str, Any]) -> float:
        """Calculate overall quality score combining multiple metrics."""
        helpfulness = self.score_helpfulness(text)
        consistency = self.score_consistency(text)
        relevance = self.score_relevance(text, context)

        # Weighted combination
        quality_score = (
            helpfulness * 0.5 +    # Helpfulness is most important
            consistency * 0.3 +    # Consistency is important for trust
            relevance * 0.2        # Relevance matters but context might be limited
        )

        # Store for trend analysis
        self.quality_history.append({
            'timestamp': datetime.now(),
            'helpfulness': helpfulness,
            'consistency': consistency,
            'relevance': relevance,
            'overall': quality_score
        })

        return quality_score


class QualityValidationStrategy(ValidationStrategy):
    """Strategy for validating output quality using multiple metrics."""

    def __init__(self, quality_scorer: QualityScorer, min_quality: float = 0.3):
        self.quality_scorer = quality_scorer
        self.min_quality = min_quality

    def validate(self, output: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate output quality."""
        errors = []
        warnings = []

        if not isinstance(output, str):
            # Non-text output gets default confidence
            return ValidationResult(
                passed=True,
                confidence=0.8,
                errors=errors,
                warnings=warnings,
                validation_level=ValidationLevel.CONTENT,
                metadata={"type": "non_text"}
            )

        # Calculate quality metrics
        helpfulness = self.quality_scorer.score_helpfulness(output)
        consistency = self.quality_scorer.score_consistency(output)
        relevance = self.quality_scorer.score_relevance(output, context)

        # Weighted quality score
        quality_score = (helpfulness * 0.5 + consistency * 0.3 + relevance * 0.2)

        # Quality thresholds
        if quality_score < self.min_quality:
            errors.append(f"Low quality score: {quality_score:.2f}")
        elif quality_score < 0.6:
            warnings.append(f"Medium quality score: {quality_score:.2f}")

        return ValidationResult(
            passed=len(errors) == 0,
            confidence=quality_score,
            errors=errors,
            warnings=warnings,
            validation_level=ValidationLevel.CONTENT,
            metadata={
                "quality_score": quality_score,
                "helpfulness": helpfulness,
                "consistency": consistency,
                "relevance": relevance
            }
        )


class ConfidenceValidationStrategy(ValidationStrategy):
    """Strategy for validating AI confidence claims and uncertainty handling."""

    def __init__(self):
        self.confidence_history = []

    def validate(self, output: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate AI confidence claims."""
        errors = []
        warnings = []

        if not isinstance(output, str):
            return ValidationResult(
                passed=True, confidence=0.8, errors=[], warnings=[],
                validation_level=ValidationLevel.CONTENT, metadata={}
            )

        # Extract confidence indicators from text
        confidence_indicators = self._extract_confidence_indicators(output)

        # Check for overconfidence patterns
        if confidence_indicators["overconfident_phrases"] > 2:
            warnings.append("Multiple overconfident statements detected")

        # Check for uncertainty without acknowledgment
        if confidence_indicators["uncertain_content"] and not confidence_indicators["uncertainty_acknowledged"]:
            errors.append("Uncertain content presented as fact")

        confidence_score = self._calculate_confidence_score(confidence_indicators)

        return ValidationResult(
            passed=len(errors) == 0,
            confidence=confidence_score,
            errors=errors,
            warnings=warnings,
            validation_level=ValidationLevel.CONTENT,
            metadata=confidence_indicators
        )

    def _extract_confidence_indicators(self, text: str) -> Dict[str, Any]:
        """Extract confidence-related patterns from text."""
        text_lower = text.lower()

        overconfident_phrases = [
            "definitely", "certainly", "absolutely", "100%", "without doubt",
            "guaranteed", "always", "never", "impossible", "certain"
        ]

        uncertainty_phrases = [
            "might", "could", "possibly", "perhaps", "maybe", "uncertain",
            "unclear", "approximately", "roughly", "probably"
        ]

        uncertainty_acknowledgments = [
            "i'm not sure", "i don't know", "uncertain", "unclear",
            "needs verification", "might be wrong", "let me check"
        ]

        return {
            "overconfident_phrases": sum(1 for phrase in overconfident_phrases if phrase in text_lower),
            "uncertainty_phrases": sum(1 for phrase in uncertainty_phrases if phrase in text_lower),
            "uncertainty_acknowledged": any(phrase in text_lower for phrase in uncertainty_acknowledgments),
            "uncertain_content": any(phrase in text_lower for phrase in uncertainty_phrases),
            "text_length": len(text)
        }

    def _calculate_confidence_score(self, indicators: Dict[str, Any]) -> float:
        """Calculate confidence calibration score."""
        base_score = 0.7

        # Penalize overconfidence
        if indicators["overconfident_phrases"] > 0:
            base_score -= 0.1 * indicators["overconfident_phrases"]

        # Reward uncertainty acknowledgment when uncertain
        if indicators["uncertain_content"] and indicators["uncertainty_acknowledged"]:
            base_score += 0.1

        # Penalize unacknowledged uncertainty
        if indicators["uncertain_content"] and not indicators["uncertainty_acknowledged"]:
            base_score -= 0.2

        return max(0.1, min(1.0, base_score))