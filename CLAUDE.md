# Flora Query Tool - Project Context

## Python Environment

**CRITICAL:** This project uses a virtual environment. You MUST activate it before running any Python commands.

```bash
source venv/bin/activate
```

All Python commands (pytest, pip, python scripts, etc.) require the venv to be activated first.

## Running Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

## Project Structure

- `src/taxa/` - Main package code
- `tests/` - Test files
- `scripts/` - Utility scripts (like PoC performance test)
- `venv/` - Virtual environment (DO NOT MODIFY)
- `docs/` - Assorted documentation

## Dependencies

Already installed in venv via `pip install -e '.[dev]'`. No need to reinstall unless pyproject.toml changes.

## Git Workflow

We're in a git worktree at `.worktrees/regional-filtering` on branch `feature/regional-filtering`. All commits should follow conventional commit format.

## Current Task

Implementing the regional filtering optimization per the plan at:
`docs/plans/2026-01-28-regional-filtering-implementation.md`

## Being a Good Neighbor

iNat has some [recommended practices](https://www.inaturalist.org/pages/api+recommended+practices).
We should incorporate these into every design decision, and consider them to
be rules, unless an exception is documented here.  Ipso facto, Rule #1 applies
to those practices not excepted below.

## Realizing Feature Ideas

We will often brainstorm and develop features from
[feature-ideas.md](docs/feature-ideas.md).  Whenever writing an
implementation plan, the final step in the plan should be to move that section
from feature-ideas.md to
[implemented-features.md](docs/implemented-features.md).
