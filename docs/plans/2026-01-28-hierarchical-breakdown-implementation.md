# Hierarchical Breakdown Command Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `taxa breakdown` command that generates hierarchical taxonomic queries with automatic subtotals.

**Architecture:** Create shared taxonomy constants module, add breakdown query generator with auto-detection, integrate into CLI with structured flags.

**Tech Stack:** Python, Click, SQLite, pytest

---

## Task 1: Create taxonomy constants module

**Files:**
- Create: `src/taxa/taxonomy.py`
- Test: `tests/test_taxonomy.py`

**Step 1: Write test for TAXONOMIC_RANKS constant**

```python
"""Tests for taxonomy constants and utilities."""
from taxa.taxonomy import TAXONOMIC_RANKS


def test_taxonomic_ranks_exists():
    """Test that TAXONOMIC_RANKS is defined and has expected structure."""
    assert isinstance(TAXONOMIC_RANKS, list)
    assert len(TAXONOMIC_RANKS) > 0


def test_taxonomic_ranks_order():
    """Test that ranks are in correct hierarchical order."""
    expected_order = [
        'kingdom', 'phylum', 'class', 'order_name', 'family',
        'subfamily', 'tribe', 'subtribe', 'genus', 'subgenus',
        'section', 'subsection', 'species', 'subspecies', 'variety', 'form'
    ]
    assert TAXONOMIC_RANKS == expected_order
```

**Step 2: Run test to verify it fails**

```bash
source venv/bin/activate
pytest tests/test_taxonomy.py::test_taxonomic_ranks_exists -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'taxa.taxonomy'"

**Step 3: Create taxonomy module with TAXONOMIC_RANKS**

```python
"""Taxonomic hierarchy constants and utilities."""

# Taxonomic ranks in hierarchical order (highest to lowest)
TAXONOMIC_RANKS = [
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
    'form'
]
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_taxonomy.py -v
```

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/taxa/taxonomy.py tests/test_taxonomy.py
git commit -m "feat: add taxonomy constants module

Add TAXONOMIC_RANKS constant defining hierarchical order of taxonomic
ranks. This will be the single source of truth for rank ordering used
in schema generation and breakdown queries."
```

---

## Task 2: Add get_next_ranks utility function

**Files:**
- Modify: `src/taxa/taxonomy.py`
- Test: `tests/test_taxonomy.py`

**Step 1: Write test for get_next_ranks**

```python
from taxa.taxonomy import get_next_ranks


def test_get_next_ranks_single():
    """Test getting next single rank in hierarchy."""
    assert get_next_ranks('family') == ['subfamily']
    assert get_next_ranks('subfamily') == ['tribe']
    assert get_next_ranks('genus') == ['subgenus']


def test_get_next_ranks_multiple():
    """Test getting multiple next ranks."""
    assert get_next_ranks('family', count=2) == ['subfamily', 'tribe']
    assert get_next_ranks('family', count=3) == ['subfamily', 'tribe', 'subtribe']


def test_get_next_ranks_at_end():
    """Test getting next ranks when near end of hierarchy."""
    # 'form' is last rank, should return empty list
    assert get_next_ranks('form', count=1) == []

    # 'variety' has only 1 rank after it
    assert get_next_ranks('variety', count=2) == ['form']
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_taxonomy.py::test_get_next_ranks_single -v
```

Expected: FAIL with "ImportError: cannot import name 'get_next_ranks'"

**Step 3: Implement get_next_ranks**

Add to `src/taxa/taxonomy.py`:

```python
def get_next_ranks(current_rank, count=1):
    """Get the next N ranks in hierarchy after current_rank.

    Args:
        current_rank: Current taxonomic rank
        count: Number of ranks to return (default 1)

    Returns:
        List of next N rank names, may be shorter if near end of hierarchy

    Raises:
        ValueError: If current_rank not in TAXONOMIC_RANKS
    """
    if current_rank not in TAXONOMIC_RANKS:
        raise ValueError(f"Unknown rank: {current_rank}")

    idx = TAXONOMIC_RANKS.index(current_rank)
    return TAXONOMIC_RANKS[idx+1:idx+1+count]
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_taxonomy.py::test_get_next_ranks_single -v
pytest tests/test_taxonomy.py::test_get_next_ranks_multiple -v
pytest tests/test_taxonomy.py::test_get_next_ranks_at_end -v
```

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/taxa/taxonomy.py tests/test_taxonomy.py
git commit -m "feat: add get_next_ranks utility function

Add function to get next N ranks in taxonomic hierarchy. Handles edge
cases like end of hierarchy and invalid ranks."
```

---

## Task 3: Add sort_ranks utility function

**Files:**
- Modify: `src/taxa/taxonomy.py`
- Test: `tests/test_taxonomy.py`

**Step 1: Write test for sort_ranks**

```python
from taxa.taxonomy import sort_ranks


def test_sort_ranks_already_sorted():
    """Test sorting ranks that are already in order."""
    ranks = ['family', 'subfamily', 'tribe', 'genus']
    assert sort_ranks(ranks) == ['family', 'subfamily', 'tribe', 'genus']


def test_sort_ranks_reverse_order():
    """Test sorting ranks in reverse order."""
    ranks = ['genus', 'tribe', 'subfamily']
    assert sort_ranks(ranks) == ['subfamily', 'tribe', 'genus']


def test_sort_ranks_mixed_order():
    """Test sorting ranks in random order."""
    ranks = ['genus', 'family', 'species', 'tribe']
    assert sort_ranks(ranks) == ['family', 'tribe', 'genus', 'species']


def test_sort_ranks_single():
    """Test sorting single rank."""
    assert sort_ranks(['genus']) == ['genus']
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_taxonomy.py::test_sort_ranks_already_sorted -v
```

Expected: FAIL with "ImportError: cannot import name 'sort_ranks'"

**Step 3: Implement sort_ranks**

Add to `src/taxa/taxonomy.py`:

```python
def sort_ranks(ranks):
    """Sort ranks by hierarchical order.

    Args:
        ranks: List of rank names to sort

    Returns:
        List of ranks sorted from highest to lowest in hierarchy

    Raises:
        ValueError: If any rank is not in TAXONOMIC_RANKS
    """
    for rank in ranks:
        if rank not in TAXONOMIC_RANKS:
            raise ValueError(f"Unknown rank: {rank}")

    return sorted(ranks, key=lambda r: TAXONOMIC_RANKS.index(r))
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_taxonomy.py -k sort_ranks -v
```

Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add src/taxa/taxonomy.py tests/test_taxonomy.py
git commit -m "feat: add sort_ranks utility function

Add function to sort ranks by hierarchical order. Validates all ranks
are known."
```

---

## Task 4: Add validate_rank_sequence utility function

**Files:**
- Modify: `src/taxa/taxonomy.py`
- Test: `tests/test_taxonomy.py`

**Step 1: Write test for validate_rank_sequence**

```python
from taxa.taxonomy import validate_rank_sequence
import pytest


def test_validate_rank_sequence_valid():
    """Test validating correct rank sequences."""
    # Valid sequences should not raise
    validate_rank_sequence('family', ['subfamily', 'tribe'])
    validate_rank_sequence('family', ['genus'])
    validate_rank_sequence('genus', ['species', 'subspecies'])


def test_validate_rank_sequence_invalid_higher():
    """Test that higher ranks are rejected."""
    with pytest.raises(ValueError, match="not below"):
        validate_rank_sequence('family', ['kingdom'])

    with pytest.raises(ValueError, match="not below"):
        validate_rank_sequence('genus', ['family'])


def test_validate_rank_sequence_invalid_same():
    """Test that same rank is rejected."""
    with pytest.raises(ValueError, match="not below"):
        validate_rank_sequence('family', ['family'])


def test_validate_rank_sequence_mixed_valid_invalid():
    """Test mixed valid and invalid ranks."""
    with pytest.raises(ValueError, match="not below"):
        validate_rank_sequence('family', ['subfamily', 'kingdom'])
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_taxonomy.py::test_validate_rank_sequence_valid -v
```

Expected: FAIL with "ImportError: cannot import name 'validate_rank_sequence'"

**Step 3: Implement validate_rank_sequence**

Add to `src/taxa/taxonomy.py`:

```python
def validate_rank_sequence(base_rank, requested_ranks):
    """Validate that requested ranks are all below base_rank in hierarchy.

    Args:
        base_rank: Starting rank
        requested_ranks: List of ranks to validate

    Returns:
        True if all ranks are valid

    Raises:
        ValueError: If any requested rank is not below base_rank
    """
    if base_rank not in TAXONOMIC_RANKS:
        raise ValueError(f"Unknown rank: {base_rank}")

    base_idx = TAXONOMIC_RANKS.index(base_rank)

    for rank in requested_ranks:
        if rank not in TAXONOMIC_RANKS:
            raise ValueError(f"Unknown rank: {rank}")

        rank_idx = TAXONOMIC_RANKS.index(rank)
        if rank_idx <= base_idx:
            raise ValueError(
                f"Cannot break down to '{rank}' - it's not below '{base_rank}'"
            )

    return True
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_taxonomy.py -k validate_rank_sequence -v
```

Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add src/taxa/taxonomy.py tests/test_taxonomy.py
git commit -m "feat: add validate_rank_sequence utility function

Add function to validate that requested ranks are below base rank in
hierarchy. Provides clear error messages for invalid sequences."
```

---

## Task 5: Create breakdown query generation module

**Files:**
- Create: `src/taxa/breakdown.py`
- Test: `tests/test_breakdown.py`

**Step 1: Write test for find_taxon_rank**

```python
"""Tests for breakdown query generation."""
import sqlite3
import pytest
from taxa.breakdown import find_taxon_rank


@pytest.fixture
def test_db():
    """Create in-memory test database with sample taxa."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    # Create simplified taxa table
    cursor.execute("""
        CREATE TABLE taxa (
            id INTEGER PRIMARY KEY,
            scientific_name TEXT,
            family TEXT,
            subfamily TEXT,
            tribe TEXT,
            genus TEXT,
            species TEXT
        )
    """)

    # Insert test data
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, family, subfamily, tribe, genus, species)
        VALUES (1, 'Asteraceae family', 'Asteraceae', NULL, NULL, NULL, NULL)
    """)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, family, subfamily, genus, species)
        VALUES (2, 'Taraxacum officinale', 'Asteraceae', 'Cichorioideae', 'Taraxacum', 'officinale')
    """)

    conn.commit()
    yield conn
    conn.close()


def test_find_taxon_rank_family(test_db):
    """Test finding taxon at family rank."""
    rank = find_taxon_rank(test_db, 'Asteraceae')
    assert rank == 'family'


def test_find_taxon_rank_genus(test_db):
    """Test finding taxon at genus rank."""
    rank = find_taxon_rank(test_db, 'Taraxacum')
    assert rank == 'genus'


def test_find_taxon_rank_not_found(test_db):
    """Test error when taxon not found."""
    with pytest.raises(ValueError, match="not found"):
        find_taxon_rank(test_db, 'NotARealTaxon')
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_breakdown.py::test_find_taxon_rank_family -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'taxa.breakdown'"

**Step 3: Create breakdown module with find_taxon_rank**

```python
"""Breakdown query generation for hierarchical taxonomic queries."""
import sqlite3
from taxa.taxonomy import TAXONOMIC_RANKS


def find_taxon_rank(db, taxon_name):
    """Query each rank column to find where this taxon appears.

    Args:
        db: SQLite database connection
        taxon_name: Name of taxon to search for

    Returns:
        str: The rank where taxon was found

    Raises:
        ValueError: If taxon not found or found at multiple ranks
    """
    cursor = db.cursor()
    found_ranks = []

    for rank in TAXONOMIC_RANKS:
        result = cursor.execute(
            f"SELECT 1 FROM taxa WHERE {rank} = ? LIMIT 1",
            (taxon_name,)
        )
        if result.fetchone():
            found_ranks.append(rank)

    if not found_ranks:
        raise ValueError(f"Taxon '{taxon_name}' not found in database")

    if len(found_ranks) > 1:
        raise ValueError(
            f"Ambiguous taxon '{taxon_name}' found at multiple ranks: {', '.join(found_ranks)}\n"
            f"Specify with --rank: taxa breakdown {taxon_name} --rank {found_ranks[0]}"
        )

    return found_ranks[0]
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_breakdown.py::test_find_taxon_rank_family -v
pytest tests/test_breakdown.py::test_find_taxon_rank_genus -v
pytest tests/test_breakdown.py::test_find_taxon_rank_not_found -v
```

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/taxa/breakdown.py tests/test_breakdown.py
git commit -m "feat: add find_taxon_rank function

Add function to auto-detect which rank a taxon name appears at in the
database. Handles ambiguous names with helpful error messages."
```

---

## Task 6: Add generate_breakdown_query function - single level

**Files:**
- Modify: `src/taxa/breakdown.py`
- Test: `tests/test_breakdown.py`

**Step 1: Write test for single level breakdown**

Add to `tests/test_breakdown.py`:

```python
from taxa.breakdown import generate_breakdown_query


def test_generate_breakdown_query_single_level():
    """Test generating query for single level breakdown."""
    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['subfamily']
    )

    # Should have single SELECT (no UNION)
    assert 'UNION' not in query

    # Should group by subfamily
    assert 'GROUP BY subfamily' in query

    # Should filter by family
    assert 'family = ?' in query

    # Should aggregate observation and species counts
    assert 'SUM(observations.observation_count)' in query
    assert 'COUNT(DISTINCT' in query
    assert 'species' in query.lower()

    # Should order by subfamily, then observation count
    assert 'ORDER BY' in query

    # Params should have base taxon
    assert params == ['Asteraceae']
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_breakdown.py::test_generate_breakdown_query_single_level -v
```

Expected: FAIL with "ImportError: cannot import name 'generate_breakdown_query'"

**Step 3: Implement generate_breakdown_query for single level**

Add to `src/taxa/breakdown.py`:

```python
from taxa.taxonomy import sort_ranks


def generate_breakdown_query(base_taxon, base_rank, levels, region_key=None):
    """Generate UNION query for hierarchical breakdown.

    Args:
        base_taxon: Name of taxon to break down (e.g., "Asteraceae")
        base_rank: Rank of base taxon (e.g., "family")
        levels: List of ranks to break down to (e.g., ["subfamily", "tribe"])
        region_key: Optional region filter

    Returns:
        Tuple of (query_string, params_list)
    """
    # Sort levels to ensure hierarchical order
    levels = sort_ranks(levels)

    queries = []

    # For each level, create a SELECT with all previous levels + current level
    for i, level in enumerate(levels):
        # Columns: all levels up to current (rest are NULL)
        select_cols = []
        group_cols = []

        for j, l in enumerate(levels):
            if j <= i:
                select_cols.append(l)
                group_cols.append(l)
            else:
                select_cols.append(f"NULL as {l}")

        # Add aggregation columns
        select_cols.extend([
            "SUM(observations.observation_count) as observation_count",
            "COUNT(DISTINCT CASE WHEN taxa.rank = 'species' THEN taxa.id END) as species_count"
        ])

        # Build WHERE clause
        where_parts = [f"{base_rank} = ?"]
        params = [base_taxon]

        # Add NOT NULL checks for all levels we're grouping by
        for col in group_cols:
            where_parts.append(f"{col} IS NOT NULL")

        # Add region filter if specified
        if region_key:
            where_parts.append("observations.region_key = ?")
            params.append(region_key)

        query = f"""
        SELECT {', '.join(select_cols)}
        FROM taxa
        JOIN observations ON observations.taxon_id = taxa.id
        WHERE {' AND '.join(where_parts)}
        GROUP BY {', '.join(group_cols)}
        """

        queries.append((query, params))

    # Combine with UNION ALL
    full_query = " UNION ALL ".join(q for q, _ in queries)

    # Add ORDER BY (NULLs first for subtotals, then by observation count)
    order_cols = [f"{level} NULLS FIRST" for level in levels]
    order_cols.append("observation_count DESC")
    full_query += f" ORDER BY {', '.join(order_cols)}"

    # Flatten params
    all_params = [p for _, params in queries for p in params]

    return full_query, all_params
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_breakdown.py::test_generate_breakdown_query_single_level -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/taxa/breakdown.py tests/test_breakdown.py
git commit -m "feat: add generate_breakdown_query function

Generate hierarchical breakdown queries with UNION structure. Initial
implementation supports single level breakdowns."
```

---

## Task 7: Extend generate_breakdown_query for multiple levels

**Files:**
- Modify: `tests/test_breakdown.py`

**Step 1: Write test for multiple level breakdown**

Add to `tests/test_breakdown.py`:

```python
def test_generate_breakdown_query_multiple_levels():
    """Test generating query with multiple hierarchical levels."""
    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['subfamily', 'tribe']
    )

    # Should have UNION ALL for multiple queries
    assert 'UNION ALL' in query

    # Should have 2 SELECTs (one for subfamily, one for subfamily+tribe)
    assert query.count('SELECT') == 2

    # First query groups by subfamily only
    # Second query groups by subfamily and tribe
    assert 'GROUP BY subfamily' in query
    assert 'GROUP BY subfamily, tribe' in query

    # Should have NULL as tribe in first query
    assert 'NULL as tribe' in query

    # Params should have base taxon twice (once per query)
    assert params == ['Asteraceae', 'Asteraceae']


def test_generate_breakdown_query_with_region():
    """Test generating query with region filter."""
    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['subfamily'],
        region_key='north_coast'
    )

    # Should filter by region
    assert 'observations.region_key = ?' in query

    # Params should have both taxon and region
    assert params == ['Asteraceae', 'north_coast']


def test_generate_breakdown_query_skip_levels():
    """Test generating query that skips intermediate levels."""
    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['genus']  # Skip subfamily, tribe, subtribe
    )

    # Should work without intermediate levels
    assert 'GROUP BY genus' in query
    assert params == ['Asteraceae']
```

**Step 2: Run tests to verify they pass**

```bash
pytest tests/test_breakdown.py::test_generate_breakdown_query_multiple_levels -v
pytest tests/test_breakdown.py::test_generate_breakdown_query_with_region -v
pytest tests/test_breakdown.py::test_generate_breakdown_query_skip_levels -v
```

Expected: PASS (implementation already supports these cases)

**Step 3: Commit**

```bash
git add tests/test_breakdown.py
git commit -m "test: add tests for multi-level and filtered breakdowns

Add tests for multiple hierarchical levels, region filtering, and
skipping intermediate ranks."
```

---

## Task 8: Add breakdown CLI command

**Files:**
- Modify: `src/taxa/cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write test for breakdown CLI command**

Add to `tests/test_cli.py`:

```python
def test_breakdown_command_help():
    """Test that breakdown command help works."""
    runner = CliRunner()
    result = runner.invoke(main, ['breakdown', '--help'])
    assert result.exit_code == 0
    assert 'breakdown' in result.output.lower()
    assert '--levels' in result.output
    assert '--region' in result.output


def test_breakdown_command_basic():
    """Test basic breakdown command execution."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create test database with sample data
        import sqlite3
        from taxa.schema import create_schema

        conn = sqlite3.connect('test.db')
        create_schema(conn)

        # Insert test taxa
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO taxa (id, scientific_name, rank, family, subfamily)
            VALUES (1, 'Plant 1', 'species', 'Asteraceae', 'Asteroideae')
        """)
        cursor.execute("""
            INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
            VALUES (1, 'test', 1, 100)
        """)
        conn.commit()
        conn.close()

        result = runner.invoke(main, ['breakdown', 'Asteraceae', '--database', 'test.db'])

        assert result.exit_code == 0
        assert 'Asteroideae' in result.output
        assert 'observation_count' in result.output
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_cli.py::test_breakdown_command_help -v
```

Expected: FAIL with "No such command 'breakdown'"

**Step 3: Add breakdown command to CLI**

Add to `src/taxa/cli.py`:

```python
from taxa.breakdown import find_taxon_rank, generate_breakdown_query
from taxa.taxonomy import get_next_ranks, validate_rank_sequence


@main.command()
@click.argument('taxon_name')
@click.option('--levels', help='Comma-separated list of taxonomic levels to show')
@click.option('--region', help='Filter to specific region')
@click.option('--database', '-d', default='flora.db', help='Database file path')
def breakdown(taxon_name, levels, region, database):
    """Break down a taxon into hierarchical levels with observation counts."""
    if not Path(database).exists():
        click.echo(f"ERROR: Database not found: {database}", err=True)
        click.echo("Run 'taxa sync' first to create the database")
        sys.exit(1)

    try:
        conn = sqlite3.connect(database)

        # Auto-detect taxon rank
        base_rank = find_taxon_rank(conn, taxon_name)

        # Parse levels or use default (next 1 level)
        if levels:
            level_list = [level.strip() for level in levels.split(',')]
            validate_rank_sequence(base_rank, level_list)
        else:
            level_list = get_next_ranks(base_rank, count=1)
            if not level_list:
                click.echo(f"ERROR: No levels below '{base_rank}' in taxonomy", err=True)
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

        # Print column headers
        if cursor.description:
            headers = [desc[0] for desc in cursor.description]
            click.echo('\t'.join(headers))

        # Print results
        for row in results:
            click.echo('\t'.join(str(val) if val is not None else 'NULL' for val in row))

    except ValueError as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
    except sqlite3.Error as e:
        click.echo(f"ERROR: Database error: {e}", err=True)
        sys.exit(1)
    finally:
        conn.close()
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cli.py::test_breakdown_command_help -v
pytest tests/test_cli.py::test_breakdown_command_basic -v
```

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/taxa/cli.py tests/test_cli.py
git commit -m "feat: add breakdown CLI command

Add 'taxa breakdown' command with auto-detection, level specification,
and region filtering. Includes comprehensive error handling."
```

---

## Task 9: Add integration tests with real database

**Files:**
- Create: `tests/test_breakdown_integration.py`

**Step 1: Write integration test**

```python
"""Integration tests for breakdown command with realistic database."""
import sqlite3
import pytest
from pathlib import Path
from taxa.schema import create_schema
from taxa.breakdown import find_taxon_rank, generate_breakdown_query


@pytest.fixture
def populated_db(tmp_path):
    """Create test database with realistic taxonomic data."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    create_schema(conn)

    cursor = conn.cursor()

    # Insert family-level taxa
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family)
        VALUES (1, 'Asteraceae', 'family', 'Asteraceae')
    """)

    # Insert subfamily-level taxa
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily)
        VALUES (2, 'Asteroideae sp.', 'species', 'Asteraceae', 'Asteroideae')
    """)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily)
        VALUES (3, 'Cichorioideae sp.', 'species', 'Asteraceae', 'Cichorioideae')
    """)

    # Insert tribe-level taxa
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily, tribe)
        VALUES (4, 'Anthemideae sp.', 'species', 'Asteraceae', 'Asteroideae', 'Anthemideae')
    """)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily, tribe)
        VALUES (5, 'Astereae sp.', 'species', 'Asteraceae', 'Asteroideae', 'Astereae')
    """)

    # Insert observations
    for taxon_id in [2, 3, 4, 5]:
        cursor.execute("""
            INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
            VALUES (?, 'test_region', 1, ?)
        """, (taxon_id, taxon_id * 100))

    conn.commit()
    yield conn
    conn.close()


def test_breakdown_single_level_integration(populated_db):
    """Test breakdown with single level using real database."""
    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['subfamily']
    )

    cursor = populated_db.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()

    # Should have 2 subfamilies
    assert len(results) == 2

    # Check that subfamilies are present
    subfamilies = [row[0] for row in results]
    assert 'Asteroideae' in subfamilies
    assert 'Cichorioideae' in subfamilies

    # Check observation counts
    for row in results:
        assert row[1] > 0  # observation_count


def test_breakdown_multiple_levels_integration(populated_db):
    """Test breakdown with multiple levels using real database."""
    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['subfamily', 'tribe']
    )

    cursor = populated_db.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()

    # Should have subfamily totals + tribe breakdowns
    # 2 subfamilies + 2 tribes under Asteroideae = 4 rows
    assert len(results) >= 2

    # First row should be subfamily total (tribe=NULL)
    assert results[0][1] is None  # tribe column


def test_breakdown_with_region_filter_integration(populated_db):
    """Test breakdown with region filter using real database."""
    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['subfamily'],
        region_key='test_region'
    )

    cursor = populated_db.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()

    # Should still have results for test_region
    assert len(results) > 0
```

**Step 2: Run test to verify it passes**

```bash
pytest tests/test_breakdown_integration.py -v
```

Expected: PASS (3 tests)

**Step 3: Commit**

```bash
git add tests/test_breakdown_integration.py
git commit -m "test: add integration tests for breakdown

Add integration tests using populated test database to verify
breakdown queries work end-to-end with realistic data."
```

---

## Task 10: Refactor schema.py to use TAXONOMIC_RANKS

**Files:**
- Modify: `src/taxa/schema.py`
- Test: `tests/test_schema.py` (create if needed)

**Step 1: Write test to verify schema uses taxonomy constants**

Create `tests/test_schema.py`:

```python
"""Tests for schema creation."""
import sqlite3
import pytest
from taxa.schema import create_schema
from taxa.taxonomy import TAXONOMIC_RANKS


def test_schema_has_all_rank_columns():
    """Test that taxa table has columns for all taxonomic ranks."""
    conn = sqlite3.connect(':memory:')
    create_schema(conn)

    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(taxa)")
    columns = {row[1] for row in cursor.fetchall()}

    # All ranks from TAXONOMIC_RANKS should be columns
    for rank in TAXONOMIC_RANKS:
        assert rank in columns, f"Missing column for rank: {rank}"

    conn.close()


def test_schema_rank_order_matches_taxonomy():
    """Test that rank columns appear in same order as TAXONOMIC_RANKS."""
    conn = sqlite3.connect(':memory:')
    create_schema(conn)

    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(taxa)")
    all_columns = [row[1] for row in cursor.fetchall()]

    # Extract rank columns in table order
    rank_columns = [col for col in all_columns if col in TAXONOMIC_RANKS]

    # Should match TAXONOMIC_RANKS order
    assert rank_columns == TAXONOMIC_RANKS

    conn.close()
```

**Step 2: Run test to verify current behavior**

```bash
pytest tests/test_schema.py -v
```

Expected: Should PASS if schema already matches, FAIL if column order is different

**Step 3: Refactor schema.py to use TAXONOMIC_RANKS**

Modify `src/taxa/schema.py`:

```python
"""SQLite schema creation for taxa database."""
import sqlite3
from taxa.taxonomy import TAXONOMIC_RANKS


def create_schema(conn: sqlite3.Connection) -> None:
    """
    Create database schema with all tables and indexes.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    # Build rank columns dynamically from TAXONOMIC_RANKS
    rank_columns = ',\n            '.join(f"{rank} TEXT" for rank in TAXONOMIC_RANKS)

    # Taxa table with wide schema (all ranks as columns)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS taxa (
            id INTEGER PRIMARY KEY,
            scientific_name TEXT NOT NULL,
            common_name TEXT,
            rank TEXT NOT NULL,

            -- All possible taxonomic ranks
            {rank_columns},

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

**Step 4: Run tests to verify refactoring works**

```bash
pytest tests/test_schema.py -v
pytest tests/test_breakdown_integration.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/taxa/schema.py tests/test_schema.py
git commit -m "refactor: use TAXONOMIC_RANKS in schema generation

Replace hardcoded rank columns with dynamic generation from
TAXONOMIC_RANKS constant. Ensures schema and taxonomy utilities
stay in sync."
```

---

## Task 11: Add error handling tests for CLI

**Files:**
- Test: `tests/test_cli.py`

**Step 1: Write tests for error cases**

Add to `tests/test_cli.py`:

```python
def test_breakdown_command_taxon_not_found():
    """Test breakdown with non-existent taxon."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        import sqlite3
        from taxa.schema import create_schema

        conn = sqlite3.connect('test.db')
        create_schema(conn)
        conn.close()

        result = runner.invoke(main, ['breakdown', 'NotARealTaxon', '--database', 'test.db'])

        assert result.exit_code == 1
        assert 'not found' in result.output


def test_breakdown_command_invalid_level():
    """Test breakdown with invalid level specification."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        import sqlite3
        from taxa.schema import create_schema

        conn = sqlite3.connect('test.db')
        create_schema(conn)

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO taxa (id, scientific_name, rank, family)
            VALUES (1, 'Asteraceae', 'family', 'Asteraceae')
        """)
        conn.commit()
        conn.close()

        # Try to break down to higher rank
        result = runner.invoke(main, [
            'breakdown', 'Asteraceae',
            '--levels', 'kingdom',
            '--database', 'test.db'
        ])

        assert result.exit_code == 1
        assert 'not below' in result.output


def test_breakdown_command_database_not_found():
    """Test breakdown with missing database."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ['breakdown', 'Asteraceae', '--database', 'missing.db'])

        assert result.exit_code == 1
        assert 'Database not found' in result.output


def test_breakdown_command_empty_results():
    """Test breakdown with no matching observations."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        import sqlite3
        from taxa.schema import create_schema

        conn = sqlite3.connect('test.db')
        create_schema(conn)

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO taxa (id, scientific_name, rank, family)
            VALUES (1, 'Asteraceae', 'family', 'Asteraceae')
        """)
        conn.commit()
        conn.close()

        # No observations inserted, should get empty result
        result = runner.invoke(main, ['breakdown', 'Asteraceae', '--database', 'test.db'])

        assert result.exit_code == 0
        assert 'No observations found' in result.output
```

**Step 2: Run tests to verify they pass**

```bash
pytest tests/test_cli.py -k breakdown_command -v
```

Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: add error handling tests for breakdown command

Add tests for taxon not found, invalid levels, missing database, and
empty results."
```

---

## Task 12: Update documentation

**Files:**
- Modify: `README.md`

**Step 1: Add breakdown command to README**

Add to README.md in the Commands section:

```markdown
## Commands

```bash
taxa sync [config.yaml]           # Sync data from iNaturalist
taxa query "SELECT ..."           # Run SQL query
taxa query                        # Interactive SQL shell
taxa breakdown TAXON [OPTIONS]    # Hierarchical taxonomic breakdown
taxa search places QUERY          # Find place IDs
taxa search taxa QUERY            # Find taxon IDs
taxa info                         # Show database stats
```

## Breakdown Command

Break down a taxon into its constituent hierarchical levels with observation and species counts.

```bash
# Show next level (subfamily) for Asteraceae
taxa breakdown Asteraceae

# Show multiple levels
taxa breakdown Asteraceae --levels subfamily,tribe

# Skip intermediate levels
taxa breakdown Asteraceae --levels genus

# Filter by region
taxa breakdown Rosaceae --region north_coast --levels genus

# Specify database
taxa breakdown "Amygdaloideae" --database flora.db
```

**Output format:**

```
subfamily       tribe           observation_count       species_count
Asteroideae     NULL            45234                   892
Asteroideae     Anthemideae     12456                   234
Asteroideae     Astereae        8901                    156
```

Rows with NULL in lower-level columns are subtotals for the parent level.
```

**Step 2: Verify documentation is clear**

Read through the updated README to ensure:
- Command syntax is clear
- Examples are helpful
- Output format is explained

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add breakdown command to README

Document the new breakdown command with examples and output format
explanation."
```

---

## Task 13: Run full test suite

**Files:**
- None (verification step)

**Step 1: Run all tests**

```bash
source venv/bin/activate
pytest tests/ -v
```

Expected: All tests PASS

**Step 2: Check test coverage (optional)**

```bash
pytest tests/ --cov=src/taxa --cov-report=term-missing
```

Expected: High coverage for new modules (taxonomy.py, breakdown.py)

**Step 3: Manual smoke test**

If you have a real database (mml.db):

```bash
taxa breakdown Asteraceae --database mml.db
taxa breakdown Asteraceae --levels subfamily,tribe --database mml.db
```

Expected: Real results with observation counts

**Step 4: Commit if any fixes needed**

```bash
git add .
git commit -m "fix: address issues found in full test suite"
```

---

## Completion

All tasks complete. The breakdown command is fully implemented with:

✅ Shared taxonomy constants module
✅ Query generation with auto-detection
✅ CLI integration with error handling
✅ Comprehensive test coverage
✅ Documentation updates

**Key features:**
- Auto-detects taxon rank from database
- Supports single or multiple hierarchical levels
- Allows skipping intermediate ranks
- Optional region filtering
- Automatic subtotals at each parent level
- Clear error messages

**Testing:**
- Unit tests for all utility functions
- Integration tests with realistic data
- CLI tests with error cases
- Schema validation tests
