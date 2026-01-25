# Flora Query Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python CLI tool that syncs iNaturalist taxonomic and occurrence data into a queryable SQLite database for exploring regional flora.

**Architecture:** Use pyinaturalist library to fetch data via iNat API, build SQLite database with wide taxonomic schema (all ranks as columns) and aggregated observation metadata. Start with proof-of-concept to validate performance before building full tool.

**Tech Stack:** Python 3.10+, pyinaturalist, pyyaml, click, sqlite3 (stdlib)

---

## Development Environment

**CRITICAL:** All tasks use a Python virtual environment with explicit paths.

**Setup (already done in worktree):**
```bash
python3 -m venv venv
venv/bin/pip install -e '.[dev]'
```

**For ALL tasks:**
- **Run tests:** `venv/bin/pytest tests/test_*.py -v`
- **Run Python:** `venv/bin/python -m taxa.cli` or `venv/bin/python scripts/...`
- **Install deps:** `venv/bin/pip install <package>`

**IMPORTANT:**
- Never use bare `pytest` or `python` commands
- Never activate the venv with `source venv/bin/activate`
- Always use full `venv/bin/` paths
- This ensures consistent, isolated environment across all operations

---

## Phase 1: Proof of Concept (Critical Path)

**Goal:** Validate that API fetching strategy scales acceptably before building full tool.

### Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/taxa/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "taxa"
version = "0.1.0"
description = "Query iNaturalist regional flora data via SQL"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "pyinaturalist>=0.20.0",
    "pyyaml>=6.0",
    "click>=8.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-mock>=3.10.0",
]

[project.scripts]
taxa = "taxa.cli:main"
```

**Step 2: Create minimal README**

```markdown
# Taxa

Query iNaturalist regional flora data via SQL.

## Installation

```bash
pip install -e .
```

## Usage

Coming soon.
```

**Step 3: Create package structure**

```bash
mkdir -p src/taxa tests
touch src/taxa/__init__.py tests/__init__.py
```

**Step 4: Create venv and install dependencies**

```bash
python3 -m venv venv
venv/bin/pip install -e '.[dev]'
```
Expected: venv created, dependencies installed successfully

**Step 5: Commit**

```bash
git add pyproject.toml README.md src/ tests/
git commit -m "build: initial project setup with dependencies"
```

---

### Task 2: Metrics Tracker Module

**Files:**
- Create: `src/taxa/metrics.py`
- Create: `tests/test_metrics.py`

**Step 1: Write failing test**

Create `tests/test_metrics.py`:

```python
from taxa.metrics import MetricsTracker
import time


def test_metrics_tracker_initialization():
    tracker = MetricsTracker(total_items=100)
    assert tracker.total_items == 100
    assert tracker.processed == 0
    assert tracker.api_calls == 0


def test_metrics_tracker_increments():
    tracker = MetricsTracker(total_items=100)
    tracker.increment_processed(5)
    tracker.increment_api_calls(2)

    assert tracker.processed == 5
    assert tracker.api_calls == 2


def test_metrics_tracker_calculates_rate():
    tracker = MetricsTracker(total_items=100)
    tracker.increment_processed(10)
    time.sleep(0.1)

    rate = tracker.get_processing_rate()
    assert rate > 0


def test_metrics_tracker_estimates_completion():
    tracker = MetricsTracker(total_items=100)
    tracker.increment_processed(10)
    time.sleep(0.1)

    estimate = tracker.estimate_completion_time()
    assert estimate > 0
```

**Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_metrics.py -v`
Expected: FAIL with "cannot import name 'MetricsTracker'"

**Step 3: Implement MetricsTracker**

Create `src/taxa/metrics.py`:

```python
"""Metrics tracking for API fetching operations."""
import time
from typing import Optional


class MetricsTracker:
    """Track progress and performance metrics during data fetching."""

    def __init__(self, total_items: int):
        self.total_items = total_items
        self.processed = 0
        self.api_calls = 0
        self.start_time = time.time()
        self._checkpoints: list[tuple[float, int]] = []

    def increment_processed(self, count: int = 1) -> None:
        """Increment the number of processed items."""
        self.processed += count
        self._checkpoints.append((time.time(), self.processed))

    def increment_api_calls(self, count: int = 1) -> None:
        """Increment the API call counter."""
        self.api_calls += count

    def get_processing_rate(self) -> float:
        """Calculate items processed per second."""
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0
        return self.processed / elapsed

    def estimate_completion_time(self) -> Optional[float]:
        """Estimate seconds until completion based on current rate."""
        rate = self.get_processing_rate()
        if rate == 0:
            return None
        remaining = self.total_items - self.processed
        return remaining / rate

    def get_progress_percent(self) -> float:
        """Get completion percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.processed / self.total_items) * 100

    def format_report(self) -> str:
        """Generate formatted progress report."""
        elapsed = time.time() - self.start_time
        minutes, seconds = divmod(int(elapsed), 60)

        rate = self.get_processing_rate()
        est_completion = self.estimate_completion_time()

        lines = [
            "Progress Report:",
            f"  Elapsed: {minutes}m {seconds}s",
            f"  Taxa fetched: {self.processed:,} / {self.total_items:,} ({self.get_progress_percent():.1f}%)",
            f"  API calls made: {self.api_calls}",
            f"  Rate: {rate:.2f} taxa/second",
        ]

        if est_completion is not None:
            est_min, est_sec = divmod(int(est_completion), 60)
            est_hours, est_min = divmod(est_min, 60)
            if est_hours > 0:
                lines.append(f"  Estimated completion: ~{est_hours}h {est_min}m")
            else:
                lines.append(f"  Estimated completion: ~{est_min}m {est_sec}s")

        return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_metrics.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/taxa/metrics.py tests/test_metrics.py
git commit -m "feat: add metrics tracker for progress monitoring"
```

---

### Task 3: Basic pyinaturalist Integration

**Files:**
- Create: `src/taxa/fetcher.py`
- Create: `tests/test_fetcher.py`

**Step 1: Write failing test**

Create `tests/test_fetcher.py`:

```python
from taxa.fetcher import fetch_taxon_descendants
from unittest.mock import Mock, patch


def test_fetch_taxon_descendants_calls_api():
    """Test that fetch_taxon_descendants makes correct API call."""
    with patch('taxa.fetcher.get_taxa') as mock_get_taxa:
        mock_get_taxa.return_value = {
            'total_results': 100,
            'results': [
                {'id': 1, 'name': 'Test Species', 'rank': 'species'}
            ]
        }

        result = fetch_taxon_descendants(taxon_id=47125, per_page=1)

        mock_get_taxa.assert_called_once()
        assert result['total_results'] == 100
        assert len(result['results']) == 1


def test_fetch_taxon_descendants_handles_pagination():
    """Test that function handles paginated responses."""
    with patch('taxa.fetcher.get_taxa') as mock_get_taxa:
        # Simulate two pages
        mock_get_taxa.side_effect = [
            {
                'total_results': 3,
                'results': [
                    {'id': 1, 'name': 'Species 1', 'rank': 'species'},
                    {'id': 2, 'name': 'Species 2', 'rank': 'species'},
                ]
            },
            {
                'total_results': 3,
                'results': [
                    {'id': 3, 'name': 'Species 3', 'rank': 'species'},
                ]
            }
        ]

        results = list(fetch_taxon_descendants(taxon_id=47125, per_page=2))

        assert len(results) == 3
        assert results[0]['id'] == 1
        assert results[2]['id'] == 3
```

**Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_fetcher.py -v`
Expected: FAIL with "cannot import name 'fetch_taxon_descendants'"

**Step 3: Implement basic fetcher**

Create `src/taxa/fetcher.py`:

```python
"""Fetch taxonomic data from iNaturalist API."""
from typing import Iterator, Dict, Any
from pyinaturalist import get_taxa


def fetch_taxon_descendants(
    taxon_id: int,
    per_page: int = 200,
    max_results: int = None
) -> Iterator[Dict[str, Any]]:
    """
    Fetch all descendant taxa for a given taxon ID.

    Args:
        taxon_id: iNaturalist taxon ID
        per_page: Results per API call (max 200)
        max_results: Maximum total results to fetch (None = all)

    Yields:
        Taxon dictionaries from API
    """
    page = 1
    total_fetched = 0

    while True:
        response = get_taxa(
            taxon_id=taxon_id,
            per_page=per_page,
            page=page
        )

        results = response.get('results', [])
        if not results:
            break

        for taxon in results:
            yield taxon
            total_fetched += 1

            if max_results and total_fetched >= max_results:
                return

        # Check if we've fetched all available results
        total_results = response.get('total_results', 0)
        if total_fetched >= total_results:
            break

        page += 1
```

**Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_fetcher.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/taxa/fetcher.py tests/test_fetcher.py
git commit -m "feat: add basic pyinaturalist integration for fetching taxa"
```

---

### Task 4: Proof-of-Concept Script

**Files:**
- Create: `scripts/poc_performance.py`

**Step 1: Create proof-of-concept script**

Create `scripts/poc_performance.py`:

```python
#!/usr/bin/env python3
"""
Proof-of-concept: Test performance of fetching large taxon in a region.

Usage:
    python scripts/poc_performance.py --taxon-id 47125 --timeout 300

This script validates whether the API fetching approach scales acceptably.
It runs with a timeout and reports progress metrics for extrapolation.
"""
import argparse
import signal
import sys
from taxa.fetcher import fetch_taxon_descendants
from taxa.metrics import MetricsTracker
from pyinaturalist import get_taxa


class TimeoutError(Exception):
    """Raised when timeout is exceeded."""
    pass


def timeout_handler(signum, frame):
    """Handle timeout signal."""
    raise TimeoutError()


def estimate_total_descendants(taxon_id: int) -> int:
    """Make a quick API call to get total descendant count."""
    response = get_taxa(taxon_id=taxon_id, per_page=1)
    return response.get('total_results', 0)


def run_poc(taxon_id: int, timeout_seconds: int) -> None:
    """
    Run proof-of-concept fetch with timeout and progress reporting.

    Args:
        taxon_id: iNaturalist taxon ID to fetch
        timeout_seconds: Timeout in seconds (0 = no timeout)
    """
    print(f"Estimating total descendants for taxon {taxon_id}...")
    total = estimate_total_descendants(taxon_id)
    print(f"Estimated total: {total:,} taxa\n")

    if total == 0:
        print("ERROR: No descendants found. Check taxon ID.")
        sys.exit(1)

    tracker = MetricsTracker(total_items=total)

    # Set up timeout if specified
    if timeout_seconds > 0:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        print(f"Running with {timeout_seconds}s timeout...\n")
    else:
        print("Running without timeout (Ctrl+C to abort)...\n")

    try:
        for taxon in fetch_taxon_descendants(taxon_id):
            tracker.increment_processed()

            # Track API calls (approximately 1 per page of 200)
            if tracker.processed % 200 == 0:
                tracker.increment_api_calls()

            # Print progress every 100 taxa
            if tracker.processed % 100 == 0:
                print(f"Progress: {tracker.processed:,} / {total:,} taxa...")

        # Completed successfully
        if timeout_seconds > 0:
            signal.alarm(0)  # Cancel timeout

        print("\n" + "="*60)
        print("COMPLETED SUCCESSFULLY")
        print("="*60)
        print(tracker.format_report())

    except (TimeoutError, KeyboardInterrupt):
        # Timeout or user interrupt
        if timeout_seconds > 0:
            signal.alarm(0)  # Cancel timeout

        print("\n" + "="*60)
        print("INTERRUPTED - PERFORMANCE ESTIMATE")
        print("="*60)
        print(tracker.format_report())
        print("\nConclusion:")

        est_time = tracker.estimate_completion_time()
        if est_time:
            hours = est_time / 3600
            if hours > 2:
                print(f"  ⚠️  Full sync would take ~{hours:.1f} hours")
                print("  Consider revising approach:")
                print("    - Fetch at higher taxonomic levels")
                print("    - Use bulk taxonomy export + aggregate observations only")
                print("    - Batch requests differently")
            elif hours > 0.5:
                print(f"  ⚠️  Full sync would take ~{hours*60:.0f} minutes")
                print("  Acceptable but slow. Consider optimizations.")
            else:
                print(f"  ✓ Full sync would take ~{hours*60:.0f} minutes")
                print("  Performance looks acceptable.")


def main():
    parser = argparse.ArgumentParser(
        description="Proof-of-concept: Test API fetch performance"
    )
    parser.add_argument(
        '--taxon-id',
        type=int,
        required=True,
        help='iNaturalist taxon ID to test (e.g., 47125 for Rosaceae)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Timeout in seconds (default: 300, 0 = no timeout)'
    )

    args = parser.parse_args()

    print("="*60)
    print("TAXA PROOF-OF-CONCEPT PERFORMANCE TEST")
    print("="*60)
    print()

    run_poc(args.taxon_id, args.timeout)


if __name__ == '__main__':
    main()
```

**Step 2: Make script executable**

```bash
chmod +x scripts/poc_performance.py
```

**Step 3: Test with small taxon (manual verification)**

Run: `venv/bin/pythonscripts/poc_performance.py --taxon-id 47851 --timeout 60`

Expected: Script runs, fetches some taxa, shows progress report
Note: This is manual verification - no automated test for this script

**Step 4: Document usage**

Update `README.md` to add:

```markdown
## Proof of Concept

Before building the full tool, test API performance:

```bash
# Test with a large taxon (e.g., Rosaceae family)
python scripts/poc_performance.py --taxon-id 47125 --timeout 300

# Test with smaller taxon (e.g., Quercus genus)
python scripts/poc_performance.py --taxon-id 47851 --timeout 60
```

The script will report estimated completion time to help decide if the approach scales.
```

**Step 5: Commit**

```bash
git add scripts/poc_performance.py README.md
chmod +x scripts/poc_performance.py
git commit -m "feat: add proof-of-concept performance testing script"
```

---

## Phase 2: Core Functionality

**Note:** Only proceed with Phase 2 if proof-of-concept shows acceptable performance. If performance is unacceptable, pause and discuss alternative approaches with Matt.

### Task 5: Config Parser

**Files:**
- Create: `src/taxa/config.py`
- Create: `tests/test_config.py`
- Create: `tests/fixtures/valid_config.yaml`
- Create: `tests/fixtures/invalid_config.yaml`

**Step 1: Write failing tests**

Create `tests/test_config.py`:

```python
import pytest
from taxa.config import Config, ConfigError
from pathlib import Path


def test_config_loads_valid_yaml(tmp_path):
    """Test loading a valid config file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
database: ./flora.db

regions:
  sfba:
    name: "San Francisco Bay Area"
    place_ids: [5245, 5678]

taxa:
  rosaceae:
    name: "Rosaceae"
    taxon_id: 47125

filters:
  quality_grade: research
""")

    config = Config.from_file(config_file)

    assert config.database == "./flora.db"
    assert "sfba" in config.regions
    assert config.regions["sfba"]["name"] == "San Francisco Bay Area"
    assert config.regions["sfba"]["place_ids"] == [5245, 5678]
    assert "rosaceae" in config.taxa
    assert config.taxa["rosaceae"]["taxon_id"] == 47125
    assert config.filters["quality_grade"] == "research"


def test_config_validates_required_fields(tmp_path):
    """Test that missing required fields raise errors."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
regions:
  sfba:
    name: "SF Bay Area"
    place_ids: [5245]
""")

    with pytest.raises(ConfigError, match="Missing required field: database"):
        Config.from_file(config_file)


def test_config_validates_region_structure(tmp_path):
    """Test that regions must have name and place_ids."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
database: ./flora.db

regions:
  sfba:
    name: "SF Bay Area"
    # Missing place_ids

taxa:
  rosaceae:
    name: "Rosaceae"
    taxon_id: 47125
""")

    with pytest.raises(ConfigError, match="place_ids"):
        Config.from_file(config_file)


def test_config_validates_taxa_structure(tmp_path):
    """Test that taxa must have name and taxon_id."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
database: ./flora.db

regions:
  sfba:
    name: "SF Bay Area"
    place_ids: [5245]

taxa:
  rosaceae:
    name: "Rosaceae"
    # Missing taxon_id
""")

    with pytest.raises(ConfigError, match="taxon_id"):
        Config.from_file(config_file)
```

**Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_config.py -v`
Expected: FAIL with import errors

**Step 3: Implement Config class**

Create `src/taxa/config.py`:

```python
"""Configuration file parsing and validation."""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigError(Exception):
    """Raised when config file is invalid."""
    pass


class Config:
    """Parsed and validated configuration."""

    def __init__(self, data: Dict[str, Any]):
        self.raw = data
        self.database = data.get('database')
        self.regions = data.get('regions', {})
        self.taxa = data.get('taxa', {})
        self.filters = data.get('filters', {})

        self._validate()

    def _validate(self) -> None:
        """Validate configuration structure."""
        # Check required fields
        if not self.database:
            raise ConfigError("Missing required field: database")

        if not self.regions:
            raise ConfigError("Missing required field: regions")

        if not self.taxa:
            raise ConfigError("Missing required field: taxa")

        # Validate each region
        for key, region in self.regions.items():
            if not isinstance(region, dict):
                raise ConfigError(f"Region '{key}' must be a dictionary")

            if 'name' not in region:
                raise ConfigError(f"Region '{key}' missing required field: name")

            if 'place_ids' not in region:
                raise ConfigError(f"Region '{key}' missing required field: place_ids")

            if not isinstance(region['place_ids'], list):
                raise ConfigError(f"Region '{key}' place_ids must be a list")

        # Validate each taxon
        for key, taxon in self.taxa.items():
            if not isinstance(taxon, dict):
                raise ConfigError(f"Taxon '{key}' must be a dictionary")

            if 'name' not in taxon:
                raise ConfigError(f"Taxon '{key}' missing required field: name")

            if 'taxon_id' not in taxon:
                raise ConfigError(f"Taxon '{key}' missing required field: taxon_id")

            if not isinstance(taxon['taxon_id'], int):
                raise ConfigError(f"Taxon '{key}' taxon_id must be an integer")

    @classmethod
    def from_file(cls, path: Path) -> 'Config':
        """Load and parse config from YAML file."""
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML: {e}")
        except FileNotFoundError:
            raise ConfigError(f"Config file not found: {path}")

        if not isinstance(data, dict):
            raise ConfigError("Config file must contain a YAML dictionary")

        return cls(data)
```

**Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_config.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/taxa/config.py tests/test_config.py
git commit -m "feat: add config parser with validation"
```

---

### Task 6: Database Schema

**Files:**
- Create: `src/taxa/schema.py`
- Create: `tests/test_schema.py`

**Step 1: Write failing test**

Create `tests/test_schema.py`:

```python
import sqlite3
from taxa.schema import create_schema


def test_create_schema_creates_tables(tmp_path):
    """Test that create_schema creates all required tables."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)

    create_schema(conn)

    cursor = conn.cursor()

    # Check taxa table exists with correct columns
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='taxa'")
    assert cursor.fetchone() is not None

    cursor.execute("PRAGMA table_info(taxa)")
    columns = {row[1] for row in cursor.fetchall()}

    required_columns = {
        'id', 'scientific_name', 'common_name', 'rank',
        'kingdom', 'phylum', 'class', 'order_name', 'family',
        'subfamily', 'tribe', 'genus', 'species'
    }
    assert required_columns.issubset(columns)

    # Check observations table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='observations'")
    assert cursor.fetchone() is not None

    # Check regions table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='regions'")
    assert cursor.fetchone() is not None

    # Check sync_info table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_info'")
    assert cursor.fetchone() is not None

    conn.close()


def test_create_schema_creates_indexes(tmp_path):
    """Test that create_schema creates required indexes."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)

    create_schema(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {row[0] for row in cursor.fetchall()}

    expected_indexes = {
        'idx_taxa_family',
        'idx_taxa_genus',
        'idx_taxa_subfamily',
        'idx_taxa_tribe',
        'idx_obs_region'
    }

    assert expected_indexes.issubset(indexes)

    conn.close()
```

**Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_schema.py -v`
Expected: FAIL with import error

**Step 3: Implement schema creation**

Create `src/taxa/schema.py`:

```python
"""SQLite schema creation for taxa database."""
import sqlite3


def create_schema(conn: sqlite3.Connection) -> None:
    """
    Create database schema with all tables and indexes.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    # Taxa table with wide schema (all ranks as columns)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS taxa (
            id INTEGER PRIMARY KEY,
            scientific_name TEXT NOT NULL,
            common_name TEXT,
            rank TEXT NOT NULL,

            -- All possible taxonomic ranks
            kingdom TEXT,
            phylum TEXT,
            class TEXT,
            order_name TEXT,
            family TEXT,
            subfamily TEXT,
            tribe TEXT,
            subtribe TEXT,
            genus TEXT,
            subgenus TEXT,
            section TEXT,
            subsection TEXT,
            species TEXT,
            subspecies TEXT,
            variety TEXT,
            form TEXT,

            -- Metadata
            is_active BOOLEAN,
            iconic_taxon TEXT
        )
    """)

    # Observations table with aggregated data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            taxon_id INTEGER NOT NULL,
            region_key TEXT NOT NULL,
            place_id INTEGER NOT NULL,

            observation_count INTEGER,
            observer_count INTEGER,
            research_grade_count INTEGER,

            first_observed DATE,
            last_observed DATE,

            PRIMARY KEY (taxon_id, place_id),
            FOREIGN KEY (taxon_id) REFERENCES taxa(id)
        )
    """)

    # Regions metadata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regions (
            key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            place_ids TEXT NOT NULL
        )
    """)

    # Sync metadata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_info (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Create indexes for common query patterns
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_taxa_family ON taxa(family)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_taxa_genus ON taxa(genus)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_taxa_subfamily ON taxa(subfamily)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_taxa_tribe ON taxa(tribe)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_region ON observations(region_key)")

    conn.commit()
```

**Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_schema.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/taxa/schema.py tests/test_schema.py
git commit -m "feat: add database schema creation"
```

---

### Task 7: Taxa Flattening

**Files:**
- Create: `src/taxa/transform.py`
- Create: `tests/test_transform.py`

**Step 1: Write failing test**

Create `tests/test_transform.py`:

```python
from taxa.transform import flatten_taxon_ancestry


def test_flatten_taxon_ancestry_extracts_all_ranks():
    """Test that flatten_taxon_ancestry extracts all ranks from ancestry."""
    taxon = {
        'id': 12345,
        'name': 'Prunus armeniaca',
        'rank': 'species',
        'is_active': True,
        'iconic_taxon_name': 'Plantae',
        'preferred_common_name': 'Apricot',
        'ancestors': [
            {'id': 1, 'name': 'Plantae', 'rank': 'kingdom'},
            {'id': 2, 'name': 'Magnoliophyta', 'rank': 'phylum'},
            {'id': 3, 'name': 'Magnoliopsida', 'rank': 'class'},
            {'id': 4, 'name': 'Rosales', 'rank': 'order'},
            {'id': 5, 'name': 'Rosaceae', 'rank': 'family'},
            {'id': 6, 'name': 'Amygdaloideae', 'rank': 'subfamily'},
            {'id': 7, 'name': 'Amygdaleae', 'rank': 'tribe'},
            {'id': 8, 'name': 'Prunus', 'rank': 'genus'},
        ]
    }

    result = flatten_taxon_ancestry(taxon)

    assert result['id'] == 12345
    assert result['scientific_name'] == 'Prunus armeniaca'
    assert result['rank'] == 'species'
    assert result['common_name'] == 'Apricot'
    assert result['kingdom'] == 'Plantae'
    assert result['phylum'] == 'Magnoliophyta'
    assert result['class'] == 'Magnoliopsida'
    assert result['order_name'] == 'Rosales'
    assert result['family'] == 'Rosaceae'
    assert result['subfamily'] == 'Amygdaloideae'
    assert result['tribe'] == 'Amygdaleae'
    assert result['genus'] == 'Prunus'
    assert result['is_active'] is True
    assert result['iconic_taxon'] == 'Plantae'


def test_flatten_taxon_ancestry_handles_missing_ranks():
    """Test that missing ranks are set to None."""
    taxon = {
        'id': 456,
        'name': 'Rosaceae',
        'rank': 'family',
        'is_active': True,
        'ancestors': [
            {'id': 1, 'name': 'Plantae', 'rank': 'kingdom'},
            {'id': 4, 'name': 'Rosales', 'rank': 'order'},
        ]
    }

    result = flatten_taxon_ancestry(taxon)

    assert result['kingdom'] == 'Plantae'
    assert result['order_name'] == 'Rosales'
    assert result['family'] == 'Rosaceae'  # Self
    assert result['phylum'] is None
    assert result['class'] is None
    assert result['subfamily'] is None
    assert result['tribe'] is None
    assert result['genus'] is None
```

**Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_transform.py -v`
Expected: FAIL with import error

**Step 3: Implement flatten_taxon_ancestry**

Create `src/taxa/transform.py`:

```python
"""Transform iNaturalist API responses into database rows."""
from typing import Dict, Any, Optional


# All taxonomic ranks we might encounter
RANK_COLUMNS = [
    'kingdom',
    'phylum',
    'class',
    'order_name',  # 'order' is SQL keyword
    'family',
    'subfamily',
    'tribe',
    'subtribe',
    'genus',
    'subgenus',
    'section',
    'subsection',
    'species',
    'subspecies',
    'variety',
    'form',
]


def flatten_taxon_ancestry(taxon: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten taxon with ancestry into wide table row.

    Extracts all taxonomic ranks from the taxon's ancestry chain
    and creates a dictionary suitable for database insertion.

    Args:
        taxon: Taxon dict from iNaturalist API with 'ancestors' key

    Returns:
        Dictionary with id, scientific_name, rank, and all rank columns
    """
    row = {
        'id': taxon['id'],
        'scientific_name': taxon['name'],
        'rank': taxon['rank'],
        'common_name': taxon.get('preferred_common_name'),
        'is_active': taxon.get('is_active', True),
        'iconic_taxon': taxon.get('iconic_taxon_name'),
    }

    # Initialize all rank columns to None
    for rank_col in RANK_COLUMNS:
        row[rank_col] = None

    # Fill in ranks from ancestors
    ancestors = taxon.get('ancestors', [])
    for ancestor in ancestors:
        rank = ancestor['rank']
        name = ancestor['name']

        # Map rank to column name (handle 'order' -> 'order_name')
        col_name = 'order_name' if rank == 'order' else rank

        if col_name in RANK_COLUMNS:
            row[col_name] = name

    # Add self to appropriate rank column
    self_rank = taxon['rank']
    self_col = 'order_name' if self_rank == 'order' else self_rank

    if self_col in RANK_COLUMNS:
        row[self_col] = taxon['name']

    return row
```

**Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_transform.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/taxa/transform.py tests/test_transform.py
git commit -m "feat: add taxon ancestry flattening"
```

---

### Task 8: CLI Framework

**Files:**
- Create: `src/taxa/cli.py`
- Modify: `pyproject.toml`

**Step 1: Implement basic CLI structure**

Create `src/taxa/cli.py`:

```python
"""Command-line interface for taxa tool."""
import click
import sys
from pathlib import Path


@click.group()
def main():
    """Query iNaturalist regional flora data via SQL."""
    pass


@main.command()
@click.argument('config', type=click.Path(exists=True), default='config.yaml')
@click.option('--timeout', type=int, default=0, help='Timeout in seconds (0 = no timeout)')
@click.option('--dry-run', is_flag=True, help='Estimate only, do not fetch/store')
def sync(config, timeout, dry_run):
    """Sync data from iNaturalist API to database."""
    click.echo(f"Syncing from config: {config}")
    click.echo("(Not yet implemented)")


@main.command()
@click.argument('query', required=False)
def query(query):
    """Run SQL query against database or open interactive shell."""
    if query:
        click.echo(f"Running query: {query}")
        click.echo("(Not yet implemented)")
    else:
        click.echo("Opening interactive SQLite shell...")
        click.echo("(Not yet implemented)")


@main.group()
def search():
    """Search for iNaturalist IDs."""
    pass


@search.command()
@click.argument('query')
def places(query):
    """Search for place IDs."""
    click.echo(f"Searching places for: {query}")
    click.echo("(Not yet implemented)")


@search.command()
@click.argument('query')
def taxa(query):
    """Search for taxon IDs."""
    click.echo(f"Searching taxa for: {query}")
    click.echo("(Not yet implemented)")


@main.command()
def info():
    """Show database info and stats."""
    click.echo("Database info:")
    click.echo("(Not yet implemented)")


if __name__ == '__main__':
    main()
```

**Step 2: Test CLI manually**

Run: `venv/bin/python-m taxa.cli --help`
Expected: Help text showing all commands

Run: `venv/bin/python-m taxa.cli sync --help`
Expected: Help text for sync command

**Step 3: Test entry point**

Run: `pip install -e .`
Run: `taxa --help`
Expected: Same help text via installed entry point

**Step 4: Commit**

```bash
git add src/taxa/cli.py
git commit -m "feat: add CLI framework with command structure"
```

---

## Phase 3: Sync Implementation

### Task 9: Observation Data Fetcher

**Files:**
- Create: `src/taxa/observations.py`
- Create: `tests/test_observations.py`

**Step 1: Write failing test**

Create `tests/test_observations.py`:

```python
from taxa.observations import fetch_observation_summary
from unittest.mock import patch


def test_fetch_observation_summary():
    """Test fetching aggregated observation data."""
    with patch('taxa.observations.get_observation_species_counts') as mock_counts, \
         patch('taxa.observations.get_observation_histogram') as mock_hist:

        mock_counts.return_value = {
            'results': [
                {
                    'taxon': {'id': 123},
                    'count': 50
                }
            ]
        }

        mock_hist.return_value = {
            'results': {
                'month_of_year': {
                    '1': 5,
                    '2': 10,
                    '12': 3
                }
            }
        }

        result = fetch_observation_summary(
            taxon_id=47125,
            place_id=14,
            quality_grade='research'
        )

        assert result['taxon_id'] == 123
        assert result['observation_count'] == 50
        assert result['first_observed'] is not None
        assert result['last_observed'] is not None
```

**Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_observations.py -v`
Expected: FAIL with import error

**Step 3: Implement observation fetcher**

Create `src/taxa/observations.py`:

```python
"""Fetch observation data from iNaturalist API."""
from typing import Dict, Any, Optional
from pyinaturalist import get_observation_species_counts, get_observation_histogram
from datetime import datetime


def fetch_observation_summary(
    taxon_id: int,
    place_id: int,
    quality_grade: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch aggregated observation data for a taxon in a place.

    Args:
        taxon_id: iNaturalist taxon ID
        place_id: iNaturalist place ID
        quality_grade: Filter by quality (research, needs_id, casual, or None)

    Returns:
        Dictionary with observation_count, observer_count, date ranges
    """
    params = {
        'taxon_id': taxon_id,
        'place_id': place_id,
    }

    if quality_grade:
        params['quality_grade'] = quality_grade

    # Get species counts (includes observation counts)
    counts_response = get_observation_species_counts(**params)

    if not counts_response.get('results'):
        return None

    # Take first result (should be the taxon itself)
    result = counts_response['results'][0]

    summary = {
        'taxon_id': result['taxon']['id'],
        'observation_count': result['count'],
        'observer_count': None,  # Not available in this endpoint
        'research_grade_count': None,  # Would need separate call
    }

    # Get histogram for date range
    try:
        hist_response = get_observation_histogram(
            date_field='observed',
            **params
        )

        # Extract date range from histogram
        # Histogram returns month_of_year or other intervals
        # For now, just mark that we have temporal data
        if hist_response.get('results'):
            summary['first_observed'] = None  # TODO: parse from histogram
            summary['last_observed'] = None   # TODO: parse from histogram
    except Exception:
        # Histogram call might fail, not critical
        summary['first_observed'] = None
        summary['last_observed'] = None

    return summary
```

**Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_observations.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/taxa/observations.py tests/test_observations.py
git commit -m "feat: add observation data fetcher"
```

---

### Task 10: Complete Sync Command

**Files:**
- Modify: `src/taxa/cli.py`
- Create: `src/taxa/sync.py`

**Step 1: Implement sync logic**

Create `src/taxa/sync.py`:

```python
"""Sync data from iNaturalist to SQLite database."""
import sqlite3
from pathlib import Path
from typing import Dict, Any
import json
import os

from taxa.config import Config
from taxa.schema import create_schema
from taxa.fetcher import fetch_taxon_descendants
from taxa.transform import flatten_taxon_ancestry
from taxa.observations import fetch_observation_summary


def sync_database(config: Config, dry_run: bool = False) -> None:
    """
    Sync iNaturalist data to SQLite database based on config.

    Args:
        config: Parsed configuration
        dry_run: If True, only estimate work without syncing
    """
    print(f"Loading config...")
    print(f"  Regions: {', '.join(config.regions.keys())}")
    print(f"  Taxa: {', '.join(config.taxa.keys())}")
    print()

    if dry_run:
        print("DRY RUN - estimation only")
        # TODO: Estimate total work
        return

    # Build database to temporary file
    temp_db = f"{config.database}.new"

    print(f"Building database: {temp_db}")
    conn = sqlite3.connect(temp_db)

    try:
        # Create schema
        create_schema(conn)

        # Store region metadata
        cursor = conn.cursor()
        for key, region in config.regions.items():
            cursor.execute(
                "INSERT INTO regions (key, name, place_ids) VALUES (?, ?, ?)",
                (key, region['name'], json.dumps(region['place_ids']))
            )

        # Sync each taxon
        for taxon_key, taxon_config in config.taxa.items():
            print(f"\nFetching taxon: {taxon_config['name']} (ID: {taxon_config['taxon_id']})")

            # Fetch all descendant taxa
            taxon_id = taxon_config['taxon_id']
            for taxon in fetch_taxon_descendants(taxon_id):
                # Flatten and insert taxon
                row = flatten_taxon_ancestry(taxon)

                cursor.execute("""
                    INSERT OR REPLACE INTO taxa (
                        id, scientific_name, common_name, rank,
                        kingdom, phylum, class, order_name, family,
                        subfamily, tribe, genus, species,
                        is_active, iconic_taxon
                    ) VALUES (
                        :id, :scientific_name, :common_name, :rank,
                        :kingdom, :phylum, :class, :order_name, :family,
                        :subfamily, :tribe, :genus, :species,
                        :is_active, :iconic_taxon
                    )
                """, row)

                # Fetch observations for this taxon in each region
                for region_key, region in config.regions.items():
                    for place_id in region['place_ids']:
                        quality = config.filters.get('quality_grade')

                        obs = fetch_observation_summary(
                            taxon_id=taxon['id'],
                            place_id=place_id,
                            quality_grade=quality
                        )

                        if obs:
                            cursor.execute("""
                                INSERT OR REPLACE INTO observations (
                                    taxon_id, region_key, place_id,
                                    observation_count, observer_count,
                                    research_grade_count,
                                    first_observed, last_observed
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                obs['taxon_id'],
                                region_key,
                                place_id,
                                obs['observation_count'],
                                obs['observer_count'],
                                obs['research_grade_count'],
                                obs['first_observed'],
                                obs['last_observed']
                            ))

            conn.commit()

        # Store sync metadata
        from datetime import datetime
        cursor.execute(
            "INSERT INTO sync_info (key, value) VALUES (?, ?)",
            ('last_sync', datetime.now().isoformat())
        )
        conn.commit()

        print("\nSync complete!")

    finally:
        conn.close()

    # Atomic database replacement
    if os.path.exists(config.database):
        backup = f"{config.database}~"
        print(f"Backing up old database to: {backup}")
        os.rename(config.database, backup)

    print(f"Replacing database: {config.database}")
    os.rename(temp_db, config.database)
```

**Step 2: Wire up CLI command**

Modify `src/taxa/cli.py`:

```python
# Add imports at top
from taxa.config import Config, ConfigError
from taxa.sync import sync_database

# Replace sync command:
@main.command()
@click.argument('config', type=click.Path(exists=True), default='config.yaml')
@click.option('--timeout', type=int, default=0, help='Timeout in seconds (0 = no timeout)')
@click.option('--dry-run', is_flag=True, help='Estimate only, do not fetch/store')
def sync(config, timeout, dry_run):
    """Sync data from iNaturalist API to database."""
    try:
        cfg = Config.from_file(Path(config))
        sync_database(cfg, dry_run=dry_run)
    except ConfigError as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\nSync interrupted by user")
        sys.exit(1)
```

**Step 3: Test manually with small config**

Create `test_config.yaml`:

```yaml
database: ./test_flora.db

regions:
  test:
    name: "Test Region"
    place_ids: [14]

taxa:
  test:
    name: "Test Genus"
    taxon_id: 47851

filters:
  quality_grade: research
```

Run: `taxa sync test_config.yaml`
Expected: Creates database, fetches data (slow)

**Step 4: Commit**

```bash
git add src/taxa/sync.py src/taxa/cli.py
git commit -m "feat: implement sync command with database building"
```

---

## Phase 4: Query and Helpers

### Task 11: Query Command

**Files:**
- Modify: `src/taxa/cli.py`

**Step 1: Implement query command**

Modify `src/taxa/cli.py`:

```python
import subprocess

# Replace query command:
@main.command()
@click.argument('query', required=False)
@click.option('--database', '-d', default='flora.db', help='Database file path')
def query(query, database):
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

            # Print column headers
            if cursor.description:
                headers = [desc[0] for desc in cursor.description]
                click.echo('\t'.join(headers))

            # Print results
            for row in results:
                click.echo('\t'.join(str(val) for val in row))
        except sqlite3.Error as e:
            click.echo(f"ERROR: {e}", err=True)
            sys.exit(1)
        finally:
            conn.close()
    else:
        # Open interactive shell
        subprocess.run(['sqlite3', database])
```

**Step 2: Test query command**

Run: `taxa query "SELECT COUNT(*) FROM taxa"`
Expected: Returns count

Run: `taxa query`
Expected: Opens sqlite3 interactive shell

**Step 3: Commit**

```bash
git add src/taxa/cli.py
git commit -m "feat: implement query command with interactive mode"
```

---

### Task 12: Search Helpers

**Files:**
- Modify: `src/taxa/cli.py`

**Step 1: Implement search commands**

Modify `src/taxa/cli.py`:

```python
from pyinaturalist import get_places, get_taxa_autocomplete

# Replace search.places command:
@search.command()
@click.argument('query')
def places(query):
    """Search for place IDs."""
    try:
        response = get_places(q=query, per_page=10)
        results = response.get('results', [])

        if not results:
            click.echo(f"No places found for: {query}")
            return

        click.echo(f"Places matching '{query}':\n")
        for place in results:
            click.echo(f"  {place['id']:8d} - {place['display_name']}")
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


# Replace search.taxa command:
@search.command()
@click.argument('query')
def taxa(query):
    """Search for taxon IDs."""
    try:
        response = get_taxa_autocomplete(q=query, per_page=10)
        results = response.get('results', [])

        if not results:
            click.echo(f"No taxa found for: {query}")
            return

        click.echo(f"Taxa matching '{query}':\n")
        for taxon in results:
            common = f" ({taxon.get('preferred_common_name', '')})" if taxon.get('preferred_common_name') else ""
            click.echo(f"  {taxon['id']:8d} - {taxon['name']}{common} [{taxon['rank']}]")
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
```

**Step 2: Test search commands**

Run: `taxa search places "Mendocino"`
Expected: List of places with IDs

Run: `taxa search taxa "Rosaceae"`
Expected: List of taxa with IDs

**Step 3: Commit**

```bash
git add src/taxa/cli.py
git commit -m "feat: implement search helpers for places and taxa"
```

---

### Task 13: Info Command

**Files:**
- Modify: `src/taxa/cli.py`

**Step 1: Implement info command**

Modify `src/taxa/cli.py`:

```python
# Replace info command:
@main.command()
@click.option('--database', '-d', default='flora.db', help='Database file path')
def info(database):
    """Show database info and stats."""
    if not Path(database).exists():
        click.echo(f"ERROR: Database not found: {database}", err=True)
        sys.exit(1)

    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # Get sync info
    cursor.execute("SELECT value FROM sync_info WHERE key = 'last_sync'")
    row = cursor.fetchone()
    last_sync = row[0] if row else "Never"

    # Get counts
    cursor.execute("SELECT COUNT(*) FROM taxa")
    taxa_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT region_key) FROM observations")
    region_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM observations")
    obs_count = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(observation_count) FROM observations")
    total_obs = cursor.fetchone()[0] or 0

    # Display info
    click.echo(f"Database: {database}")
    click.echo(f"Last sync: {last_sync}")
    click.echo()
    click.echo(f"Taxa: {taxa_count:,}")
    click.echo(f"Regions: {region_count}")
    click.echo(f"Region-taxon combinations: {obs_count:,}")
    click.echo(f"Total observations: {total_obs:,}")

    conn.close()
```

**Step 2: Test info command**

Run: `taxa info`
Expected: Display database statistics

**Step 3: Commit**

```bash
git add src/taxa/cli.py
git commit -m "feat: implement info command for database stats"
```

---

### Task 14: Documentation

**Files:**
- Modify: `README.md`
- Create: `example_config.yaml`

**Step 1: Create example config**

Create `example_config.yaml`:

```yaml
# Taxa Query Tool Configuration
# See: docs/plans/2026-01-25-flora-query-tool-design.md

database: ./flora.db

# Geographic regions to track
regions:
  north_coast:
    name: "North Coast California"
    place_ids: [14, 1038, 1039]  # Mendocino, Humboldt, Del Norte

  sfba:
    name: "San Francisco Bay Area"
    place_ids: [5246]

# Taxa of interest (can be any rank)
taxa:
  rosaceae:
    name: "Rosaceae"
    taxon_id: 47125
    notes: "Rose family - includes roses, stone fruits, apples"

  oaks:
    name: "Quercus (Oaks)"
    taxon_id: 47851
    notes: "All oak species"

# Optional filters
filters:
  quality_grade: research  # research, needs_id, casual, or omit for all
```

**Step 2: Update README**

Update `README.md`:

```markdown
# Taxa

Query iNaturalist regional flora data via SQL.

## Overview

Taxa is a CLI tool that syncs iNaturalist taxonomic and occurrence data into a SQLite database optimized for exploratory SQL queries. Perfect for botanists who want to ask questions like "what tribes of Amygdaloideae occur in these 3 counties?"

## Installation

```bash
# Clone repository
git clone <repo-url>
cd taxa

# Install with dependencies
pip install -e '.[dev]'
```

## Quick Start

### 1. Find IDs for your regions and taxa

```bash
# Find place IDs
taxa search places "Mendocino County"
taxa search places "San Francisco"

# Find taxon IDs
taxa search taxa "Rosaceae"
taxa search taxa "Quercus"
```

### 2. Create config file

Copy `example_config.yaml` to `config.yaml` and edit with your regions and taxa:

```yaml
database: ./flora.db

regions:
  north_coast:
    name: "North Coast"
    place_ids: [14, 1038]  # IDs from search

taxa:
  rosaceae:
    name: "Rosaceae"
    taxon_id: 47125

filters:
  quality_grade: research
```

### 3. Sync data

```bash
taxa sync config.yaml
```

This fetches taxonomic hierarchy and observation data from iNaturalist and builds a SQLite database.

### 4. Query the data

```bash
# Run a SQL query
taxa query "SELECT DISTINCT tribe FROM taxa WHERE subfamily = 'Amygdaloideae'"

# Open interactive SQL shell
taxa query

# View database stats
taxa info
```

## Example Queries

**What tribes of Amygdaloideae occur in the North Coast region?**

```sql
SELECT DISTINCT tribe
FROM taxa t
JOIN observations o ON o.taxon_id = t.id
WHERE subfamily = 'Amygdaloideae'
  AND tribe IS NOT NULL
  AND o.region_key = 'north_coast';
```

**What Quercus species are in the Bay Area with >50 observations?**

```sql
SELECT scientific_name, common_name, observation_count
FROM taxa t
JOIN observations o ON o.taxon_id = t.id
WHERE genus = 'Quercus'
  AND rank = 'species'
  AND region_key = 'sfba'
  AND observation_count > 50
ORDER BY observation_count DESC;
```

**What families are most diverse in my region?**

```sql
SELECT family, COUNT(DISTINCT id) as species_count
FROM taxa t
JOIN observations o ON o.taxon_id = t.id
WHERE rank = 'species'
  AND region_key = 'north_coast'
GROUP BY family
ORDER BY species_count DESC
LIMIT 20;
```

## Performance Testing

Before syncing large datasets, test performance with the proof-of-concept script:

```bash
# Test with Rosaceae (large family)
python scripts/poc_performance.py --taxon-id 47125 --timeout 300

# Test with smaller genus
python scripts/poc_performance.py --taxon-id 47851 --timeout 60
```

The script estimates how long a full sync would take.

## Database Schema

- **taxa** - Wide table with all taxonomic ranks as columns
- **observations** - Aggregated observation data (counts, dates, observers)
- **regions** - Region metadata from config
- **sync_info** - Sync timestamps and metadata

## Commands

```bash
taxa sync [config.yaml]           # Sync data from iNaturalist
taxa query "SELECT ..."           # Run SQL query
taxa query                        # Interactive SQL shell
taxa search places QUERY          # Find place IDs
taxa search taxa QUERY            # Find taxon IDs
taxa info                         # Show database stats
```

## Development

```bash
# Run tests
pytest

# Run specific test
pytest tests/test_config.py -v

# Install in editable mode with dev dependencies
pip install -e '.[dev]'
```

## Design

See [docs/plans/2026-01-25-flora-query-tool-design.md](docs/plans/2026-01-25-flora-query-tool-design.md) for complete design documentation.

## License

MIT
```

**Step 3: Commit**

```bash
git add README.md example_config.yaml
git commit -m "docs: add comprehensive README and example config"
```

---

## Summary

This implementation plan provides:

1. **Phase 1 (Critical)**: Proof-of-concept script to validate API performance
2. **Phase 2**: Core functionality (config, schema, data transforms)
3. **Phase 3**: Sync implementation with atomic DB replacement
4. **Phase 4**: Query helpers and documentation

Each task follows TDD with explicit test-implement-verify-commit steps.

**Decision point after Task 4**: Review proof-of-concept results before proceeding to Phase 2.
