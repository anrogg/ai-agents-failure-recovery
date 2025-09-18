# Blog Series: When Perfect Agents Meet Imperfect Reality

## Repository Navigation for Blog Readers

This companion repository evolves with each blog post.

### Quick Navigation

| Blog Post | Repository Version | Key Files | Demo |
|-----------|-------------------|-----------|------|
| **Part 1: "When Perfect Agents Meet Imperfect Reality"** | [`v1.0-foundation`](https://github.com/anrogg/ai-agents-failure-recovery/tree/v1.0-foundation) | [`failure_injector.py`](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.0-foundation/app/failure_injector.py), [`models.py`](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.0-foundation/app/models.py) | [`insurance demo`](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.0-foundation/demos/insurance/) |

### 📖 Blog Post 1: "When Perfect Agents Meet Imperfect Reality: Foundation"

**Repository State**: [`v1.0-foundation`](https://github.com/anrogg/ai-agents-failure-recovery/tree/v1.0-foundation)

**What You'll Explore**:
- 🔍 **[11 Failure Modes](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.0-foundation/app/models.py#L31-L42)** - Complete taxonomy
- 🎭 **[Failure Injection Engine](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.0-foundation/app/failure_injector.py#L23-L150)** - How failures are simulated
- 📊 **[Real-World Impact Demo](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.0-foundation/demos/insurance/README.md)** - $10K+ business impact from small failures
- 🔄 **[Decision Logic Diagrams](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.0-foundation/diagrams/)** - Visual failure flow

**Quick Start for Blog Post 1**:
```bash
git clone https://github.com/anrogg/ai-agents-failure-recovery
cd ai-agents-failure-recovery
git checkout v1.0-foundation
docker-compose up
python demos/insurance/run_demo.py
```

**Key Code Sections Referenced in Blog**:
- [Hallucination Injection](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.0-foundation/app/failure_injector.py#L204-L207) (Lines 204-207)
- [Failure Mode Definitions](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.0-foundation/app/models.py#L31-L42) (Lines 31-42)
- [Insurance Demo Impact Calculation](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.0-foundation/demos/insurance/demo.py#L85-L105) (Lines 85-105)

### Blog Post 2: "TBD"

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
[See the implementation](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.0-foundation/app/failure_injector.py#L204-L207)

<!-- For entire files -->
[Review the complete failure injector](https://github.com/anrogg/ai-agents-failure-recovery/blob/v1.0-foundation/app/failure_injector.py)

<!-- For specific releases -->
[Download this blog post's code](https://github.com/anrogg/ai-agents-failure-recovery/releases/tag/v1.0-foundation)
```

## 📝 Notes for Repository Maintainers

1. **Tag each blog post release**: `git tag -a v1.0-foundation -m "Blog Post 1: Foundation"`
2. **Update this guide**: Add new blog posts to the table above
3. **Keep permalinks stable**: Don't rewrite history on tagged releases
4. **Test links**: Verify all GitHub links work before publishing blog posts