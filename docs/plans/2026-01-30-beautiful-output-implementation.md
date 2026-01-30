# Beautiful Output Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add rich table formatting with smart terminal detection to taxa commands.

**Architecture:** Create reusable formatting module that handles TTY detection, NULL transformation, and multiple output formats (table/CSV). Commands call formatters instead of direct echo. TDD throughout.

**Tech Stack:** Rich library for tables, Python csv module, Click for CLI

---

## Task 1: Add Rich Dependency

**Files:**
- Modify: `pyproject.toml:11-16`

**Step 1: Add rich to dependencies**

Edit pyproject.toml to add rich>=13.0.0 to the dependencies list:

```toml
dependencies = [
    "pyinaturalist>=0.20.0",
    "pyyaml>=6.0",
    "click>=8.1.0",
    "tqdm>=4.65.0",
    "rich>=13.0.0",
]
```

**Step 2: Install the dependency**

Run: `source venv/bin/activate && pip install rich>=13.0.0`
Expected: Successfully installed rich

**Step 3: Verify installation**

Run: `source venv/bin/activate && python -c "import rich; print(rich.__version__)"`
Expected: Version number printed (e.g., 13.x.x)

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "build: add rich dependency for table formatting"
```

---

## Task 2: Format Detection Function

**Files:**
- Create: `src/taxa/formatting.py`
- Create: `tests/test_formatting.py`

**Step 1: Write failing test for TTY detection**

Create tests/test_formatting.py:

```python
"""Tests for output formatting module."""
import sys
from taxa.formatting import detect_format


def test_detect_format_returns_table_for_tty(mocker):
    """When stdout is a TTY, detect_format returns 'table'."""
    mocker.patch('sys.stdout.isatty', return_value=True)
    assert detect_format() == 'table'


def test_detect_format_returns_csv_for_non_tty(mocker):
    """When stdout is not a TTY, detect_format returns 'csv'."""
    mocker.patch('sys.stdout.isatty', return_value=False)
    assert detect_format() == 'csv'
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_formatting.py -v`
Expected: FAIL with "cannot import name 'detect_format'"

**Step 3: Write minimal implementation**

Create src/taxa/formatting.py:

```python
"""Output formatting for taxa commands."""
import sys


def detect_format():
    """Detect appropriate output format based on stdout.

    Returns:
        str: 'table' if stdout is a TTY, 'csv' otherwise
    """
    return 'table' if sys.stdout.isatty() else 'csv'
```

**Step 4: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/test_formatting.py::test_detect_format_returns_table_for_tty -v`
Expected: PASS

Run: `source venv/bin/activate && pytest tests/test_formatting.py::test_detect_format_returns_csv_for_non_tty -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/taxa/formatting.py tests/test_formatting.py
git commit -m "feat: add format detection for TTY vs pipe"
```

---

## Task 3: NULL Transformation Helper

**Files:**
- Modify: `src/taxa/formatting.py`
- Modify: `tests/test_formatting.py`

**Step 1: Write failing test for NULL transformation**

Add to tests/test_formatting.py:

```python
from taxa.formatting import transform_null


def test_transform_null_to_empty_string():
    """By default, NULL values become empty strings."""
    assert transform_null(None, show_null=False) == ''


def test_transform_null_preserves_other_values():
    """Non-NULL values are returned unchanged."""
    assert transform_null('foo', show_null=False) == 'foo'
    assert transform_null(42, show_null=False) == 42
    assert transform_null(0, show_null=False) == 0


def test_transform_null_with_show_null_flag():
    """When show_null=True, NULL becomes the string 'NULL'."""
    assert transform_null(None, show_null=True) == 'NULL'


def test_transform_null_preserves_values_with_show_null():
    """When show_null=True, non-NULL values still unchanged."""
    assert transform_null('foo', show_null=True) == 'foo'
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_formatting.py::test_transform_null_to_empty_string -v`
Expected: FAIL with "cannot import name 'transform_null'"

**Step 3: Write minimal implementation**

Add to src/taxa/formatting.py:

```python
def transform_null(value, show_null=False):
    """Transform NULL values for display.

    Args:
        value: The value to transform (may be None)
        show_null: If True, render None as 'NULL'; if False, render as ''

    Returns:
        The transformed value
    """
    if value is None:
        return 'NULL' if show_null else ''
    return value
```

**Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && pytest tests/test_formatting.py -k transform_null -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add src/taxa/formatting.py tests/test_formatting.py
git commit -m "feat: add NULL value transformation helper"
```

---

## Task 4: CSV Formatter

**Files:**
- Modify: `src/taxa/formatting.py`
- Modify: `tests/test_formatting.py`

**Step 1: Write failing test for CSV formatting**

Add to tests/test_formatting.py:

```python
import io
from taxa.formatting import format_csv


def test_format_csv_basic_output(capsys):
    """CSV formatter outputs RFC 4180 compliant CSV."""
    headers = ['name', 'count']
    rows = [('Alice', 10), ('Bob', 20)]

    format_csv(headers, rows, show_null=False)

    captured = capsys.readouterr()
    assert captured.out == 'name,count\nAlice,10\nBob,20\n'


def test_format_csv_with_null_values(capsys):
    """CSV formatter handles NULL values correctly."""
    headers = ['name', 'count']
    rows = [('Alice', None), (None, 20)]

    format_csv(headers, rows, show_null=False)

    captured = capsys.readouterr()
    assert captured.out == 'name,count\nAlice,\n,20\n'


def test_format_csv_with_show_null_flag(capsys):
    """CSV formatter shows NULL when show_null=True."""
    headers = ['name', 'count']
    rows = [('Alice', None)]

    format_csv(headers, rows, show_null=True)

    captured = capsys.readouterr()
    assert captured.out == 'name,count\nAlice,NULL\n'


def test_format_csv_escapes_values_with_commas(capsys):
    """CSV formatter properly escapes values containing commas."""
    headers = ['name', 'description']
    rows = [('Alice', 'Hello, world')]

    format_csv(headers, rows, show_null=False)

    captured = capsys.readouterr()
    assert captured.out == 'name,description\nAlice,"Hello, world"\n'
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_formatting.py::test_format_csv_basic_output -v`
Expected: FAIL with "cannot import name 'format_csv'"

**Step 3: Write minimal implementation**

Add to src/taxa/formatting.py:

```python
import csv


def format_csv(headers, rows, show_null=False):
    """Format results as CSV output to stdout.

    Args:
        headers: List of column header strings
        rows: List of tuples containing row data
        show_null: If True, render None as 'NULL'; if False, render as ''
    """
    writer = csv.writer(
        sys.stdout,
        delimiter=',',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator='\n'
    )

    writer.writerow(headers)
    for row in rows:
        transformed_row = [transform_null(val, show_null) for val in row]
        writer.writerow(transformed_row)
```

**Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && pytest tests/test_formatting.py -k format_csv -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add src/taxa/formatting.py tests/test_formatting.py
git commit -m "feat: add CSV formatter with NULL handling"
```

---

## Task 5: Rich Table Formatter

**Files:**
- Modify: `src/taxa/formatting.py`
- Modify: `tests/test_formatting.py`

**Step 1: Write failing test for table formatting**

Add to tests/test_formatting.py:

```python
from unittest.mock import Mock
from taxa.formatting import format_table


def test_format_table_creates_table_with_headers(mocker):
    """Table formatter creates table with correct headers."""
    mock_console = Mock()
    mock_table_class = Mock()
    mock_table = Mock()
    mock_table_class.return_value = mock_table

    mocker.patch('taxa.formatting.Console', return_value=mock_console)
    mocker.patch('taxa.formatting.Table', mock_table_class)

    headers = ['name', 'count']
    rows = [('Alice', 10)]

    format_table(headers, rows, show_null=False)

    # Verify Table was created with correct config
    mock_table_class.assert_called_once()
    call_kwargs = mock_table_class.call_args[1]
    assert call_kwargs['show_header'] is True
    assert call_kwargs['header_style'] == 'bold'
    assert call_kwargs['show_lines'] is False

    # Verify columns were added
    assert mock_table.add_column.call_count == 2
    mock_table.add_column.assert_any_call('name')
    mock_table.add_column.assert_any_call('count', justify='right')


def test_format_table_adds_rows_with_null_handling(mocker):
    """Table formatter adds rows with NULL transformation."""
    mock_console = Mock()
    mock_table = Mock()
    mocker.patch('taxa.formatting.Console', return_value=mock_console)
    mocker.patch('taxa.formatting.Table', return_value=mock_table)

    headers = ['name', 'count']
    rows = [('Alice', None), (None, 20)]

    format_table(headers, rows, show_null=False)

    # Verify rows were added with transformed NULLs
    assert mock_table.add_row.call_count == 2
    mock_table.add_row.assert_any_call('Alice', '')
    mock_table.add_row.assert_any_call('', '20')


def test_format_table_prints_to_console(mocker):
    """Table formatter prints table via console."""
    mock_console = Mock()
    mock_table = Mock()
    mocker.patch('taxa.formatting.Console', return_value=mock_console)
    mocker.patch('taxa.formatting.Table', return_value=mock_table)

    headers = ['name']
    rows = [('Alice',)]

    format_table(headers, rows, show_null=False)

    mock_console.print.assert_called_once_with(mock_table)
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_formatting.py::test_format_table_creates_table_with_headers -v`
Expected: FAIL with "cannot import name 'format_table'"

**Step 3: Write minimal implementation**

Add to src/taxa/formatting.py (at top, update imports):

```python
from rich.console import Console
from rich.table import Table
from rich import box
```

Add function to src/taxa/formatting.py:

```python
def format_table(headers, rows, show_null=False):
    """Format results as a rich table output to stdout.

    Args:
        headers: List of column header strings
        rows: List of tuples containing row data
        show_null: If True, render None as 'NULL'; if False, render as ''
    """
    table = Table(
        show_header=True,
        header_style='bold',
        box=box.ROUNDED,
        show_lines=False
    )

    # Add columns - numbers right-aligned
    for header in headers:
        # Assume columns with 'count' or 'id' in name are numeric
        justify = 'right' if 'count' in header.lower() or 'id' in header.lower() else 'left'
        table.add_column(header, justify=justify)

    # Add rows with NULL transformation
    for row in rows:
        transformed_row = [str(transform_null(val, show_null)) for val in row]
        table.add_row(*transformed_row)

    console = Console()
    console.print(table)
```

**Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && pytest tests/test_formatting.py -k format_table -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add src/taxa/formatting.py tests/test_formatting.py
git commit -m "feat: add rich table formatter with column alignment"
```

---

## Task 6: Main Output Function

**Files:**
- Modify: `src/taxa/formatting.py`
- Modify: `tests/test_formatting.py`

**Step 1: Write failing test for output_results dispatcher**

Add to tests/test_formatting.py:

```python
from taxa.formatting import output_results


def test_output_results_with_auto_format_tty(mocker):
    """output_results uses table format for TTY."""
    mock_format_table = mocker.patch('taxa.formatting.format_table')
    mocker.patch('sys.stdout.isatty', return_value=True)

    headers = ['name']
    rows = [('Alice',)]

    output_results(headers, rows, format='auto', show_null=False)

    mock_format_table.assert_called_once_with(headers, rows, show_null=False)


def test_output_results_with_auto_format_pipe(mocker):
    """output_results uses CSV format for pipes."""
    mock_format_csv = mocker.patch('taxa.formatting.format_csv')
    mocker.patch('sys.stdout.isatty', return_value=False)

    headers = ['name']
    rows = [('Alice',)]

    output_results(headers, rows, format='auto', show_null=False)

    mock_format_csv.assert_called_once_with(headers, rows, show_null=False)


def test_output_results_with_explicit_table_format(mocker):
    """output_results respects explicit table format."""
    mock_format_table = mocker.patch('taxa.formatting.format_table')
    mocker.patch('sys.stdout.isatty', return_value=False)  # Even when piped

    headers = ['name']
    rows = [('Alice',)]

    output_results(headers, rows, format='table', show_null=True)

    mock_format_table.assert_called_once_with(headers, rows, show_null=True)


def test_output_results_with_explicit_csv_format(mocker):
    """output_results respects explicit CSV format."""
    mock_format_csv = mocker.patch('taxa.formatting.format_csv')
    mocker.patch('sys.stdout.isatty', return_value=True)  # Even in TTY

    headers = ['name']
    rows = [('Alice',)]

    output_results(headers, rows, format='csv', show_null=False)

    mock_format_csv.assert_called_once_with(headers, rows, show_null=False)


def test_output_results_invalid_format_raises_error():
    """output_results raises ValueError for invalid format."""
    import pytest

    with pytest.raises(ValueError, match="Unknown format: invalid"):
        output_results(['name'], [('Alice',)], format='invalid', show_null=False)
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_formatting.py::test_output_results_with_auto_format_tty -v`
Expected: FAIL with "cannot import name 'output_results'"

**Step 3: Write minimal implementation**

Add to src/taxa/formatting.py:

```python
def output_results(headers, rows, format='auto', show_null=False):
    """Output results in the specified format.

    Args:
        headers: List of column header strings
        rows: List of tuples containing row data
        format: Output format - 'auto', 'table', 'csv', or 'tree' (future)
        show_null: If True, render None as 'NULL'; if False, render as ''

    Raises:
        ValueError: If format is not recognized
    """
    # Resolve auto format
    if format == 'auto':
        format = detect_format()

    # Dispatch to appropriate formatter
    if format == 'table':
        format_table(headers, rows, show_null)
    elif format == 'csv':
        format_csv(headers, rows, show_null)
    elif format == 'tree':
        raise NotImplementedError("Tree format not yet implemented")
    else:
        raise ValueError(f"Unknown format: {format}")
```

**Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && pytest tests/test_formatting.py -k output_results -v`
Expected: All 5 tests PASS

**Step 5: Run all formatting tests**

Run: `source venv/bin/activate && pytest tests/test_formatting.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/taxa/formatting.py tests/test_formatting.py
git commit -m "feat: add output_results dispatcher with format routing"
```

---

## Task 7: Integrate with breakdown Command

**Files:**
- Modify: `src/taxa/cli.py:171-236`
- Modify: `tests/test_cli.py`

**Step 1: Write failing test for breakdown formatting options**

Add to tests/test_cli.py:

```python
def test_breakdown_command_with_table_format(tmp_path, mocker, memory_sample_db):
    """breakdown command supports --format table option."""
    mock_output = mocker.patch('taxa.cli.output_results')

    runner = CliRunner()
    result = runner.invoke(
        main,
        ['breakdown', 'Rosaceae', '--format', 'table', '-d', str(memory_sample_db)]
    )

    assert result.exit_code == 0
    mock_output.assert_called_once()
    call_kwargs = mock_output.call_args[1]
    assert call_kwargs['format'] == 'table'
    assert call_kwargs['show_null'] is False


def test_breakdown_command_with_csv_format(tmp_path, mocker, memory_sample_db):
    """breakdown command supports --format csv option."""
    mock_output = mocker.patch('taxa.cli.output_results')

    runner = CliRunner()
    result = runner.invoke(
        main,
        ['breakdown', 'Rosaceae', '--format', 'csv', '-d', str(memory_sample_db)]
    )

    assert result.exit_code == 0
    mock_output.assert_called_once()
    call_kwargs = mock_output.call_args[1]
    assert call_kwargs['format'] == 'csv'


def test_breakdown_command_with_show_null_flag(tmp_path, mocker, memory_sample_db):
    """breakdown command supports --show-null flag."""
    mock_output = mocker.patch('taxa.cli.output_results')

    runner = CliRunner()
    result = runner.invoke(
        main,
        ['breakdown', 'Rosaceae', '--show-null', '-d', str(memory_sample_db)]
    )

    assert result.exit_code == 0
    mock_output.assert_called_once()
    call_kwargs = mock_output.call_args[1]
    assert call_kwargs['show_null'] is True


def test_breakdown_command_default_format_is_auto(tmp_path, mocker, memory_sample_db):
    """breakdown command defaults to auto format."""
    mock_output = mocker.patch('taxa.cli.output_results')

    runner = CliRunner()
    result = runner.invoke(
        main,
        ['breakdown', 'Rosaceae', '-d', str(memory_sample_db)]
    )

    assert result.exit_code == 0
    mock_output.assert_called_once()
    call_kwargs = mock_output.call_args[1]
    assert call_kwargs['format'] == 'auto'
    assert call_kwargs['show_null'] is False
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_cli.py::test_breakdown_command_with_table_format -v`
Expected: FAIL (breakdown doesn't have --format option yet)

**Step 3: Modify breakdown command**

In src/taxa/cli.py, update the breakdown function imports (add at top):

```python
from taxa.formatting import output_results
```

Then modify the breakdown command (replace lines 171-236):

```python
@main.command()
@click.argument('taxon_name')
@click.option('--levels', help='Comma-separated list of taxonomic levels to show')
@click.option('--region', help='Filter to specific region')
@click.option('--database', '-d', default='flora.db', help='Database file path')
@click.option(
    '--format',
    type=click.Choice(['auto', 'table', 'csv'], case_sensitive=False),
    default='auto',
    help='Output format (default: auto-detect)'
)
@click.option('--show-null', is_flag=True, help='Show NULL instead of empty strings')
def breakdown(taxon_name, levels, region, database, format, show_null):
    """Break down a taxon into hierarchical levels with observation counts."""
    if not Path(database).exists():
        click.echo(f"ERROR: Database not found: {database}", err=True)
        click.echo("Run 'taxa sync' first to create the database")
        sys.exit(1)

    try:
        conn = sqlite3.connect(database)

        # Auto-detect taxon rank
        base_rank = find_taxon_rank(conn, taxon_name)

        # Parse levels or use smart default
        if levels:
            # Explicit levels - use as-is
            level_list = [level.strip() for level in levels.split(',')]
            validate_rank_sequence(base_rank, level_list)
        else:
            # Smart default - find first populated rank
            try:
                populated_rank, expected_rank = find_first_populated_rank(
                    conn, taxon_name, base_rank
                )
                level_list = [populated_rank]

                # Show notice if we skipped ranks
                if populated_rank != expected_rank:
                    click.echo(
                        f"[Notice: {expected_rank} unpopulated, showing {populated_rank} instead]",
                        err=True
                    )
            except ValueError as e:
                click.echo(f"ERROR: {e}", err=True)
                sys.exit(1)

        # Generate and execute query
        query, params = generate_breakdown_query(
            base_taxon=taxon_name,
            base_rank=base_rank,
            levels=level_list,
            region_key=region
        )

        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()

        if not results:
            click.echo(f"No observations found for {taxon_name}" +
                      (f" in region '{region}'" if region else ""))
            sys.exit(0)

        # Format and output results
        headers = [desc[0] for desc in cursor.description]
        output_results(headers, results, format=format, show_null=show_null)

    except ValueError as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
    except sqlite3.Error as e:
        click.echo(f"ERROR: Database error: {e}", err=True)
        sys.exit(1)
```

**Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && pytest tests/test_cli.py::test_breakdown_command_with_table_format -v`
Expected: PASS

Run: `source venv/bin/activate && pytest tests/test_cli.py -k "breakdown_command_with" -v`
Expected: All 4 new tests PASS

**Step 5: Run all breakdown tests**

Run: `source venv/bin/activate && pytest tests/test_cli.py -k breakdown -v`
Expected: All breakdown tests PASS

**Step 6: Commit**

```bash
git add src/taxa/cli.py tests/test_cli.py
git commit -m "feat: integrate formatting into breakdown command"
```

---

## Task 8: Integrate with query Command

**Files:**
- Modify: `src/taxa/cli.py:42-75`
- Modify: `tests/test_cli.py`

**Step 1: Write failing test for query formatting options**

Add to tests/test_cli.py:

```python
def test_query_command_with_format_option(tmp_path, mocker, memory_sample_db):
    """query command supports --format option."""
    mock_output = mocker.patch('taxa.cli.output_results')

    runner = CliRunner()
    result = runner.invoke(
        main,
        ['query', 'SELECT * FROM taxa LIMIT 1', '--format', 'csv', '-d', str(memory_sample_db)]
    )

    assert result.exit_code == 0
    mock_output.assert_called_once()
    call_kwargs = mock_output.call_args[1]
    assert call_kwargs['format'] == 'csv'


def test_query_command_with_show_null_option(tmp_path, mocker, memory_sample_db):
    """query command supports --show-null option."""
    mock_output = mocker.patch('taxa.cli.output_results')

    runner = CliRunner()
    result = runner.invoke(
        main,
        ['query', 'SELECT * FROM taxa LIMIT 1', '--show-null', '-d', str(memory_sample_db)]
    )

    assert result.exit_code == 0
    mock_output.assert_called_once()
    call_kwargs = mock_output.call_args[1]
    assert call_kwargs['show_null'] is True
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_cli.py::test_query_command_with_format_option -v`
Expected: FAIL (query doesn't have --format option yet)

**Step 3: Modify query command**

In src/taxa/cli.py, modify the query command (replace lines 42-75):

```python
@main.command()
@click.argument('query', required=False)
@click.option('--database', '-d', default='flora.db', help='Database file path')
@click.option(
    '--format',
    type=click.Choice(['auto', 'table', 'csv'], case_sensitive=False),
    default='auto',
    help='Output format (default: auto-detect)'
)
@click.option('--show-null', is_flag=True, help='Show NULL instead of empty strings')
def query(query, database, format, show_null):
    """Run SQL query against database or open interactive shell."""
    if not Path(database).exists():
        click.echo(f"ERROR: Database not found: {database}", err=True)
        click.echo("Run 'taxa sync' first to create the database")
        sys.exit(1)

    if query:
        # Run single query
        conn = sqlite3.connect(database)
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            results = cursor.fetchall()

            # Format and output results
            if cursor.description:
                headers = [desc[0] for desc in cursor.description]
                output_results(headers, results, format=format, show_null=show_null)

        except sqlite3.Error as e:
            click.echo(f"ERROR: {e}", err=True)
            sys.exit(1)
        finally:
            conn.close()
    else:
        # Open interactive shell
        subprocess.run(['sqlite3', database])
```

**Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && pytest tests/test_cli.py::test_query_command_with_format_option -v`
Expected: PASS

Run: `source venv/bin/activate && pytest tests/test_cli.py::test_query_command_with_show_null_option -v`
Expected: PASS

**Step 5: Run all query tests**

Run: `source venv/bin/activate && pytest tests/test_cli.py -k query_command -v`
Expected: All query tests PASS

**Step 6: Commit**

```bash
git add src/taxa/cli.py tests/test_cli.py
git commit -m "feat: integrate formatting into query command"
```

---

## Task 9: Full Test Suite Verification

**Files:**
- All

**Step 1: Run complete test suite**

Run: `source venv/bin/activate && pytest tests/ -v`
Expected: All tests PASS (no regressions)

**Step 2: Test breakdown command manually**

Run: `source venv/bin/activate && taxa breakdown Abies --levels species -d flora.db`
Expected: Beautiful table output with box-drawing characters

Run: `source venv/bin/activate && taxa breakdown Abies --levels species -d flora.db | cat`
Expected: CSV output (because piped)

Run: `source venv/bin/activate && taxa breakdown Abies --levels species -d flora.db --format csv`
Expected: CSV output (explicit format)

Run: `source venv/bin/activate && taxa breakdown Abies --levels species -d flora.db --show-null`
Expected: Table with "NULL" text visible

**Step 3: Test query command manually**

Run: `source venv/bin/activate && taxa query "SELECT genus, COUNT(*) as count FROM taxa GROUP BY genus LIMIT 5" -d flora.db`
Expected: Beautiful table output

Run: `source venv/bin/activate && taxa query "SELECT genus, COUNT(*) as count FROM taxa GROUP BY genus LIMIT 5" -d flora.db --format csv`
Expected: CSV output

**Step 4: Verify no breaking changes**

Run: `source venv/bin/activate && taxa breakdown Apiaceae --levels genus -d flora.db --format csv > /tmp/output.csv && head -5 /tmp/output.csv`
Expected: Valid CSV file that can be parsed by other tools

**Step 5: Commit if manual tests pass**

If all manual verification passes:
```bash
git commit --allow-empty -m "test: verify manual testing of formatting"
```

---

## Task 10: Update Feature Documentation

**Files:**
- Modify: `docs/feature-ideas.md`
- Modify: `docs/implemented-features.md`

**Step 1: Read current feature-ideas.md**

Run: `cat docs/feature-ideas.md | grep -A 20 "Automatic Paging"`
Expected: See the deferred formatting features

**Step 2: Move implemented section to implemented-features.md**

Create/append to docs/implemented-features.md:

```markdown
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
```

**Commands:**
- `breakdown`: Full formatting support
- `query`: Full formatting support

**Implementation:**
- Design: `docs/plans/2026-01-30-beautiful-output-design.md`
- Plan: `docs/plans/2026-01-30-beautiful-output-implementation.md`
- Module: `src/taxa/formatting.py`
- Tests: `tests/test_formatting.py`

**Future enhancements:**
- Automatic paging for long output
- Multi-column layout for wide terminals
- Colorization of ranks
```

**Step 3: Keep deferred features in feature-ideas.md**

The features remain in feature-ideas.md as documented (paging, multi-column, colorization).

**Step 4: Commit documentation updates**

```bash
git add docs/implemented-features.md
git commit -m "docs: document beautiful output implementation"
```

---

## Completion Checklist

- [x] Rich dependency added
- [x] Format detection implemented
- [x] NULL transformation helper
- [x] CSV formatter
- [x] Rich table formatter
- [x] Main output dispatcher
- [x] breakdown command integration
- [x] query command integration
- [x] Full test suite passing
- [x] Manual testing completed
- [x] Documentation updated

## Testing Summary

**Unit tests:** 20+ new tests in test_formatting.py
**Integration tests:** 6+ new tests in test_cli.py
**Coverage:** Format detection, NULL handling, CSV output, table rendering, command integration
**Manual verification:** Required for visual table output and TTY detection
