# Zsh Tab Completion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add comprehensive zsh tab completion with dynamic suggestions from cached database content.

**Architecture:** Three-component system: (1) Python cache generator queries database and writes JSON, (2) CLI commands for installation and cache management, (3) Zsh completion script loads cache and provides context-aware completions.

**Tech Stack:** Python (Click, sqlite3, json, fcntl), Zsh completion framework, jq for JSON parsing in shell.

---

## Task 1: Cache Generator Core

**Files:**
- Create: `src/taxa/completion.py`
- Test: `tests/test_completion.py`

**Step 1: Write failing test for basic cache generation**

```python
# tests/test_completion.py
"""Tests for completion cache generation."""
import json
import sqlite3
from pathlib import Path
import pytest
from taxa.completion import generate_completion_cache
from taxa.schema import create_schema


@pytest.fixture
def sample_db(tmp_path):
    """Create test database with sample data."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    create_schema(conn)

    cursor = conn.cursor()

    # Insert sample taxa
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, genus)
        VALUES (1, 'Quercus', 'genus', 'Fagaceae', 'Quercus')
    """)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, genus, species)
        VALUES (2, 'Quercus alba', 'species', 'Fagaceae', 'Quercus', 'alba')
    """)

    # Insert sample observations
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (1, 'us-ca', 123, 100)
    """)
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (2, 'us-or', 456, 200)
    """)

    conn.commit()
    conn.close()

    return db_path


def test_generate_cache_basic_structure(sample_db):
    """Cache includes required top-level keys."""
    cache = generate_completion_cache(sample_db)

    assert "metadata" in cache
    assert "taxon_names" in cache
    assert "region_keys" in cache
    assert "ranks" in cache


def test_generate_cache_taxon_names(sample_db):
    """Cache includes taxon names from database."""
    cache = generate_completion_cache(sample_db)

    assert "Quercus" in cache["taxon_names"]
    assert "Quercus alba" in cache["taxon_names"]
    assert len(cache["taxon_names"]) == 2
```

**Step 2: Run test to verify it fails**

```bash
source venv/bin/activate
pytest tests/test_completion.py::test_generate_cache_basic_structure -v
```

Expected output: `ModuleNotFoundError: No module named 'taxa.completion'`

**Step 3: Write minimal implementation**

```python
# src/taxa/completion.py
"""Shell completion support for taxa CLI."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from taxa.taxonomy import TAXONOMIC_RANKS


def generate_completion_cache(database_path: Path) -> dict:
    """Generate completion data from database.

    Args:
        database_path: Path to flora.db

    Returns:
        Dictionary with completion data

    Raises:
        FileNotFoundError: If database doesn't exist
    """
    database_path = Path(database_path)

    if not database_path.exists():
        raise FileNotFoundError(f"Database not found: {database_path}")

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Get unique taxon names
    cursor.execute("SELECT DISTINCT scientific_name FROM taxa ORDER BY scientific_name")
    taxon_names = [row[0] for row in cursor.fetchall()]

    # Get unique region keys
    cursor.execute("SELECT DISTINCT region_key FROM observations ORDER BY region_key")
    region_keys = [row[0] for row in cursor.fetchall()]

    # Get database stats
    db_stat = database_path.stat()

    conn.close()

    return {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "database_path": str(database_path.absolute()),
            "database_mtime": db_stat.st_mtime,
            "taxa_count": len(taxon_names),
            "region_count": len(region_keys),
        },
        "taxon_names": taxon_names,
        "region_keys": region_keys,
        "ranks": TAXONOMIC_RANKS,
    }
```

**Step 4: Run tests to verify they pass**

```bash
source venv/bin/activate
pytest tests/test_completion.py::test_generate_cache_basic_structure -v
pytest tests/test_completion.py::test_generate_cache_taxon_names -v
```

Expected output: Both tests PASS

**Step 5: Commit**

```bash
git add src/taxa/completion.py tests/test_completion.py
git commit -m "feat: add completion cache generator

Adds generate_completion_cache() function that queries database
and extracts taxon names, region keys, and taxonomic ranks.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Cache Metadata Tests

**Files:**
- Modify: `tests/test_completion.py`

**Step 1: Write failing tests for metadata**

```python
# tests/test_completion.py (add to existing file)

def test_generate_cache_metadata_fields(sample_db):
    """Metadata includes all required fields."""
    cache = generate_completion_cache(sample_db)

    metadata = cache["metadata"]
    assert "generated_at" in metadata
    assert "database_path" in metadata
    assert "database_mtime" in metadata
    assert "taxa_count" in metadata
    assert "region_count" in metadata


def test_generate_cache_metadata_values(sample_db):
    """Metadata values are correct."""
    cache = generate_completion_cache(sample_db)

    metadata = cache["metadata"]
    assert metadata["taxa_count"] == 2
    assert metadata["region_count"] == 2
    assert metadata["database_mtime"] > 0
    assert str(sample_db) in metadata["database_path"]


def test_generate_cache_region_keys(sample_db):
    """Cache includes region keys from database."""
    cache = generate_completion_cache(sample_db)

    assert "us-ca" in cache["region_keys"]
    assert "us-or" in cache["region_keys"]
    assert len(cache["region_keys"]) == 2


def test_generate_cache_ranks(sample_db):
    """Cache includes taxonomic ranks."""
    cache = generate_completion_cache(sample_db)

    assert "kingdom" in cache["ranks"]
    assert "genus" in cache["ranks"]
    assert "species" in cache["ranks"]
```

**Step 2: Run tests to verify they pass**

```bash
source venv/bin/activate
pytest tests/test_completion.py -v
```

Expected output: All tests PASS (implementation already supports metadata)

**Step 3: Commit**

```bash
git add tests/test_completion.py
git commit -m "test: add metadata validation tests for cache

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Cache Writer with Atomic Write

**Files:**
- Modify: `src/taxa/completion.py`
- Modify: `tests/test_completion.py`

**Step 1: Write failing test for cache writer**

```python
# tests/test_completion.py (add to existing file)

from taxa.completion import write_completion_cache


def test_write_cache_creates_file(tmp_path, sample_db):
    """write_completion_cache creates JSON file."""
    cache_path = tmp_path / "cache.json"
    cache_data = generate_completion_cache(sample_db)

    write_completion_cache(cache_data, cache_path)

    assert cache_path.exists()


def test_write_cache_valid_json(tmp_path, sample_db):
    """Written cache is valid JSON."""
    cache_path = tmp_path / "cache.json"
    cache_data = generate_completion_cache(sample_db)

    write_completion_cache(cache_data, cache_path)

    with open(cache_path) as f:
        loaded = json.load(f)

    assert loaded["taxon_names"] == cache_data["taxon_names"]
    assert loaded["region_keys"] == cache_data["region_keys"]


def test_write_cache_creates_directory(tmp_path, sample_db):
    """write_completion_cache creates parent directories."""
    cache_path = tmp_path / "subdir" / "cache.json"
    cache_data = generate_completion_cache(sample_db)

    write_completion_cache(cache_data, cache_path)

    assert cache_path.exists()
```

**Step 2: Run tests to verify they fail**

```bash
source venv/bin/activate
pytest tests/test_completion.py::test_write_cache_creates_file -v
```

Expected output: `AttributeError: module 'taxa.completion' has no attribute 'write_completion_cache'`

**Step 3: Implement cache writer**

```python
# src/taxa/completion.py (add to existing file)

import fcntl


def write_completion_cache(cache_data: dict, cache_path: Path):
    """Write cache to file with atomic write and flock protection.

    Args:
        cache_data: Dictionary with completion data
        cache_path: Path where cache should be written
    """
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file with exclusive lock
    temp_path = cache_path.with_suffix('.tmp')

    with open(temp_path, 'w') as f:
        # Acquire exclusive lock (blocks if another process has it)
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(cache_data, f, indent=2)
        # Lock released on close

    # Atomic rename
    temp_path.rename(cache_path)
```

**Step 4: Run tests to verify they pass**

```bash
source venv/bin/activate
pytest tests/test_completion.py::test_write_cache_creates_file -v
pytest tests/test_completion.py::test_write_cache_valid_json -v
pytest tests/test_completion.py::test_write_cache_creates_directory -v
```

Expected output: All tests PASS

**Step 5: Commit**

```bash
git add src/taxa/completion.py tests/test_completion.py
git commit -m "feat: add atomic cache writer with flock

Uses temp file + rename for atomic writes and flock for
concurrent write protection.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Cache Path Helper

**Files:**
- Modify: `src/taxa/completion.py`
- Modify: `tests/test_completion.py`

**Step 1: Write failing test for cache path helper**

```python
# tests/test_completion.py (add to existing file)

import os
from taxa.completion import get_cache_path


def test_get_cache_path_default():
    """Cache path uses XDG_CACHE_HOME or ~/.cache."""
    cache_path = get_cache_path("flora.db")

    # Should contain either XDG_CACHE_HOME or ~/.cache
    path_str = str(cache_path)
    assert "taxa" in path_str
    assert "completion-cache-flora.json" in path_str


def test_get_cache_path_respects_xdg(tmp_path, monkeypatch):
    """Cache path respects XDG_CACHE_HOME environment variable."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    cache_path = get_cache_path("flora.db")

    assert str(cache_path).startswith(str(tmp_path))
    assert cache_path == tmp_path / "taxa" / "completion-cache-flora.json"


def test_get_cache_path_different_databases():
    """Different database names get different cache files."""
    cache1 = get_cache_path("flora.db")
    cache2 = get_cache_path("test.db")

    assert "flora" in str(cache1)
    assert "test" in str(cache2)
    assert cache1 != cache2
```

**Step 2: Run tests to verify they fail**

```bash
source venv/bin/activate
pytest tests/test_completion.py::test_get_cache_path_default -v
```

Expected output: `AttributeError: module 'taxa.completion' has no attribute 'get_cache_path'`

**Step 3: Implement cache path helper**

```python
# src/taxa/completion.py (add to existing file)

import os


def get_cache_path(database_name: str) -> Path:
    """Get cache file path for a database.

    Args:
        database_name: Database filename (e.g., 'flora.db')

    Returns:
        Path to cache file in XDG cache directory
    """
    # Extract basename without extension
    db_base = Path(database_name).stem

    # Respect XDG_CACHE_HOME or use ~/.cache
    cache_home = os.environ.get('XDG_CACHE_HOME')
    if cache_home:
        cache_dir = Path(cache_home)
    else:
        cache_dir = Path.home() / '.cache'

    return cache_dir / 'taxa' / f'completion-cache-{db_base}.json'
```

**Step 4: Run tests to verify they pass**

```bash
source venv/bin/activate
pytest tests/test_completion.py::test_get_cache_path_default -v
pytest tests/test_completion.py::test_get_cache_path_respects_xdg -v
pytest tests/test_completion.py::test_get_cache_path_different_databases -v
```

Expected output: All tests PASS

**Step 5: Commit**

```bash
git add src/taxa/completion.py tests/test_completion.py
git commit -m "feat: add XDG-compliant cache path helper

Respects XDG_CACHE_HOME and creates per-database cache files.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Edge Case Tests

**Files:**
- Modify: `tests/test_completion.py`

**Step 1: Write tests for edge cases**

```python
# tests/test_completion.py (add to existing file)

def test_generate_cache_missing_database():
    """generate_completion_cache raises FileNotFoundError for missing DB."""
    with pytest.raises(FileNotFoundError, match="Database not found"):
        generate_completion_cache(Path("/nonexistent/database.db"))


def test_generate_cache_empty_database(tmp_path):
    """Empty database produces valid cache with empty lists."""
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(db_path)
    create_schema(conn)
    conn.close()

    cache = generate_completion_cache(db_path)

    assert cache["taxon_names"] == []
    assert cache["region_keys"] == []
    assert cache["metadata"]["taxa_count"] == 0
    assert cache["metadata"]["region_count"] == 0
```

**Step 2: Run tests to verify they pass**

```bash
source venv/bin/activate
pytest tests/test_completion.py::test_generate_cache_missing_database -v
pytest tests/test_completion.py::test_generate_cache_empty_database -v
```

Expected output: Both tests PASS (implementation already handles these cases)

**Step 3: Commit**

```bash
git add tests/test_completion.py
git commit -m "test: add edge case tests for cache generation

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: CLI Command Group

**Files:**
- Modify: `src/taxa/cli.py`
- Create: `tests/test_completion_cli.py`

**Step 1: Write failing test for completion command group**

```python
# tests/test_completion_cli.py
"""Tests for completion CLI commands."""
from click.testing import CliRunner
from taxa.cli import main


def test_completion_command_exists():
    """Completion command group exists."""
    runner = CliRunner()
    result = runner.invoke(main, ['completion', '--help'])

    assert result.exit_code == 0
    assert 'Manage shell completions' in result.output


def test_completion_shows_subcommands():
    """Completion command lists subcommands."""
    runner = CliRunner()
    result = runner.invoke(main, ['completion', '--help'])

    assert 'generate-cache' in result.output
    assert 'install' in result.output
```

**Step 2: Run test to verify it fails**

```bash
source venv/bin/activate
pytest tests/test_completion_cli.py::test_completion_command_exists -v
```

Expected output: Test fails (completion command doesn't exist)

**Step 3: Add completion command group**

```python
# src/taxa/cli.py (add after existing commands)

@main.group()
def completion():
    """Manage shell completions."""
    pass
```

**Step 4: Run test to verify it passes**

```bash
source venv/bin/activate
pytest tests/test_completion_cli.py::test_completion_command_exists -v
```

Expected output: Test PASS

**Step 5: Commit**

```bash
git add src/taxa/cli.py tests/test_completion_cli.py
git commit -m "feat: add completion command group

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Generate-Cache Command

**Files:**
- Modify: `src/taxa/cli.py`
- Modify: `tests/test_completion_cli.py`

**Step 1: Write failing test for generate-cache command**

```python
# tests/test_completion_cli.py (add to existing file)

import json
from pathlib import Path


def test_generate_cache_command_creates_cache(tmp_path, monkeypatch, sample_db):
    """generate-cache command creates cache file."""
    # Use a fixture or create sample_db here
    # For now, assume sample_db fixture from test_completion.py
    cache_dir = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

    runner = CliRunner()
    result = runner.invoke(main, ['completion', 'generate-cache', '--database', str(sample_db)])

    assert result.exit_code == 0

    # Check cache file was created
    cache_file = cache_dir / 'taxa' / f'completion-cache-{sample_db.stem}.json'
    assert cache_file.exists()


def test_generate_cache_command_missing_database():
    """generate-cache command fails gracefully for missing database."""
    runner = CliRunner()
    result = runner.invoke(main, ['completion', 'generate-cache', '--database', '/nonexistent.db'])

    assert result.exit_code != 0
    assert 'Database not found' in result.output or 'ERROR' in result.output
```

**Step 2: Run test to verify it fails**

```bash
source venv/bin/activate
pytest tests/test_completion_cli.py::test_generate_cache_command_creates_cache -v
```

Expected output: Test fails (generate-cache command doesn't exist)

**Step 3: Implement generate-cache command**

```python
# src/taxa/cli.py (add to completion group)

from taxa.completion import generate_completion_cache, write_completion_cache, get_cache_path


@completion.command('generate-cache')
@click.option('--database', '-d', default='flora.db', help='Database file path')
def generate_cache(database):
    """Generate completion cache from database."""
    try:
        db_path = Path(database)
        cache_data = generate_completion_cache(db_path)
        cache_path = get_cache_path(database)
        write_completion_cache(cache_data, cache_path)

        click.echo(f"Generated completion cache: {cache_path}")
        click.echo(f"  Taxa: {cache_data['metadata']['taxa_count']}")
        click.echo(f"  Regions: {cache_data['metadata']['region_count']}")
    except FileNotFoundError as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"ERROR: Failed to generate cache: {e}", err=True)
        sys.exit(1)
```

**Step 4: Run test to verify it passes**

```bash
source venv/bin/activate
pytest tests/test_completion_cli.py::test_generate_cache_command_creates_cache -v
pytest tests/test_completion_cli.py::test_generate_cache_command_missing_database -v
```

Expected output: Both tests PASS

**Step 5: Commit**

```bash
git add src/taxa/cli.py tests/test_completion_cli.py
git commit -m "feat: add generate-cache CLI command

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Install Command - Basic Structure

**Files:**
- Modify: `src/taxa/cli.py`
- Modify: `tests/test_completion_cli.py`

**Step 1: Write failing test for install command**

```python
# tests/test_completion_cli.py (add to existing file)

def test_install_command_exists():
    """Install command exists."""
    runner = CliRunner()
    result = runner.invoke(main, ['completion', 'install', '--help'])

    assert result.exit_code == 0
    assert 'Install shell completion' in result.output


def test_install_command_creates_completion_script(tmp_path, monkeypatch):
    """Install command creates completion script."""
    config_dir = tmp_path / "config"
    monkeypatch.setenv("HOME", str(tmp_path))

    runner = CliRunner()
    result = runner.invoke(main, ['completion', 'install'])

    assert result.exit_code == 0

    # Check completion script was created
    completion_script = tmp_path / '.config' / 'taxa' / 'completions' / '_taxa'
    assert completion_script.exists()
```

**Step 2: Run test to verify it fails**

```bash
source venv/bin/activate
pytest tests/test_completion_cli.py::test_install_command_exists -v
```

Expected output: Test fails (install command doesn't exist)

**Step 3: Implement basic install command**

```python
# src/taxa/cli.py (add to completion group)

@completion.command()
@click.option('--shell', type=click.Choice(['zsh']), default='zsh', help='Shell type')
def install(shell):
    """Install shell completion for taxa."""
    try:
        # For now, just create the directory structure
        # We'll add the actual completion script in next task
        config_dir = Path.home() / '.config' / 'taxa' / 'completions'
        config_dir.mkdir(parents=True, exist_ok=True)

        completion_script = config_dir / '_taxa'

        # Placeholder - we'll add real script content next
        completion_script.write_text("# taxa completion script\n")

        click.echo(f"Installed completion script: {completion_script}")
        click.echo("\nTo enable completions, add to your ~/.zshrc:")
        click.echo("  fpath=(~/.config/taxa/completions $fpath)")
        click.echo("  autoload -Uz compinit && compinit")
        click.echo("\nThen reload your shell:")
        click.echo("  exec zsh")
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
```

**Step 4: Run tests to verify they pass**

```bash
source venv/bin/activate
pytest tests/test_completion_cli.py::test_install_command_exists -v
pytest tests/test_completion_cli.py::test_install_command_creates_completion_script -v
```

Expected output: Both tests PASS

**Step 5: Commit**

```bash
git add src/taxa/cli.py tests/test_completion_cli.py
git commit -m "feat: add basic install command structure

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Zsh Completion Script Template

**Files:**
- Create: `src/taxa/completion_template.zsh`
- Modify: `src/taxa/cli.py`

**Step 1: Create zsh completion script template**

```zsh
# src/taxa/completion_template.zsh
#compdef taxa

# taxa zsh completion script
# Generated by 'taxa completion install'

_taxa() {
  local -a commands
  commands=(
    'sync:Sync data from iNaturalist API to database'
    'query:Run SQL query or open interactive shell'
    'search:Search for iNaturalist IDs'
    'info:Show database info and stats'
    'breakdown:Break down taxon into hierarchical levels'
    'completion:Manage shell completions'
  )

  _arguments -C \
    '1: :->command' \
    '*:: :->args'

  case $state in
    command)
      _describe 'command' commands
      ;;
    args)
      case ${words[1]} in
        sync)
          _taxa_sync
          ;;
        query)
          _taxa_query
          ;;
        search)
          _taxa_search
          ;;
        info)
          _taxa_info
          ;;
        breakdown)
          _taxa_breakdown
          ;;
        completion)
          _taxa_completion
          ;;
      esac
      ;;
  esac
}

# Subcommand completions (static for now, will add dynamic loading next)

_taxa_sync() {
  _arguments \
    '1:config file:_files -g "*.yaml"' \
    '--timeout[Timeout in seconds]:timeout:' \
    '--dry-run[Estimate only, do not fetch/store]'
}

_taxa_query() {
  _arguments \
    '1:query:' \
    '--database[Database file path]:database:_files -g "*.db"' \
    '-d[Database file path]:database:_files -g "*.db"'
}

_taxa_search() {
  local -a search_commands
  search_commands=(
    'places:Search for place IDs'
    'taxa:Search for taxon IDs'
  )

  _arguments -C \
    '1: :->search_command' \
    '*:: :->search_args'

  case $state in
    search_command)
      _describe 'search command' search_commands
      ;;
    search_args)
      _arguments '1:query:'
      ;;
  esac
}

_taxa_info() {
  _arguments \
    '--database[Database file path]:database:_files -g "*.db"' \
    '-d[Database file path]:database:_files -g "*.db"'
}

_taxa_breakdown() {
  _arguments \
    '1:taxon name:' \
    '--levels[Comma-separated list of taxonomic levels]:levels:' \
    '--region[Filter to specific region]:region:' \
    '--database[Database file path]:database:_files -g "*.db"' \
    '-d[Database file path]:database:_files -g "*.db"'
}

_taxa_completion() {
  local -a completion_commands
  completion_commands=(
    'generate-cache:Generate completion cache from database'
    'install:Install shell completion for taxa'
  )

  _arguments -C \
    '1: :->completion_command' \
    '*:: :->completion_args'

  case $state in
    completion_command)
      _describe 'completion command' completion_commands
      ;;
    completion_args)
      case ${words[1]} in
        generate-cache)
          _arguments \
            '--database[Database file path]:database:_files -g "*.db"' \
            '-d[Database file path]:database:_files -g "*.db"'
          ;;
        install)
          _arguments '--shell[Shell type]:shell:(zsh)'
          ;;
      esac
      ;;
  esac
}

_taxa "$@"
```

**Step 2: Update install command to use template**

```python
# src/taxa/cli.py (modify install function)

import importlib.resources


@completion.command()
@click.option('--shell', type=click.Choice(['zsh']), default='zsh', help='Shell type')
def install(shell):
    """Install shell completion for taxa."""
    try:
        config_dir = Path.home() / '.config' / 'taxa' / 'completions'
        config_dir.mkdir(parents=True, exist_ok=True)

        completion_script = config_dir / '_taxa'

        # Read template from package
        template_path = Path(__file__).parent / 'completion_template.zsh'
        completion_content = template_path.read_text()

        # Write completion script
        completion_script.write_text(completion_content)

        click.echo(f"Installed completion script: {completion_script}")
        click.echo("\nTo enable completions, add to your ~/.zshrc:")
        click.echo("  fpath=(~/.config/taxa/completions $fpath)")
        click.echo("  autoload -Uz compinit && compinit")
        click.echo("\nThen reload your shell:")
        click.echo("  exec zsh")
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
```

**Step 3: Test manually (no automated test for zsh script syntax)**

```bash
source venv/bin/activate
taxa completion install
cat ~/.config/taxa/completions/_taxa
```

Expected: File contains the zsh completion script

**Step 4: Commit**

```bash
git add src/taxa/completion_template.zsh src/taxa/cli.py
git commit -m "feat: add zsh completion script template

Provides static completions for all commands and options.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Dynamic Completion Loading

**Files:**
- Modify: `src/taxa/completion_template.zsh`

**Step 1: Add cache loading function to template**

```zsh
# src/taxa/completion_template.zsh (add near the top, after comments)

# Load completion cache
_taxa_load_cache() {
  local database_name="${1:-flora}"
  local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}"
  local cache_file="${cache_dir}/taxa/completion-cache-${database_name}.json"

  # Check if jq is available
  if ! command -v jq &> /dev/null; then
    # jq not found, skip dynamic completions
    return 1
  fi

  # Check if cache exists
  [[ -f "$cache_file" ]] || return 1

  # Load arrays from cache
  # Use @ flag to split on newlines, f flag to read lines into array
  typeset -ga _taxa_taxon_names
  typeset -ga _taxa_region_keys
  typeset -ga _taxa_ranks

  _taxa_taxon_names=("${(@f)$(jq -r '.taxon_names[]' "$cache_file" 2>/dev/null)}")
  _taxa_region_keys=("${(@f)$(jq -r '.region_keys[]' "$cache_file" 2>/dev/null)}")
  _taxa_ranks=("${(@f)$(jq -r '.ranks[]' "$cache_file" 2>/dev/null)}")

  return 0
}

# Check cache freshness and trigger background regeneration if needed
_taxa_refresh_cache() {
  local database_path="${1:-flora.db}"
  local database_name="$(basename "$database_path" .db)"
  local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}"
  local cache_file="${cache_dir}/taxa/completion-cache-${database_name}.json"

  # If database doesn't exist, nothing to do
  [[ -f "$database_path" ]] || return 1

  # If cache doesn't exist, try to generate it in background
  if [[ ! -f "$cache_file" ]]; then
    (taxa completion generate-cache --database "$database_path" &>/dev/null &)
    return 1
  fi

  # Check if database is newer than cache
  if [[ "$database_path" -nt "$cache_file" ]]; then
    # Database modified, regenerate cache in background
    (taxa completion generate-cache --database "$database_path" &>/dev/null &)
  fi

  return 0
}
```

**Step 2: Update _taxa_breakdown to use dynamic completions**

```zsh
# src/taxa/completion_template.zsh (replace _taxa_breakdown function)

_taxa_breakdown() {
  local database_path="flora.db"

  # Extract database path from command line if specified
  local i
  for ((i=2; i<=$#words; i++)); do
    if [[ "${words[$i]}" == "--database" ]] || [[ "${words[$i]}" == "-d" ]]; then
      database_path="${words[$((i+1))]}"
      break
    fi
  done

  # Attempt to refresh cache (non-blocking)
  _taxa_refresh_cache "$database_path"

  # Load cache
  local database_name="$(basename "$database_path" .db)"
  _taxa_load_cache "$database_name"

  _arguments \
    '1:taxon name:_taxa_complete_taxon' \
    '--levels[Comma-separated list of taxonomic levels]:levels:_taxa_complete_ranks' \
    '--region[Filter to specific region]:region:_taxa_complete_regions' \
    '--database[Database file path]:database:_files -g "*.db"' \
    '-d[Database file path]:database:_files -g "*.db"'
}

# Completion functions for dynamic data

_taxa_complete_taxon() {
  if (( ${#_taxa_taxon_names} > 0 )); then
    _describe 'taxon name' _taxa_taxon_names
  fi
}

_taxa_complete_regions() {
  if (( ${#_taxa_region_keys} > 0 )); then
    _describe 'region' _taxa_region_keys
  fi
}

_taxa_complete_ranks() {
  if (( ${#_taxa_ranks} > 0 )); then
    # For --levels, user can enter comma-separated list
    # This is a simplified completion - just suggest ranks
    _describe 'rank' _taxa_ranks
  fi
}
```

**Step 3: Test manually with real database**

```bash
# Ensure you have a database
source venv/bin/activate
taxa completion install
exec zsh

# Test completions
taxa breakdown <TAB>        # Should show taxon names if DB exists
taxa breakdown --region <TAB>  # Should show region keys
```

Expected: Dynamic completions appear if database exists

**Step 4: Commit**

```bash
git add src/taxa/completion_template.zsh
git commit -m "feat: add dynamic completion loading from cache

Loads taxon names, regions, and ranks from cache. Falls back
gracefully when cache or jq unavailable.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 11: Install Command Cache Generation

**Files:**
- Modify: `src/taxa/cli.py`
- Modify: `tests/test_completion_cli.py`

**Step 1: Write test for cache generation during install**

```python
# tests/test_completion_cli.py (add to existing file)

def test_install_generates_initial_cache(tmp_path, monkeypatch, sample_db):
    """Install command generates initial cache if database exists."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    # Create flora.db in current directory
    import shutil
    test_db = Path.cwd() / "flora.db"
    shutil.copy(sample_db, test_db)

    try:
        runner = CliRunner()
        result = runner.invoke(main, ['completion', 'install'])

        assert result.exit_code == 0

        # Check cache was created
        cache_file = tmp_path / 'cache' / 'taxa' / 'completion-cache-flora.json'
        assert cache_file.exists()
    finally:
        # Clean up
        if test_db.exists():
            test_db.unlink()
```

**Step 2: Run test to verify it fails**

```bash
source venv/bin/activate
pytest tests/test_completion_cli.py::test_install_generates_initial_cache -v
```

Expected output: Test fails (install doesn't generate cache yet)

**Step 3: Update install command to generate cache**

```python
# src/taxa/cli.py (modify install function)

@completion.command()
@click.option('--shell', type=click.Choice(['zsh']), default='zsh', help='Shell type')
def install(shell):
    """Install shell completion for taxa."""
    try:
        config_dir = Path.home() / '.config' / 'taxa' / 'completions'
        config_dir.mkdir(parents=True, exist_ok=True)

        completion_script = config_dir / '_taxa'

        # Read template from package
        template_path = Path(__file__).parent / 'completion_template.zsh'
        completion_content = template_path.read_text()

        # Write completion script
        completion_script.write_text(completion_content)

        click.echo(f"Installed completion script: {completion_script}")

        # Generate initial cache if database exists
        default_db = Path('flora.db')
        if default_db.exists():
            try:
                cache_data = generate_completion_cache(default_db)
                cache_path = get_cache_path('flora.db')
                write_completion_cache(cache_data, cache_path)
                click.echo(f"Generated initial cache: {cache_path}")
            except Exception as e:
                click.echo(f"Warning: Could not generate cache: {e}", err=True)

        click.echo("\nTo enable completions, add to your ~/.zshrc:")
        click.echo("  fpath=(~/.config/taxa/completions $fpath)")
        click.echo("  autoload -Uz compinit && compinit")
        click.echo("\nThen reload your shell:")
        click.echo("  exec zsh")
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
```

**Step 4: Run test to verify it passes**

```bash
source venv/bin/activate
pytest tests/test_completion_cli.py::test_install_generates_initial_cache -v
```

Expected output: Test PASS

**Step 5: Commit**

```bash
git add src/taxa/cli.py tests/test_completion_cli.py
git commit -m "feat: install command generates initial cache

Automatically creates cache from flora.db if it exists.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 12: Documentation and README

**Files:**
- Modify: `README.md`

**Step 1: Add completion section to README**

```markdown
# README.md (add new section after Installation or Usage)

## Shell Completion

Taxa supports intelligent tab completion for zsh shells with dynamic suggestions from your database.

### Installation

Install completion support:

```bash
taxa completion install
```

Then add to your `~/.zshrc`:

```bash
fpath=(~/.config/taxa/completions $fpath)
autoload -Uz compinit && compinit
```

Reload your shell:

```bash
exec zsh
```

### Features

- Complete taxon names from your database
- Complete region keys
- Complete taxonomic ranks for `--levels` option
- Complete file paths for `--database` and config files
- Automatic cache refresh when database changes

### Manual Cache Refresh

The cache updates automatically when the database changes. To manually regenerate:

```bash
taxa completion generate-cache
```

### Requirements

- `jq` command-line JSON processor for dynamic completions
- Without `jq`, static completions (commands and options) still work

Install jq:

```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# Fedora
sudo dnf install jq
```
```

**Step 2: Verify README renders correctly**

```bash
cat README.md | grep -A 30 "Shell Completion"
```

Expected: Completion section is well-formatted

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add shell completion documentation

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 13: End-to-End Manual Testing

**Files:**
- None (manual testing only)

**Step 1: Create test database**

```bash
source venv/bin/activate

# Create test config if needed
cat > test-config.yaml <<EOF
regions:
  - name: "California"
    place_id: 14
taxon_id: 47126  # Plantae
database: test-flora.db
EOF

# Sync small dataset for testing
taxa sync test-config.yaml --dry-run
```

**Step 2: Install and test completions**

```bash
# Install completions
taxa completion install

# Add to .zshrc if not already added
echo 'fpath=(~/.config/taxa/completions $fpath)' >> ~/.zshrc
echo 'autoload -Uz compinit && compinit' >> ~/.zshrc

# Reload shell
exec zsh

# Test command completion
taxa <TAB>
# Expected: shows sync, query, search, info, breakdown, completion

# Test breakdown with taxon completion
taxa breakdown <TAB>
# Expected: shows taxon names from database (if exists)

# Test region completion
taxa breakdown --region <TAB>
# Expected: shows region keys from database

# Test rank completion
taxa breakdown --levels <TAB>
# Expected: shows taxonomic ranks

# Test file completion
taxa query --database <TAB>
# Expected: shows .db files
```

**Step 3: Test cache refresh**

```bash
# Modify database (run sync)
taxa sync test-config.yaml

# Next completion should trigger background cache refresh
taxa breakdown <TAB>

# Check cache was updated
ls -lh ~/.cache/taxa/completion-cache-*.json
```

**Step 4: Test graceful degradation**

```bash
# Test without database
cd /tmp
taxa breakdown <TAB>
# Expected: static completions still work, no errors

# Test without jq (if you can temporarily remove it)
# Expected: completion works but no dynamic suggestions
```

**Step 5: Document test results**

Create test results summary in your journal or notes.

**Step 6: Commit (if any fixes were needed)**

```bash
# If you found and fixed issues during testing
git add <changed files>
git commit -m "fix: issues found during manual testing

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 14: Final Integration Tests

**Files:**
- Modify: `tests/test_completion_cli.py`

**Step 1: Add comprehensive integration test**

```python
# tests/test_completion_cli.py (add to existing file)

def test_full_install_workflow(tmp_path, monkeypatch, sample_db):
    """Test complete install workflow with cache generation."""
    monkeypatch.setenv("HOME", str(tmp_path))
    cache_dir = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

    # Create flora.db in current directory
    import shutil
    test_db = Path.cwd() / "flora.db"
    shutil.copy(sample_db, test_db)

    try:
        runner = CliRunner()

        # Run install
        result = runner.invoke(main, ['completion', 'install'])
        assert result.exit_code == 0
        assert 'Installed completion script' in result.output
        assert 'Generated initial cache' in result.output

        # Verify completion script exists
        completion_script = tmp_path / '.config' / 'taxa' / 'completions' / '_taxa'
        assert completion_script.exists()
        assert '#compdef taxa' in completion_script.read_text()

        # Verify cache exists
        cache_file = cache_dir / 'taxa' / 'completion-cache-flora.json'
        assert cache_file.exists()

        # Verify cache content
        cache_data = json.loads(cache_file.read_text())
        assert 'taxon_names' in cache_data
        assert 'region_keys' in cache_data
        assert 'ranks' in cache_data

        # Run generate-cache with different database
        result2 = runner.invoke(main, ['completion', 'generate-cache', '--database', str(sample_db)])
        assert result2.exit_code == 0

        # Verify second cache created
        cache_file2 = cache_dir / 'taxa' / f'completion-cache-{sample_db.stem}.json'
        assert cache_file2.exists()

    finally:
        if test_db.exists():
            test_db.unlink()
```

**Step 2: Run all completion tests**

```bash
source venv/bin/activate
pytest tests/test_completion.py tests/test_completion_cli.py -v
```

Expected output: All tests PASS

**Step 3: Commit**

```bash
git add tests/test_completion_cli.py
git commit -m "test: add comprehensive integration tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 15: Update Design Status

**Files:**
- Modify: `docs/plans/2026-01-28-zsh-completion-design.md`

**Step 1: Update design document status**

```markdown
# docs/plans/2026-01-28-zsh-completion-design.md (change line 4)

**Status**: Implemented
```

**Step 2: Commit**

```bash
git add docs/plans/2026-01-28-zsh-completion-design.md
git commit -m "docs: mark zsh completion design as implemented

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Post-Implementation

### Verification Checklist

Run all tests:
```bash
source venv/bin/activate
pytest tests/test_completion.py tests/test_completion_cli.py -v
```

Manual verification:
- [ ] `taxa completion install` creates files in correct locations
- [ ] `taxa completion generate-cache` creates valid JSON cache
- [ ] Zsh completion works for commands: `taxa <TAB>`
- [ ] Dynamic completion works for taxa names (if DB exists)
- [ ] Dynamic completion works for regions
- [ ] Dynamic completion works for ranks
- [ ] Graceful fallback when database missing
- [ ] Cache auto-refreshes after `taxa sync`

### Performance Validation

```bash
# Time cache generation with realistic database
time taxa completion generate-cache

# Time completion invocation (in zsh)
# Should be <50ms
time _taxa
```

### Future Enhancements

See design document for future enhancement ideas:
- Bash support
- Fish support
- Fuzzy matching with fzf
- Completion descriptions showing common names
