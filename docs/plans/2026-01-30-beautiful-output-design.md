# Beautiful Output Design

## Overview

Add rich table formatting to taxa commands with smart terminal detection, replacing tab-separated output with beautiful Unicode tables when appropriate.

## Goals

- Beautiful table output with Unicode box-drawing characters
- Smart auto-detection: tables for terminals, CSV for pipes
- Manual format override for all contexts
- Reusable formatting layer for all commands
- Clean NULL rendering (empty strings by default)
- Foundation for future tree visualization

## User Interface

### Format Flag

```bash
taxa breakdown Apiaceae                    # auto-detects
taxa breakdown Apiaceae --format table     # force table
taxa breakdown Apiaceae --format csv       # force CSV
taxa breakdown Apiaceae --format tree      # future tree view
```

Values: `auto` (default), `table`, `csv`, `tree` (future)

### NULL Display Flag

```bash
taxa breakdown Apiaceae                    # NULLs render as empty strings
taxa breakdown Apiaceae --show-null        # NULLs render as "NULL"
```

### Auto-Detection Behavior

When `--format auto`:
- Terminal (TTY): render as table
- Pipe/redirect: output CSV

Users can override with explicit `--format` value.

## Implementation

### New Module: src/taxa/formatting.py

```python
def output_results(headers, rows, format='auto', show_null=False):
    """Main entry point for formatted output."""

def format_table(headers, rows, show_null=False):
    """Render using rich.table.Table"""

def format_csv(headers, rows, show_null=False):
    """Render as CSV"""

def detect_format():
    """Check if stdout is a TTY"""
```

### Rich Table Configuration

```python
from rich.console import Console
from rich.table import Table
from rich import box

table = Table(
    show_header=True,
    header_style="bold",
    box=box.ROUNDED,
    show_lines=False
)
```

Features:
- Headers in bold
- Text left-aligned, numbers right-aligned
- Auto-sized columns
- Terminal width detection
- Thousands separators in table mode (21,323)

Example output:
```
╭─────────────────┬────────────────────┬───────────────╮
│ genus           │ observation_count  │ species_count │
├─────────────────┼────────────────────┼───────────────┤
│                 │             21,323 │             0 │
│ Ammi            │                 34 │             1 │
│ Angelica        │                466 │             4 │
╰─────────────────┴────────────────────┴───────────────╯
```

### CSV Configuration

Use Python's standard `csv` module:

```python
import csv
import sys

writer = csv.writer(
    sys.stdout,
    delimiter=',',
    quoting=csv.QUOTE_MINIMAL,
    lineterminator='\n'
)
```

Features:
- RFC 4180 compliant
- Proper escaping
- No thousands separators
- Standard tool compatibility

Example output:
```csv
genus,observation_count,species_count
,21323,0
Ammi,34,1
Angelica,466,4
```

### NULL Handling

Apply transformation in formatters:
- `show_null=False` (default): NULL → `""`
- `show_null=True`: NULL → `"NULL"`

Consistent across all output formats.

### Command Integration

Commands call formatters instead of direct output:

```python
# Before
if cursor.description:
    headers = [desc[0] for desc in cursor.description]
    click.echo('\t'.join(headers))
for row in results:
    click.echo('\t'.join(str(val) for val in row))

# After
headers = [desc[0] for desc in cursor.description]
output_results(headers, results, format=format, show_null=show_null)
```

## Migration Plan

### Phase 1: Create Formatting Module
- Implement `src/taxa/formatting.py`
- Add rich dependency to pyproject.toml
- Test format detection, NULL handling, rendering
- No command changes yet

### Phase 2: Update breakdown Command
- Add `--format` and `--show-null` options
- Replace output logic with `output_results()`
- Test auto-detection and explicit formats

### Phase 3: Update query Command
- Apply same changes
- Standardize output across commands

### Phase 4: Future Commands
- New commands use formatting from start
- Consistent experience throughout tool

## Backwards Compatibility

### Breaking Change: TSV → CSV

Old behavior: tab-separated values
New behavior: comma-separated values (when piped)

Mitigation: CSV is more standard and widely supported
Decision: Document in changelog, worth the migration

### Preserved Behavior

- Headers still in first row
- Data ordering unchanged
- NULL handling configurable

## Future Enhancements

Deferred features to add later:

### Automatic Paging
Invoke pager (like `less`) when output exceeds terminal height. Similar to `git log` behavior.

### Multi-Column Layout
Use `rich.columns.Columns` to arrange items in multiple columns when terminal is wide. Efficient use of horizontal space for long lists.

## Testing Strategy

### Unit Tests
- Format detection (TTY vs pipe)
- NULL handling (show_null true/false)
- Table rendering with mock data
- CSV output validation

### Integration Tests
- breakdown command with real database
- All format combinations
- Pipe detection
- Empty result sets

## Dependencies

Add to pyproject.toml:
```toml
dependencies = [
    "rich>=13.0.0",
    # ... existing deps
]
```

Rich provides:
- Table rendering
- Console/TTY detection
- Color support (future)
- Tree rendering (future)
- ~500KB, well-maintained, industry standard
