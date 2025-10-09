"""
Format validation strategies for AI agent responses.

These strategies validate basic format requirements and structural compliance
of agent outputs before more expensive semantic validation.
"""

from typing import Any, Dict
import re
import json
import structlog

from ..core import ValidationStrategy, ValidationResult, ValidationLevel

logger = structlog.get_logger(__name__)


class FormatValidationStrategy(ValidationStrategy):
    """Strategy for basic format and structure validation."""

    def __init__(self, max_length: int = 5000):
        self.max_length = max_length

    def validate(self, output: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate basic format requirements."""
        errors = []
        warnings = []

        # Check for empty output
        if not output:
            errors.append("Empty output")
            return ValidationResult(
                passed=False,
                confidence=0.0,
                errors=errors,
                warnings=warnings,
                validation_level=ValidationLevel.FORMAT,
                metadata={"output_type": type(output).__name__}
            )

        # String-specific validation
        if isinstance(output, str):
            # Only check for excessively long responses
            if len(output) > self.max_length:
                warnings.append(f"Very long response ({len(output)} chars)")

            # Check for basic structural issues
            if output.strip() != output:
                warnings.append("Leading/trailing whitespace")

            # Check for obvious format issues
            if output.count('"') % 2 != 0:
                warnings.append("Unmatched quotes detected")

            # Check for repeated characters (potential hallucination)
            if re.search(r'(.)\1{15,}', output):  # Increased threshold
                errors.append("Excessive character repetition detected")

        # JSON/Dict output validation
        elif isinstance(output, dict):
            if not output:
                errors.append("Empty dictionary output")

        return ValidationResult(
            passed=len(errors) == 0,
            confidence=0.9 if len(errors) == 0 else 0.3,
            errors=errors,
            warnings=warnings,
            validation_level=ValidationLevel.FORMAT,
            metadata={
                "output_type": type(output).__name__,
                "length": len(str(output)),
                "warnings_count": len(warnings)
            }
        )


class CustomerServiceValidationStrategy(ValidationStrategy):
    """Strategy for customer service specific validation rules."""

    def __init__(self):
        # Common customer service patterns that indicate problems
        self.inappropriate_patterns = [
            r'\b(fuck|shit|damn|hell)\b',  # Profanity
            r'\b(stupid|idiot|moron)\b',   # Insults
            r'\b(go away|shut up|leave me alone)\b'  # Dismissive
        ]

    def validate(self, output: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate customer service appropriateness."""
        errors = []
        warnings = []

        if not isinstance(output, str):
            return ValidationResult(
                passed=True,
                confidence=0.8,
                errors=[],
                warnings=[],
                validation_level=ValidationLevel.CONTENT,
                metadata={"type": "non_text"}
            )

        output_lower = output.lower()

        # Check for inappropriate content
        for pattern in self.inappropriate_patterns:
            if re.search(pattern, output_lower, re.IGNORECASE):
                errors.append(f"Inappropriate language detected")

        # Check for unhelpful responses that don't offer alternatives
        if ("i don't know" in output_lower or "i can't help" in output_lower) and \
           not any(phrase in output_lower for phrase in ["let me", "i can", "try", "help you", "contact"]):
            warnings.append("Response admits limitation without offering assistance")

        confidence = 0.9 if len(errors) == 0 else 0.4
        if warnings:
            confidence *= 0.8

        return ValidationResult(
            passed=len(errors) == 0,
            confidence=confidence,
            errors=errors,
            warnings=warnings,
            validation_level=ValidationLevel.CONTENT,
            metadata={
                "response_length": len(output),
                "appropriateness_check": "completed"
            }
        )


class ResponseCoherenceStrategy(ValidationStrategy):
    """Strategy for validating response coherence and relevance."""

    def validate(self, output: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate response coherence."""
        errors = []
        warnings = []

        if not isinstance(output, str):
            return ValidationResult(
                passed=True,
                confidence=0.8,
                errors=[],
                warnings=[],
                validation_level=ValidationLevel.CONTENT,
                metadata={"type": "non_text"}
            )

        # Check for coherence issues
        sentences = [s.strip() for s in output.split('.') if s.strip()]

        if len(sentences) == 0:
            errors.append("No complete sentences found")
            return ValidationResult(
                passed=False,
                confidence=0.1,
                errors=errors,
                warnings=warnings,
                validation_level=ValidationLevel.CONTENT,
                metadata={"sentence_count": 0}
            )

        # Check for repeated sentences (copy-paste errors)
        if len(sentences) > 1 and len(sentences) != len(set(sentences)):
            errors.append("Duplicate sentences detected")

        # Check for gibberish patterns (random characters, no spaces)
        if len(output) > 20 and ' ' not in output:
            errors.append("Response appears to be gibberish (no spaces)")

        # Check for excessive punctuation repetition
        if re.search(r'[!?]{3,}', output):
            warnings.append("Excessive punctuation detected")

        confidence = 0.8 if len(errors) == 0 else 0.3
        if warnings:
            confidence *= 0.9

        return ValidationResult(
            passed=len(errors) == 0,
            confidence=confidence,
            errors=errors,
            warnings=warnings,
            validation_level=ValidationLevel.CONTENT,
            metadata={
                "sentence_count": len(sentences),
                "coherence_score": confidence
            }
        )