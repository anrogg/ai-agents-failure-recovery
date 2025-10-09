"""
Core validation framework for AI agent output validation.

This module provides the fundamental components for validating AI agent outputs
using a Strategy pattern approach for extensibility and maintainability.
"""

from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import time
import structlog

logger = structlog.get_logger(__name__)


class ValidationLevel(Enum):
    """Validation levels in order of cost/complexity."""
    FORMAT = "format"
    CONTENT = "content"
    SEMANTIC = "semantic"
    EXPERT = "expert"


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    passed: bool
    confidence: float
    errors: List[str]
    warnings: List[str]
    validation_level: ValidationLevel
    metadata: Dict[str, Any]


class ValidationStrategy(ABC):
    """Abstract base class for all validation strategies."""

    @abstractmethod
    def validate(self, output: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate output and return result."""
        pass


class OutputValidator:
    """Main validator that orchestrates validation strategies."""

    def __init__(self):
        self.strategies = {
            ValidationLevel.FORMAT: [],
            ValidationLevel.CONTENT: [],
            ValidationLevel.SEMANTIC: [],
            ValidationLevel.EXPERT: []
        }
        self.validation_history = []

    def register_strategy(self, level: ValidationLevel, strategy: ValidationStrategy):
        """Register a validation strategy at specified level."""
        self.strategies[level].append(strategy)
        logger.info("Registered validation strategy",
                   level=level.value,
                   strategy=strategy.__class__.__name__)

    def validate(self, output: Any, context: Dict[str, Any],
                max_level: ValidationLevel = ValidationLevel.CONTENT) -> ValidationResult:
        """Run validation strategies up to specified level."""
        start_time = time.time()
        errors = []
        warnings = []
        confidence = 1.0

        # Import metrics here to avoid circular imports
        try:
            from ..metrics import metrics_collector
        except ImportError:
            metrics_collector = None

        # Run strategies in order of cost
        validation_levels = [ValidationLevel.FORMAT, ValidationLevel.CONTENT,
                           ValidationLevel.SEMANTIC, ValidationLevel.EXPERT]

        for level in validation_levels:
            # Convert enum to comparable value for ordering
            if self._level_value(level) > self._level_value(max_level):
                break

            for strategy in self.strategies[level]:
                strategy_start = time.time()
                try:
                    result = strategy.validate(output, context)
                    strategy_duration = time.time() - strategy_start

                    if not result.passed:
                        errors.extend(result.errors)
                        confidence = min(confidence, result.confidence)
                    warnings.extend(result.warnings)

                    # Record metrics for this strategy
                    if metrics_collector:
                        metrics_collector.record_validation_check(
                            validation_level=level.value,
                            strategy=strategy.__class__.__name__,
                            passed=result.passed,
                            confidence=result.confidence,
                            duration=strategy_duration,
                            errors=result.errors
                        )

                    logger.debug("Validation strategy completed",
                               strategy=strategy.__class__.__name__,
                               level=level.value,
                               passed=result.passed,
                               confidence=result.confidence)

                except Exception as e:
                    strategy_duration = time.time() - strategy_start
                    error_msg = f"Strategy error in {strategy.__class__.__name__}: {str(e)}"
                    errors.append(error_msg)
                    confidence *= 0.8

                    # Record failed strategy metrics
                    if metrics_collector:
                        metrics_collector.record_validation_check(
                            validation_level=level.value,
                            strategy=strategy.__class__.__name__,
                            passed=False,
                            confidence=0.0,
                            duration=strategy_duration,
                            errors=[error_msg]
                        )

                    logger.error("Validation strategy failed",
                               strategy=strategy.__class__.__name__,
                               error=str(e))

        total_duration = time.time() - start_time
        final_result = ValidationResult(
            passed=len(errors) == 0,
            confidence=confidence,
            errors=errors,
            warnings=warnings,
            validation_level=max_level,
            metadata={"timestamp": datetime.now().isoformat(), "duration": total_duration}
        )

        self.validation_history.append(final_result)
        return final_result

    def _level_value(self, level: ValidationLevel) -> int:
        """Convert validation level to numeric value for comparison."""
        level_order = {
            ValidationLevel.FORMAT: 1,
            ValidationLevel.CONTENT: 2,
            ValidationLevel.SEMANTIC: 3,
            ValidationLevel.EXPERT: 4
        }
        return level_order[level]

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get statistics about validation performance."""
        if not self.validation_history:
            return {"total_validations": 0}

        total = len(self.validation_history)
        passed = sum(1 for r in self.validation_history if r.passed)
        avg_confidence = sum(r.confidence for r in self.validation_history) / total

        return {
            "total_validations": total,
            "pass_rate": passed / total,
            "average_confidence": avg_confidence,
            "recent_validations": self.validation_history[-10:]
        }


def validate_output(validator: OutputValidator,
                   max_level: ValidationLevel = ValidationLevel.CONTENT,
                   confidence_threshold: float = 0.7):
    """Decorator to add output validation to any function."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the original function
            result = func(*args, **kwargs)

            # Prepare context for validation
            context = {
                "function_name": func.__name__,
                "args": args,
                "kwargs": kwargs,
                "timestamp": datetime.now()
            }

            # Validate the output
            validation_result = validator.validate(result, context, max_level)

            # Log validation results
            logger.info("Output validation completed",
                       function=func.__name__,
                       passed=validation_result.passed,
                       confidence=validation_result.confidence,
                       errors=validation_result.errors,
                       warnings=validation_result.warnings)

            # Decide whether to return result or raise exception
            if validation_result.confidence < confidence_threshold:
                logger.warning("Output validation failed threshold",
                             function=func.__name__,
                             confidence=validation_result.confidence,
                             threshold=confidence_threshold,
                             errors=validation_result.errors)
                raise ValueError(f"Output validation failed: {validation_result.errors}")

            return result
        return wrapper
    return decorator