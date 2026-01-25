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

## Dependencies

Already installed in venv via `pip install -e '.[dev]'`. No need to reinstall unless pyproject.toml changes.

## Git Workflow

We're in a git worktree at `.worktrees/flora-query-tool`. All commits should follow conventional commit format.
