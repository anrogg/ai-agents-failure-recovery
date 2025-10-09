"""
Setup and configuration utilities for the validation system.

This module provides convenient functions to create pre-configured validators
for different use cases in the AI agent system.
"""

from typing import Dict, List
import structlog

from .core import OutputValidator, ValidationLevel
from .strategies.format_strategy import (
    FormatValidationStrategy,
    CustomerServiceValidationStrategy,
    ResponseCoherenceStrategy
)
from .strategies.quality_strategy import (
    QualityValidationStrategy,
    ConfidenceValidationStrategy,
    QualityScorer
)

logger = structlog.get_logger(__name__)


def create_standard_validator() -> OutputValidator:
    """Create a validator with standard strategies for customer service agents."""
    validator = OutputValidator()
    quality_scorer = QualityScorer()

    # Register strategies at appropriate levels
    validator.register_strategy(ValidationLevel.FORMAT, FormatValidationStrategy())
    validator.register_strategy(ValidationLevel.CONTENT, CustomerServiceValidationStrategy())
    validator.register_strategy(ValidationLevel.CONTENT, ResponseCoherenceStrategy())
    validator.register_strategy(ValidationLevel.CONTENT, QualityValidationStrategy(quality_scorer))
    validator.register_strategy(ValidationLevel.CONTENT, ConfidenceValidationStrategy())

    logger.info("Created standard validator with all strategies")
    return validator


def create_basic_validator() -> OutputValidator:
    """Create a validator with only basic format and coherence checks."""
    validator = OutputValidator()

    # Register only essential strategies
    validator.register_strategy(ValidationLevel.FORMAT, FormatValidationStrategy())
    validator.register_strategy(ValidationLevel.CONTENT, ResponseCoherenceStrategy())

    logger.info("Created basic validator with essential strategies")
    return validator


def create_quality_focused_validator() -> OutputValidator:
    """Create a validator focused on quality metrics."""
    validator = OutputValidator()
    quality_scorer = QualityScorer()

    # Register quality-focused strategies
    validator.register_strategy(ValidationLevel.FORMAT, FormatValidationStrategy())
    validator.register_strategy(ValidationLevel.CONTENT, QualityValidationStrategy(quality_scorer))
    validator.register_strategy(ValidationLevel.CONTENT, ConfidenceValidationStrategy())

    logger.info("Created quality-focused validator")
    return validator


def create_custom_validator(strategies: Dict[ValidationLevel, List]) -> OutputValidator:
    """Create a validator with custom strategy configuration."""
    validator = OutputValidator()

    for level, strategy_list in strategies.items():
        for strategy in strategy_list:
            validator.register_strategy(level, strategy)

    logger.info("Created custom validator",
               levels=list(strategies.keys()),
               total_strategies=sum(len(strategies) for strategies in strategies.values()))
    return validator