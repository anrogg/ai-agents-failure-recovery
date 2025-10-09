# Validation System Design Patterns

This diagram illustrates the three core design patterns used in the validation system: Registry, Strategy, and Decorator patterns working together.

```mermaid
graph LR
    %% Main flow
    A[Agent Response] --> B[validate_output<br/>Decorator]
    B --> C[OutputValidator<br/>Registry]
    C --> D[ValidationStrategy<br/>Implementations]
    D --> E[Validated Response]

    %% Registry levels
    C --> F[FORMAT Level]
    C --> G[CONTENT Level]

    %% Strategy examples
    F --> H[FormatValidationStrategy]
    G --> I[QualityValidationStrategy]
    G --> J[ConfidenceValidationStrategy]

    style B fill:#e1f5fe
    style C fill:#f3e5f5
    style D fill:#e8f5e8
```

## Pattern Interactions

1. **Decorator Pattern** (`validate_output`):
   - Wraps any function to automatically apply validation
   - Intercepts function results before returning to caller
   - Decides whether to return result or raise validation error

2. **Registry Pattern** (`OutputValidator`):
   - Maintains organized collections of validation strategies by level
   - Provides centralized strategy management and execution
   - Enables dynamic strategy registration and configuration

3. **Strategy Pattern** (`ValidationStrategy` implementations):
   - Defines interchangeable validation algorithms
   - Allows easy addition of new validation types
   - Encapsulates specific validation logic in separate classes

## How They Work Together

The **Decorator** catches function outputs → The **Registry** orchestrates validation → The **Strategies** perform specific checks → Results flow back through the **Decorator** to the caller.