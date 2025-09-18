# AI Agent Failure Recovery Laboratory

> **Blog Series Companion**: This repository accompanies the "When Perfect Agents Meet Imperfect Reality" blog series. See [Blog Series Guide](docs/blog-series-guide.md) for navigation by specific blog post and code versions.

A comprehensive laboratory for testing, demonstrating, and analyzing AI agent failure modes and recovery patterns in production environments.

## What This Project Currently Does

This system deliberately injects 11 different types of failures into AI agents to:
- **Study real failure patterns** that occur in production AI systems
- **Demonstrate business impact** of technical failures ($10K+ losses from small bugs)
- **Research recovery strategies** and resilience patterns
- **Provide controlled testing** environments for AI reliability

## Key Features

- **11 Failure Modes**: Hallucinations, infinite loops, API timeouts, resource exhaustion, and more
- **Dual-Mode Injection**: Force specific failures OR enable probabilistic random failures
- **Real Business Impact Demo**: Insurance customer support showing cascading failure costs
- **Complete Transparency**: Track what AI naturally produces vs. what users observe
- **Research Configuration**: Environment variables for failure rate studies

## Quick Start

```bash
# Clone and start the system
git clone https://github.com/anrogg/ai-agents-failure-recovery
cd ai-agents-failure-recovery
docker-compose up --build

# Run the insurance customer support demo
python demos/insurance/run_demo.py

# View API documentation
open http://localhost:8000/docs
```

## Documentation

- **[Complete Documentation](docs/README-1.md)** - Full technical documentation, API reference, and configuration guide
- **[Blog Series Guide](docs/blog-series-guide.md)** - Navigation for blog readers by post and code version
- **[Decision Logic Diagrams](diagrams/)** - Visual flowcharts of failure injection logic

## Core Failure Categories

| Category | Examples | Impact |
|----------|----------|---------|
| **Output Quality** | Hallucinations, incorrect reasoning | Wrong information to users |
| **Behavioral** | Infinite loops, refusing progress | Stuck conversations |
| **Integration** | API timeouts, service failures | System unavailability |
| **Resource** | Token limits, memory exhaustion | Performance degradation |

## Research Mode

Enable probabilistic failures for research:

```bash
# Set environment variables
PROBABILISTIC_FAILURES=true
FAILURE_RATE_MULTIPLIER=1.5

# Failures now trigger randomly based on configured probabilities
# with intelligent session management and cooldown periods
```

## Real-World Impact Demo

The insurance demo shows how small technical failures cascade:
- Customer starts polite, becomes furious
- Simple timeouts lead to $2,125 customer costs
- System restarts cause $8,300 company losses
- **Total impact: $10,425** from minor technical issues

## Important Notice

This system is designed for **research and testing only**. The deliberate failure injection makes it unsuitable for production without significant safety modifications.

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-failure-mode`
3. Add your failure modes or recovery patterns
4. Submit pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Built for researchers, engineers, and organizations studying AI reliability and failure recovery patterns.**