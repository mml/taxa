# Implemented Features

## Beautiful Table Output (2026-01-30)

Rich table formatting with smart terminal detection for all tabular commands.

**Features:**
- Beautiful Unicode box-drawing tables in terminals
- Automatic CSV output when piping to files or other commands
- Manual format override with `--format auto|table|csv`
- Configurable NULL display with `--show-null` flag
- Reusable formatting layer for all commands

**Usage:**
```bash
taxa breakdown Apiaceae                    # auto-detects (table in terminal)
taxa breakdown Apiaceae --format csv       # force CSV
taxa breakdown Apiaceae --show-null        # show NULL values
taxa breakdown Apiaceae | other_tool       # auto CSV when piped
taxa query "SELECT * FROM taxa" --format table  # explicit table format
```

**Commands:**
- `breakdown`: Full formatting support with `--format` and `--show-null` options
- `query`: Full formatting support with `--format` and `--show-null` options

**Implementation:**
- Design: `docs/plans/2026-01-30-beautiful-output-design.md`
- Plan: `docs/plans/2026-01-30-beautiful-output-implementation.md`
- Module: `src/taxa/formatting.py`
- Tests: `tests/test_formatting.py` (20+ unit tests)
- CLI Integration: `src/taxa/cli.py` (breakdown and query commands)

**Technical Details:**
- Uses `rich` library (v13.0.0+) for terminal rendering
- Detects TTY with `sys.stdout.isatty()` for auto format selection
- Python `csv` module for RFC 4180 compliant CSV output
- Numeric columns (count, id) automatically right-aligned
- NULL values configurable (empty string by default, "NULL" with --show-null)

**Future enhancements:**
- Automatic paging for long output
- Multi-column layout for wide terminals
- Colorization of ranks (basic table stable)
