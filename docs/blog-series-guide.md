# Blog Series: When Perfect Agents Meet Imperfect Reality

## Repository Navigation for Blog Readers

This companion repository evolves with each blog post.

### Quick Navigation

| Blog Post                                                               | Repository Version                                                                             | Key Files                                                                                                                                                                                                                                                                                                                                                                                                                                     | Demo |
|-------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------|
| **Part 1: "When Perfect Agents Meet Imperfect Reality"**                | [`v1.2-foundation`](https://github.com/anrogg/ai-agents-failure-recovery/tree/v1.2-foundation) | [`failure_injector.py`](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.2-foundation/app/failure_injector.py), [`models.py`](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.2-foundation/app/models.py)                                                                                                                                                                                                            | [`insurance demo`](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.2-foundation/demos/insurance/) |
| **Part 2: "When AI Agents Lie: Building Truth-Seeking Infrastructure"** | [`v1.4-foundation`](https://github.com/anrogg/ai-agents-failure-recovery/tree/v1.4-foundation) | [`metrics.py`](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.4-foundation/app/metrics.py), [`routes.py`](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.4-foundation/app/routes.py), [`docker-compose.yml`](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.4-foundation/docker-compose.yml), [`prometheus.yml`](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.4-foundation/config/prometheus.yml) | NA |
| **Part 3: "When Good AI Goes Bad: Detecting Quality Output Failures"**  | [`v2.0-monitoring`](https://github.com/anrogg/ai-agents-failure-recovery/tree/v2.0-monitoring) | [`format_strategy.py`](https://github.com/anrogg/ai-agents-failure-recovery/blob/v2.0-monitoring/app/validation/strategies/format_strategy.py), [`quality_strategy.py`](https://github.com/anrogg/ai-agents-failure-recovery/blob/v2.0-monitoring/app/validation/strategies/quality_strategy.py) | NA |
### 📖 Blog Post 1: "When Perfect Agents Meet Imperfect Reality: Foundation"

**Repository State**: [`v1.2-foundation`](https://github.com/anrogg/ai-agents-failure-recovery/tree/v1.2-foundation)

**What You'll Explore**:
- 🔍 **[11 Failure Modes](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.2-foundation/app/models.py#L31-L42)** - Complete taxonomy
- 🎭 **[Failure Injection Engine](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.2-foundation/app/failure_injector.py#L23-L150)** - How failures are simulated
- 📊 **[Real-World Impact Demo](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.2-foundation/demos/insurance/README.md)** - $10K+ business impact from small failures
- 🔄 **[Decision Logic Diagrams](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.2-foundation/diagrams/)** - Visual failure flow

**Quick Start for Blog Post 1**:
```bash
git clone https://github.com/anrogg/ai-agents-failure-recovery
cd ai-agents-failure-recovery
git checkout v1.2-foundation
docker-compose up
python demos/insurance/run_demo.py
```

**Key Code Sections Referenced in Blog**:
- [Hallucination Injection](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.2-foundation/app/failure_injector.py#L204-L207) (Lines 204-207)
- [Failure Mode Definitions](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.2-foundation/app/models.py#L31-L42) (Lines 31-42)
- [Insurance Demo Impact Calculation](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.2-foundation/demos/insurance/demo.py#L85-L105) (Lines 85-105)

### 📖 Blog Post 2: "When AI Agents Lie: Building Truth-Seeking Infrastructure"

**Repository State**: [`v1.4-foundation`](https://github.com/anrogg/ai-agents-failure-recovery/tree/v1.4-foundation)

**What You'll Explore**:
- 🎭 [Prometheus as our agent sidekick](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.4-foundation/config/prometheus.yml)
- 📊 [Basic metrics setup](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.4-foundation/app/metrics.py)
- 🔍 [New health endpoints for Prometheus to scrape](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.4-foundation/app/routes.py)

**Quick Start for Blog Post 2**:
```bash
git clone https://github.com/anrogg/ai-agents-failure-recovery
cd ai-agents-failure-recovery
git checkout v1.4-foundation
docker-compose up
```

### 📖 Part 3: "When Good AI Goes Bad: Detecting Quality Output Failures"

**Repository State**: [`v2.0-monitoring`](https://github.com/anrogg/ai-agents-failure-recovery/tree/v2.0-monitoring)

**What You'll Explore**:
- 🔍 **[Output Validation Framework](https://github.com/anrogg/ai-agents-failure-recovery/blob/v2.0-monitoring/app/validation/core.py)** - Strategy pattern-based validation system
- 🎯 **[Quality Detection Strategies](https://github.com/anrogg/ai-agents-failure-recovery/tree/v2.0-monitoring/app/validation/strategies)** - Multiple validation approaches for different failure types
- 📊 **[Validation Metrics Integration](https://github.com/anrogg/ai-agents-failure-recovery/blob/v2.0-monitoring/app/metrics.py#L77-L99)** - Prometheus metrics for validation monitoring
- 🧪 **[End-to-End Validation Test](https://github.com/anrogg/ai-agents-failure-recovery/blob/v2.0-monitoring/tests/test_validation_e2e.py)** - End-to_end system verification

**Quick Start for Blog Post 3**:
```bash
git clone https://github.com/anrogg/ai-agents-failure-recovery
cd ai-agents-failure-recovery
git checkout feature/truth-detectors
export OUTPUT_VALIDATION_ENABLED=true
export OUTPUT_VALIDATION_LEVEL=content
python -m app.main
# Test validation: python tests/test_validation_e2e.py
```

**Key Code Sections Referenced in Blog**:
- [ValidationStrategy Interface](https://github.com/anrogg/ai-agents-failure-recovery/blob/feature/truth-detectors/app/validation/core.py#L194-L200) (Lines 194-200)
- [Quality Scoring Implementation](https://github.com/anrogg/ai-agents-failure-recovery/blob/feature/truth-detectors/app/validation/strategies/quality_strategy.py#L427-L443) (Lines 427-443)
- [Confidence Calibration Logic](https://github.com/anrogg/ai-agents-failure-recovery/blob/feature/truth-detectors/app/validation/strategies/quality_strategy.py#L604-L620) (Lines 604-620)

---

## Always Current: Latest Complete Version

Want the full-featured version with all blog post features combined?

```bash
git clone https://github.com/anrogg/ai-agents-failure-recovery
# No checkout needed - main branch has everything
docker-compose up
```

**Current Features**: Foundation + Probabilistic + Recovery (when available)
**Branch**: [`main`](https://github.com/anrogg/ai-agents-failure-recovery)

---

## Direct Links for Blog Authors

When writing your blog posts, use these permalink patterns:

```markdown
<!-- For specific code sections -->
[See the implementation](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.2-foundation/app/failure_injector.py#L204-L207)

<!-- For entire files -->
[Review the complete failure injector](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.2-foundation/app/failure_injector.py)

<!-- For specific releases -->
[Download this blog post's code](https://github.com/anrogg/ai-agents-failure-recovery/releases/tag/v1.2-foundation)
```

## 📝 Notes for Repository Maintainers

1. **Tag each blog post release**: `git tag -a v1.2-foundation -m "Blog Post 1: Foundation"`
2. **Update this guide**: Add new blog posts to the table above
3. **Keep permalinks stable**: Don't rewrite history on tagged releases
4. **Test links**: Verify all GitHub links work before publishing blog posts