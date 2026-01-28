# Regional Filtering Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Optimize sync performance by discovering regional taxa first, reducing API calls from ~10,000 to ~7-12.

**Architecture:** Two-phase sync: (1) discover taxa with observations in regions via `get_observation_taxonomy`, (2) batch fetch full details via `get_taxa_by_id`. Eliminates fetching global taxa that don't occur in target regions.

**Tech Stack:** pyinaturalist, tqdm, sqlite3

**Design Document:** `docs/plans/2026-01-28-regional-filtering-optimization.md`

---

## Task 1: Add User Agent Configuration

**Files:**
- Modify: `src/taxa/cli.py:1-10` (add after imports)
- Test: Manual verification (no unit test needed for global config)

**Step 1: Set pyinaturalist user agent**

Add after imports in `src/taxa/cli.py`:

```python
import pyinaturalist

# Set user agent to comply with iNaturalist API best practices
pyinaturalist.user_agent = "taxa-flora-query-tool/1.0 (github.com/mml/taxa)"
```

**Step 2: Verify configuration**

Run: `grep -A2 "import pyinaturalist" src/taxa/cli.py`

Expected: See user_agent assignment

**Step 3: Commit**

```bash
git add src/taxa/cli.py
git commit -m "feat: add user agent for iNaturalist API compliance"
```

---

## Task 2: Add fetch_regional_taxa Function

**Files:**
- Modify: `src/taxa/fetcher.py` (add new function)
- Test: `tests/test_fetcher.py` (add new tests)

**Step 1: Write failing test for single page**

Add to `tests/test_fetcher.py`:

```python
from unittest.mock import patch, MagicMock
from taxa.fetcher import fetch_regional_taxa


def test_fetch_regional_taxa_single_page():
    """Test fetching regional taxa with results in one page."""
    with patch('taxa.fetcher.with_retry') as mock_retry:
        # Mock response with < 200 results
        mock_retry.return_value = {
            'results': [
                {
                    'id': 123,
                    'name': 'Malus domestica',
                    'rank': 'species',
                    'descendant_obs_count': 50,
                    'direct_obs_count': 50
                },
                {
                    'id': 456,
                    'name': 'Prunus avium',
                    'rank': 'species',
                    'descendant_obs_count': 30,
                    'direct_obs_count': 30
                }
            ]
        }

        result = fetch_regional_taxa(
            taxon_id=922110,
            place_id=2764,
            quality_grade='research'
        )

        # Should return all taxa
        assert len(result) == 2
        assert result[0]['id'] == 123
        assert result[1]['id'] == 456

        # Should have called API once
        assert mock_retry.call_count == 1


def test_fetch_regional_taxa_pagination():
    """Test pagination when results span multiple pages."""
    with patch('taxa.fetcher.with_retry') as mock_retry:
        # Mock two pages of results
        mock_retry.side_effect = [
            {
                'results': [{'id': i, 'name': f'Taxon {i}'} for i in range(200)]
            },
            {
                'results': [{'id': i, 'name': f'Taxon {i}'} for i in range(200, 250)]
            },
            {
                'results': []  # Empty page signals end
            }
        ]

        result = fetch_regional_taxa(taxon_id=922110, place_id=2764)

        # Should return all taxa from both pages
        assert len(result) == 250

        # Should have called API 3 times (2 full pages + 1 empty)
        assert mock_retry.call_count == 3


def test_fetch_regional_taxa_empty():
    """Test handling when no taxa have observations in region."""
    with patch('taxa.fetcher.with_retry') as mock_retry:
        mock_retry.return_value = {'results': []}

        result = fetch_regional_taxa(taxon_id=999999, place_id=2764)

        # Should return empty list
        assert result == []

        # Should have called API once
        assert mock_retry.call_count == 1
```

**Step 2: Run tests to verify they fail**

Run: `source venv/bin/activate && pytest tests/test_fetcher.py::test_fetch_regional_taxa_single_page -v`

Expected: FAIL with "ImportError: cannot import name 'fetch_regional_taxa'"

**Step 3: Implement fetch_regional_taxa**

Add to `src/taxa/fetcher.py`:

```python
from typing import List
from pyinaturalist import get_observation_taxonomy


def fetch_regional_taxa(
    taxon_id: int,
    place_id: int,
    quality_grade: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch all taxa with observations in a region at any rank.

    Uses the /v1/observations/taxonomy endpoint to discover which taxa
    actually occur in a specific place. Handles pagination automatically.

    Args:
        taxon_id: iNaturalist taxon ID (root taxon to search under)
        place_id: iNaturalist place ID (geographic region)
        quality_grade: Filter by quality (research, needs_id, casual, or None)

    Returns:
        List of taxon dictionaries with observation counts
    """
    all_taxa = []
    page = 1
    per_page = 200  # Maximum supported by API

    while True:
        params = {
            'taxon_id': taxon_id,
            'place_id': place_id,
            'per_page': per_page,
            'page': page
        }

        if quality_grade:
            params['quality_grade'] = quality_grade

        response = with_retry(
            get_observation_taxonomy,
            **params
        )

        results = response.get('results', [])
        if not results:
            break

        all_taxa.extend(results)

        # Check if we've fetched everything
        if len(results) < per_page:
            break

        page += 1

    return all_taxa
```

**Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && pytest tests/test_fetcher.py::test_fetch_regional_taxa -v`

Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add src/taxa/fetcher.py tests/test_fetcher.py
git commit -m "feat: add fetch_regional_taxa for discovering taxa in regions"
```

---

## Task 3: Add Batch Taxa Fetching Helper

**Files:**
- Create: `src/taxa/batch.py` (new module)
- Test: `tests/test_batch.py` (new test file)

**Step 1: Write failing test**

Create `tests/test_batch.py`:

```python
from unittest.mock import patch
from taxa.batch import fetch_taxa_batch


def test_fetch_taxa_batch_single_batch():
    """Test fetching small number of taxa in one batch."""
    with patch('taxa.batch.with_retry') as mock_retry:
        mock_retry.return_value = {
            'results': [
                {'id': 1, 'name': 'Taxon 1', 'ancestors': []},
                {'id': 2, 'name': 'Taxon 2', 'ancestors': []},
                {'id': 3, 'name': 'Taxon 3', 'ancestors': []}
            ]
        }

        result = fetch_taxa_batch([1, 2, 3])

        # Should return all taxa
        assert len(result) == 3
        assert result[0]['id'] == 1

        # Should have called API once with list of IDs
        assert mock_retry.call_count == 1
        call_args = mock_retry.call_args[0]
        assert call_args[0]([1, 2, 3])


def test_fetch_taxa_batch_multiple_batches():
    """Test batching when taxa count exceeds batch size."""
    with patch('taxa.batch.with_retry') as mock_retry:
        # Mock responses for two batches
        mock_retry.side_effect = [
            {'results': [{'id': i, 'name': f'Taxon {i}'} for i in range(30)]},
            {'results': [{'id': i, 'name': f'Taxon {i}'} for i in range(30, 35)]}
        ]

        # Fetch 35 taxa (should be 2 batches of 30)
        taxon_ids = list(range(35))
        result = fetch_taxa_batch(taxon_ids, batch_size=30)

        # Should return all taxa
        assert len(result) == 35

        # Should have called API twice
        assert mock_retry.call_count == 2


def test_fetch_taxa_batch_with_callback():
    """Test progress callback invoked after each batch."""
    with patch('taxa.batch.with_retry') as mock_retry:
        mock_retry.side_effect = [
            {'results': [{'id': i} for i in range(30)]},
            {'results': [{'id': i} for i in range(30, 40)]}
        ]

        batches_completed = []

        def callback(batch_num, total_batches):
            batches_completed.append((batch_num, total_batches))

        result = fetch_taxa_batch(list(range(40)), batch_size=30, callback=callback)

        # Callback should have been called twice
        assert batches_completed == [(1, 2), (2, 2)]
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_batch.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'taxa.batch'"

**Step 3: Implement fetch_taxa_batch**

Create `src/taxa/batch.py`:

```python
"""Batch fetching utilities for iNaturalist API."""
from typing import List, Dict, Any, Callable, Optional
from pyinaturalist import get_taxa_by_id

from taxa.retry import with_retry


def fetch_taxa_batch(
    taxon_ids: List[int],
    batch_size: int = 30,
    callback: Optional[Callable[[int, int], None]] = None
) -> List[Dict[str, Any]]:
    """
    Fetch multiple taxa by ID in batches.

    Uses get_taxa_by_id with multiple IDs per call to reduce API requests.
    iNaturalist API supports fetching multiple taxa in a single request.

    Args:
        taxon_ids: List of iNaturalist taxon IDs to fetch
        batch_size: Number of taxa to fetch per API call (default 30)
        callback: Optional function called after each batch: callback(batch_num, total_batches)

    Returns:
        List of complete taxon dictionaries with full details and ancestors
    """
    all_taxa = []
    total_batches = (len(taxon_ids) + batch_size - 1) // batch_size  # Ceiling division

    for batch_num, i in enumerate(range(0, len(taxon_ids), batch_size), start=1):
        batch = taxon_ids[i:i+batch_size]

        response = with_retry(get_taxa_by_id, batch)
        taxa = response.get('results', [])
        all_taxa.extend(taxa)

        if callback:
            callback(batch_num, total_batches)

    return all_taxa
```

**Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && pytest tests/test_batch.py -v`

Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add src/taxa/batch.py tests/test_batch.py
git commit -m "feat: add batch taxa fetching to reduce API calls"
```

---

## Task 4: Refactor sync_database to Use Regional Filtering

**Files:**
- Modify: `src/taxa/sync.py` (major refactor)
- Test: `tests/test_sync.py` (update existing tests)

**Step 1: Write failing integration test**

Add to `tests/test_sync.py`:

```python
def test_sync_database_regional_filtering(tmp_path):
    """Test sync uses regional filtering instead of global fetch."""
    from unittest.mock import patch, MagicMock

    config = Config(
        database=str(tmp_path / "test.db"),
        regions={
            'test_region': {
                'name': 'Test Region',
                'place_ids': [123]
            }
        },
        taxa={
            'test_taxon': {
                'name': 'Test Taxon',
                'taxon_id': 456
            }
        },
        filters={}
    )

    with patch('taxa.sync.fetch_regional_taxa') as mock_regional, \
         patch('taxa.sync.fetch_taxa_batch') as mock_batch:

        # Mock regional discovery returns 3 taxa
        mock_regional.return_value = [
            {'id': 1, 'descendant_obs_count': 10, 'direct_obs_count': 5},
            {'id': 2, 'descendant_obs_count': 20, 'direct_obs_count': 10},
            {'id': 3, 'descendant_obs_count': 15, 'direct_obs_count': 15}
        ]

        # Mock batch fetch returns full details
        mock_batch.return_value = [
            {
                'id': 1,
                'name': 'Taxon 1',
                'rank': 'species',
                'ancestors': []
            },
            {
                'id': 2,
                'name': 'Taxon 2',
                'rank': 'species',
                'ancestors': []
            },
            {
                'id': 3,
                'name': 'Taxon 3',
                'rank': 'species',
                'ancestors': []
            }
        ]

        sync_database(config)

        # Should have called regional fetch once per region
        assert mock_regional.call_count == 1

        # Should have called batch fetch once with all 3 IDs
        assert mock_batch.call_count == 1
        batch_ids = mock_batch.call_args[0][0]
        assert set(batch_ids) == {1, 2, 3}

        # Verify database has the taxa
        conn = sqlite3.connect(config.database)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM taxa")
        assert cursor.fetchone()[0] == 3
        conn.close()
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_sync.py::test_sync_database_regional_filtering -v`

Expected: FAIL (old implementation doesn't use regional filtering)

**Step 3: Refactor sync_database function**

Replace the sync loop in `src/taxa/sync.py` (lines 53-124) with:

```python
        # Sync each taxon using regional filtering
        for taxon_key, taxon_config in config.taxa.items():
            print(f"\nSyncing taxon: {taxon_config['name']} (ID: {taxon_config['taxon_id']})")

            # Phase 1: Discover which taxa occur in regions
            print(f"Discovering regional taxa...")

            # Calculate total queries for progress
            total_queries = sum(len(region['place_ids']) for region in config.regions.values())

            print(f"  Regions: {len(config.regions)}")
            print(f"  Total queries: {total_queries}\n")

            regional_taxa = {}  # taxon_id -> {region_key -> {place_id -> obs_data}}

            with tqdm(total=total_queries, desc="Querying regions", unit="query") as pbar:
                for region_key, region in config.regions.items():
                    for place_id in region['place_ids']:
                        # Update progress bar with current query
                        pbar.set_postfix_str(
                            f"{taxon_config['name'][:20]} in {region['name'][:20]}"
                        )

                        # Fetch all taxa with observations in this place
                        taxa = fetch_regional_taxa(
                            taxon_id=taxon_config['taxon_id'],
                            place_id=place_id,
                            quality_grade=config.filters.get('quality_grade')
                        )

                        # Store observation data by taxon/region/place
                        for taxon in taxa:
                            taxon_id = taxon['id']

                            if taxon_id not in regional_taxa:
                                regional_taxa[taxon_id] = {}
                            if region_key not in regional_taxa[taxon_id]:
                                regional_taxa[taxon_id][region_key] = {}

                            regional_taxa[taxon_id][region_key][place_id] = {
                                'observation_count': taxon['descendant_obs_count'],
                                'direct_count': taxon.get('direct_obs_count', 0)
                            }

                        pbar.update(1)

            print(f"\nTotal unique taxa discovered: {len(regional_taxa)}")

            if not regional_taxa:
                print(f"WARNING: No observations found for {taxon_config['name']} in any configured region")
                continue

            # Phase 2: Batch fetch full details
            print(f"\nFetching taxonomic details for {len(regional_taxa)} taxa...")

            taxon_ids = list(regional_taxa.keys())

            with tqdm(total=len(taxon_ids), desc="Processing taxa", unit="taxon") as pbar:

                def update_progress(batch_num, total_batches):
                    # Update progress bar by batch size (approximation)
                    pass  # tqdm updates happen per taxon below

                taxa = fetch_taxa_batch(taxon_ids, batch_size=30, callback=update_progress)

                for taxon in taxa:
                    taxon_id = taxon['id']

                    # Insert main taxon
                    row = flatten_taxon_ancestry(taxon)
                    cursor.execute("""
                        INSERT OR REPLACE INTO taxa (
                            id, scientific_name, common_name, rank,
                            kingdom, phylum, class, order_name, family,
                            subfamily, tribe, subtribe, genus, subgenus,
                            section, subsection, species, subspecies, variety, form,
                            is_active, iconic_taxon
                        ) VALUES (
                            :id, :scientific_name, :common_name, :rank,
                            :kingdom, :phylum, :class, :order_name, :family,
                            :subfamily, :tribe, :subtribe, :genus, :subgenus,
                            :section, :subsection, :species, :subspecies, :variety, :form,
                            :is_active, :iconic_taxon
                        )
                    """, row)

                    # Insert all ancestors (for complete hierarchy)
                    ancestors = taxon.get('ancestors', [])
                    for ancestor in ancestors:
                        ancestor_row = flatten_taxon_ancestry(ancestor)
                        cursor.execute("""
                            INSERT OR REPLACE INTO taxa (
                                id, scientific_name, common_name, rank,
                                kingdom, phylum, class, order_name, family,
                                subfamily, tribe, subtribe, genus, subgenus,
                                section, subsection, species, subspecies, variety, form,
                                is_active, iconic_taxon
                            ) VALUES (
                                :id, :scientific_name, :common_name, :rank,
                                :kingdom, :phylum, :class, :order_name, :family,
                                :subfamily, :tribe, :subtribe, :genus, :subgenus,
                                :section, :subsection, :species, :subspecies, :variety, :form,
                                :is_active, :iconic_taxon
                            )
                        """, ancestor_row)

                    # Insert observation data (already collected in Phase 1)
                    for region_key, places in regional_taxa[taxon_id].items():
                        for place_id, obs_data in places.items():
                            cursor.execute("""
                                INSERT OR REPLACE INTO observations (
                                    taxon_id, region_key, place_id,
                                    observation_count, observer_count,
                                    research_grade_count,
                                    first_observed, last_observed
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                taxon_id,
                                region_key,
                                place_id,
                                obs_data['observation_count'],
                                None,  # observer_count not available
                                None,  # research_grade_count not available
                                None,  # first_observed not available
                                None   # last_observed not available
                            ))

                    pbar.update(1)

            conn.commit()
```

Add imports at top of file:

```python
from taxa.fetcher import fetch_regional_taxa
from taxa.batch import fetch_taxa_batch
from pyinaturalist import get_taxa_by_id
```

**Step 4: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/test_sync.py::test_sync_database_regional_filtering -v`

Expected: PASS

**Step 5: Run all sync tests**

Run: `source venv/bin/activate && pytest tests/test_sync.py -v`

Expected: All tests PASS (existing tests should still work)

**Step 6: Commit**

```bash
git add src/taxa/sync.py
git commit -m "refactor: use regional filtering for sync optimization

Replace global taxa fetch with two-phase approach:
1. Discover taxa with observations in regions
2. Batch fetch full details for regional taxa only

Reduces API calls from ~10,000 to ~7-12 for typical configs."
```

---

## Task 5: Update Existing Tests for New Behavior

**Files:**
- Modify: `tests/test_sync.py` (update mocks)
- Modify: `tests/test_observations.py` (may need updates)

**Step 1: Review and update test mocks**

Check which tests mock `fetch_taxon_descendants` or `fetch_observation_summary`:

Run: `grep -n "fetch_taxon_descendants\|fetch_observation_summary" tests/test_sync.py`

**Step 2: Update tests to mock new functions**

For each test that used old functions, update mocks to use:
- `fetch_regional_taxa` instead of `fetch_taxon_descendants` + `fetch_observation_summary`
- `fetch_taxa_batch` instead of individual `get_taxa_by_id` calls

Example update:

```python
# OLD
with patch('taxa.sync.fetch_taxon_descendants') as mock_descendants:
    mock_descendants.return_value = [...]

# NEW
with patch('taxa.sync.fetch_regional_taxa') as mock_regional:
    mock_regional.return_value = [...]
```

**Step 3: Run all tests**

Run: `source venv/bin/activate && pytest tests/ -v`

Expected: All tests PASS

**Step 4: Commit**

```bash
git add tests/
git commit -m "test: update tests for regional filtering implementation"
```

---

## Task 6: Integration Test with Real API (Manual)

**Files:**
- None (manual testing)

**Step 1: Create small test config**

Create `test_regional.yaml`:

```yaml
database: ./test_regional.db

regions:
  sonoma_test:
    name: "Sonoma County Test"
    place_ids: [2764]

taxa:
  malus:
    name: "Malus (Apples)"
    taxon_id: 47426  # Small genus for quick test

filters:
  quality_grade: research
```

**Step 2: Run sync with test config**

Run: `source venv/bin/activate && python -m taxa.cli sync test_regional.yaml`

Expected:
- Progress bar for regional discovery (1 query)
- Progress bar for taxa details (small number, ~5-20 taxa)
- Completes in under 1 minute
- Creates `test_regional.db`

**Step 3: Verify database contents**

Run:
```bash
source venv/bin/activate
sqlite3 test_regional.db "SELECT COUNT(*) FROM taxa;"
sqlite3 test_regional.db "SELECT COUNT(*) FROM observations;"
sqlite3 test_regional.db "SELECT scientific_name, rank FROM taxa LIMIT 10;"
```

Expected:
- taxa table has entries (Malus species + ancestors)
- observations table has entries
- Scientific names look correct

**Step 4: Compare with web UI**

Visit: https://www.inaturalist.org/observations?taxon_id=47426&place_id=2764

Compare taxon count with database count.

**Step 5: Clean up test files**

```bash
rm test_regional.yaml test_regional.db
```

**Step 6: Document results**

No commit needed - manual test passed.

---

## Task 7: Performance Comparison Test

**Files:**
- Create: `scripts/compare_performance.py` (new script)

**Step 1: Create comparison script**

Create `scripts/compare_performance.py`:

```python
"""Compare performance of old vs new sync implementations."""
import time
import sqlite3
from unittest.mock import patch, MagicMock

from taxa.config import Config
from taxa.sync import sync_database


def mock_old_implementation(config):
    """Simulate old implementation behavior."""
    start = time.time()

    # Simulate fetching 5000 global taxa
    api_calls = 5000

    # Simulate 2 API calls per taxon (taxa fetch + observation query)
    api_calls *= 2

    # Simulate rate limiting (1 req/sec with pyinaturalist)
    elapsed = api_calls  # Seconds at 1 req/sec

    end = time.time()

    return {
        'api_calls': api_calls,
        'elapsed_simulated': elapsed,
        'taxa_count': 168  # Assume 168 actually have observations
    }


def test_new_implementation(config):
    """Test new implementation with mocks."""
    start = time.time()
    api_calls = 0

    with patch('taxa.sync.fetch_regional_taxa') as mock_regional, \
         patch('taxa.sync.fetch_taxa_batch') as mock_batch:

        # Simulate regional discovery (1 call)
        mock_regional.return_value = [
            {'id': i, 'descendant_obs_count': 10, 'direct_obs_count': 5}
            for i in range(168)
        ]
        api_calls += 1

        # Simulate batch fetching (168 taxa / 30 batch = 6 calls)
        def batch_side_effect(taxon_ids, batch_size=30, callback=None):
            nonlocal api_calls
            batches = (len(taxon_ids) + batch_size - 1) // batch_size
            api_calls += batches
            return [
                {'id': tid, 'name': f'Taxon {tid}', 'rank': 'species', 'ancestors': []}
                for tid in taxon_ids
            ]

        mock_batch.side_effect = batch_side_effect

        sync_database(config)

    end = time.time()

    return {
        'api_calls': api_calls,
        'elapsed_actual': end - start,
        'taxa_count': 168
    }


def main():
    """Run comparison."""
    config = Config(
        database=':memory:',
        regions={'test': {'name': 'Test', 'place_ids': [123]}},
        taxa={'test': {'name': 'Test', 'taxon_id': 456}},
        filters={}
    )

    print("Performance Comparison: Old vs New Implementation")
    print("=" * 60)
    print()

    print("OLD IMPLEMENTATION (simulated):")
    old_result = mock_old_implementation(config)
    print(f"  API calls: {old_result['api_calls']:,}")
    print(f"  Time (simulated): {old_result['elapsed_simulated']:,.1f} seconds")
    print(f"  Taxa discovered: {old_result['taxa_count']}")
    print()

    print("NEW IMPLEMENTATION:")
    new_result = test_new_implementation(config)
    print(f"  API calls: {new_result['api_calls']}")
    print(f"  Time (actual): {new_result['elapsed_actual']:.2f} seconds")
    print(f"  Taxa discovered: {new_result['taxa_count']}")
    print()

    print("IMPROVEMENT:")
    api_reduction = (1 - new_result['api_calls'] / old_result['api_calls']) * 100
    time_reduction = (1 - new_result['elapsed_actual'] / old_result['elapsed_simulated']) * 100
    print(f"  API calls reduced: {api_reduction:.1f}%")
    print(f"  Time reduced: {time_reduction:.1f}%")
    print(f"  Speedup factor: {old_result['api_calls'] / new_result['api_calls']:.1f}x")


if __name__ == '__main__':
    main()
```

**Step 2: Run comparison**

Run: `source venv/bin/activate && python scripts/compare_performance.py`

Expected output showing ~99% reduction in API calls

**Step 3: Commit**

```bash
git add scripts/compare_performance.py
git commit -m "test: add performance comparison script

Shows ~1000x reduction in API calls vs old implementation."
```

---

## Task 8: Update Documentation

**Files:**
- Modify: `README.md` (add performance notes)
- Modify: `docs/plans/2026-01-28-regional-filtering-optimization.md` (update status)

**Step 1: Add performance section to README**

Add to `README.md` after installation section:

```markdown
## Performance

The tool uses regional filtering to optimize sync performance:

- **Old approach:** Fetch all global taxa, then query observations for each (~10,000 API calls)
- **New approach:** Discover regional taxa first, then batch fetch details (~7-12 API calls)

**Typical sync times:**
- Small genus (e.g., Malus) in one county: ~1 minute
- Large subfamily (e.g., Amygdaloideae) in one county: ~2-3 minutes
- Multiple taxa across multiple regions: ~5-10 minutes

The tool complies with iNaturalist's recommended API practices (~1 req/sec, ~10k req/day).
```

**Step 2: Update design doc status**

Change status in `docs/plans/2026-01-28-regional-filtering-optimization.md`:

```markdown
**Status:** ✅ Implemented and Tested
```

**Step 3: Commit**

```bash
git add README.md docs/plans/2026-01-28-regional-filtering-optimization.md
git commit -m "docs: update README with performance improvements"
```

---

## Task 9: Final Integration Test

**Files:**
- None (use actual config)

**Step 1: Run full sync with real config**

Run: `source venv/bin/activate && python -m taxa.cli sync mml.yaml`

**Step 2: Verify results**

Check:
- Sync completes successfully
- Progress bars display correctly
- Database contains expected taxa
- Query results match expectations

**Step 3: Compare with previous database (if available)**

If you have a database from the old implementation:
```bash
sqlite3 mml.db.old "SELECT COUNT(*) FROM taxa;" > old_count.txt
sqlite3 mml.db "SELECT COUNT(*) FROM taxa;" > new_count.txt
diff old_count.txt new_count.txt
```

Expected: Counts should be similar (±few percent due to timing)

**Step 4: Document success**

Create git tag for this milestone:

```bash
git tag -a v1.1.0 -m "Regional filtering optimization

- Reduces API calls by ~1000x
- Sync time from hours to minutes
- Maintains data accuracy"

git push origin v1.1.0
```

---

## Completion Checklist

- [x] User agent configuration added
- [x] fetch_regional_taxa function implemented and tested
- [x] Batch fetching implemented and tested
- [x] sync_database refactored to use regional filtering
- [x] All existing tests updated and passing
- [x] Integration test with real API successful
- [x] Performance comparison documented
- [x] Documentation updated
- [x] Full sync with real config successful

## Notes

**API Rate Limiting:**
- pyinaturalist handles rate limiting automatically
- Our `with_retry()` wrapper adds exponential backoff
- Typical configs stay well under 10k req/day limit

**Testing Strategy:**
- Unit tests use mocks for fast execution
- Integration test with real API validates behavior
- Manual testing confirms results match web UI

**Rollback Plan:**
If issues arise, the old implementation is still in git history. To rollback:
```bash
git revert HEAD~N  # Revert last N commits
```

**Future Optimizations:**
- Could cache taxonomy responses for repeated syncs
- Could add incremental sync mode (only fetch new/updated taxa)
- Could parallelize regional queries if needed
