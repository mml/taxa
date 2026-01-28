# Regional Filtering Optimization Design

**Date:** 2026-01-28
**Status:** ✅ Implemented and Tested

## Overview

Optimize sync performance by discovering which taxa occur in configured regions FIRST, then only fetching details for regional taxa. This eliminates thousands of wasted API calls for taxa that don't occur in the target regions.

## Problem Statement

Current implementation fetches ALL descendants of a configured taxon globally (e.g., ~5000 Amygdaloideae taxa worldwide), then queries observation counts for each in the target region. Most taxa have zero observations in the region, resulting in ~10,000 wasted API calls.

**Current performance:**
- Amygdaloideae in Sonoma County: ~10,000 API calls, ~2 hours at rate limit
- Sync rate: 1-2 taxa/second

**Root cause:**
- Fetching global taxonomy first is inefficient
- Most API calls return zero observations

## Solution

Use iNaturalist's `/v1/observations/taxonomy` endpoint to discover which taxa actually occur in target regions FIRST, then fetch full details only for those taxa.

**Flow change:**
```
OLD: Fetch 5000 global taxa → Query observations for each → Most return zero
NEW: Query regional taxa → Returns ~168 taxa with counts → Fetch details for each
```

**Expected speedup:**
- From ~10,000 API calls to ~7-12 calls (~1000x reduction)
- From ~2 hours to ~2-3 minutes
- Sync rate: ~1-2 taxa/second → complete in minutes regardless of global taxon count

## API Endpoint Details

### get_observation_taxonomy

**Endpoint:** `/v1/observations/taxonomy` (via pyinaturalist)

**Function:** `pyinaturalist.get_observation_taxonomy(taxon_id, place_id, quality_grade, ...)`

**Purpose:** Returns all taxa with observations in a region at ANY rank (not just leaf taxa)

**Key features:**
- Accepts standard filters: `taxon_id`, `place_id`, `quality_grade`
- Returns flat list ordered taxonomically
- Each result includes:
  - `id`, `name`, `rank`, `rank_level`
  - `direct_obs_count` - observations identified to this specific rank
  - `descendant_obs_count` - total including all descendants
  - `parent_id` - for building hierarchy
  - `is_active`, `iconic_taxon_name`
- Supports pagination via `page`/`per_page`
- Handles all ranks: species, genus, tribe, subfamily, etc.

**Status:** Undocumented but officially supported by pyinaturalist (noted in docstring)

### get_taxa_by_id

**Batch capability:** Accepts `Union[int, Iterable[int]]` - can fetch multiple taxa in one call

**Usage:**
```python
# Single taxon
response = get_taxa_by_id(123)

# Batch of taxa (up to 30 recommended)
response = get_taxa_by_id([123, 456, 789])
```

Returns full taxon details including:
- Complete ancestry chain
- Common names
- All taxonomic rank fields
- `is_active`, `iconic_taxon` flags

## Implementation Design

### High-Level Flow

```python
# Setup
set_user_agent()

for taxon_key, taxon_config in config.taxa.items():

    # Phase 1: Regional Discovery
    regional_taxa = discover_regional_taxa(taxon_config, config.regions)
    # Returns: {taxon_id -> {region_key -> {place_id -> obs_data}}}

    # Phase 2: Batch Fetch Details
    fetch_and_insert_taxa_batch(regional_taxa, cursor)
    # Fetches taxa in batches of 30, inserts with ancestors

conn.commit()
```

### Phase 1: Regional Discovery

```python
def discover_regional_taxa(taxon_config, regions):
    """
    Query all region/place combinations to find which taxa occur.

    Returns:
        {taxon_id -> {region_key -> {place_id -> obs_data}}}
    """
    regional_taxa = {}

    # Calculate total queries for progress bar
    total_queries = sum(
        len(region['place_ids']) for region in regions.values()
    )

    with tqdm(total=total_queries, desc="Querying regions", unit="query") as pbar:
        for region_key, region in regions.items():
            for place_id in region['place_ids']:
                # Show what we're currently querying
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
                        'direct_count': taxon['direct_obs_count']
                    }

                pbar.update(1)

    return regional_taxa
```

### fetch_regional_taxa Helper

```python
def fetch_regional_taxa(
    taxon_id: int,
    place_id: int,
    quality_grade: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch all taxa with observations in a region at any rank.

    Handles pagination automatically.
    Returns taxa with observation counts populated.
    """
    all_taxa = []
    page = 1
    per_page = 200  # Maximum supported

    while True:
        response = with_retry(
            get_observation_taxonomy,
            taxon_id=taxon_id,
            place_id=place_id,
            quality_grade=quality_grade,
            per_page=per_page,
            page=page
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

### Phase 2: Batch Fetch and Insert

```python
def fetch_and_insert_taxa_batch(regional_taxa, cursor):
    """
    Fetch full details for discovered taxa in batches.
    Insert taxa + ancestors + observations.
    """
    taxon_ids = list(regional_taxa.keys())
    batch_size = 30  # Conservative batch size

    print(f"\nFetching taxonomic details for {len(taxon_ids)} taxa...")

    with tqdm(total=len(taxon_ids), desc="Processing taxa", unit="taxon") as pbar:
        for i in range(0, len(taxon_ids), batch_size):
            batch = taxon_ids[i:i+batch_size]

            # Fetch batch of taxa with full details
            response = with_retry(get_taxa_by_id, batch)
            taxa = response['results']

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
                    cursor.execute("INSERT OR REPLACE INTO taxa ...", ancestor_row)

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
```

### User Agent Configuration

At application startup:

```python
# In cli.py or sync.py module level
import pyinaturalist

# Set user agent to identify our application
pyinaturalist.user_agent = "taxa-flora-query-tool/1.0 (github.com/mml/taxa)"
```

This complies with iNaturalist's recommended practice to identify applications.

## Progress Reporting

### Phase 1: Discovery

```
Discovering regional taxa...
  Regions: 2
  Taxa: 3
  Total queries: 12

Querying regions: 100%|████████████| 12/12 [0:15<00:00, 1.3 query/s] Rosaceae in Mendocino

Total unique taxa discovered: 347
```

Key features:
- Shows total queries upfront (calculable from config)
- Progress bar with current query description via `set_postfix_str()`
- Updates in place (doesn't scroll)

### Phase 2: Detail Fetching

```
Fetching taxonomic details for 347 taxa...
Processing taxa: 100%|████████████| 347/347 [0:45<00:00, 7.7 taxon/s]
```

Key features:
- Known total from Phase 1
- Standard tqdm progress bar
- Shows rate in taxa/second

### Complete Output Example

```
Loading config from mml.yaml...
  Regions: sonoma_county
  Taxa: amygdaloideae

Discovering regional taxa...
  Regions: 1
  Taxa: 1
  Total queries: 1

Querying regions: 100%|████████████| 1/1 [0:02<00:00, 0.5 query/s] Amygdaloideae in Sonoma

Total unique taxa discovered: 168

Fetching taxonomic details for 168 taxa...
Processing taxa: 100%|████████████| 168/168 [0:30<00:00, 5.6 taxon/s]

Sync complete!
```

## Performance Analysis

### API Call Reduction

**Example: Amygdaloideae in Sonoma County**

| Phase | Old Approach | New Approach |
|-------|-------------|--------------|
| Discovery | N/A | 1 call |
| Taxon details | 5000 calls (all global descendants) | 6 calls (168 taxa ÷ 30 batch) |
| Observations | 5000 calls (per taxon) | 0 (included in discovery) |
| **Total** | **~10,000 calls** | **~7 calls** |
| **Time** | **~2 hours** | **~2 minutes** |

### Multi-Region/Taxa Configs

**Example: 3 taxa × 2 regions (5 places each)**

| Component | Calls |
|-----------|-------|
| Phase 1 discovery | 3 × 2 × 5 = 30 calls |
| Phase 2 details | ~500 taxa ÷ 30 = ~17 calls |
| **Total** | **~47 calls** |

Still well under iNaturalist's ~10k/day limit and ~1 req/sec recommendation.

## API Best Practices Compliance

### Rate Limiting

iNaturalist recommends ~1 request/second and ~10k requests/day.

**Compliance:**
- Typical sync: 7-50 API calls (well under daily limit)
- pyinaturalist handles rate limiting automatically
- `with_retry()` wrapper adds exponential backoff
- Natural pacing from processing time keeps us near 1 req/sec

### User Agent

**Requirement:** "Please consider using a custom User Agent to identify your application"

**Implementation:**
```python
pyinaturalist.user_agent = "taxa-flora-query-tool/1.0 (github.com/mml/taxa)"
```

Set at application startup, applies to all requests.

### Batch Fetching

**Recommendation:** "Fetch multiple records by ID in single requests instead of individually"

**Implementation:** Using `get_taxa_by_id([id1, id2, ...])` with batches of 30 taxa.

### Pagination Best Practices

**Recommendation:** "Use highest supported per_page values (up to 200)"

**Implementation:** All pagination uses `per_page=200`

## Data Handling

### Observation Count Fields

The `taxonomy` endpoint returns:
- `direct_obs_count` - observations identified specifically to this taxon
- `descendant_obs_count` - total including descendants

**Decision:** Store `descendant_obs_count` in `observation_count` field (matches current behavior).

We can add `direct_obs_count` column later if needed, but it's not in current schema.

### Ancestor Handling

Intermediate ranks (e.g., Maleae tribe) are included via the ancestry chain:
- Each fetched taxon includes `ancestors` array
- All ancestors inserted into taxa table
- Root taxon (e.g., Amygdaloideae) included via child taxa ancestry
- No explicit root fetch needed

**Result:** Complete taxonomy for queries like `WHERE tribe = 'Maleae'`

### Deduplication

Multiple regions/places may have overlapping taxa:
- `regional_taxa` dict prevents duplicate detail fetches
- `INSERT OR REPLACE INTO taxa` handles duplicate inserts
- Primary key `(taxon_id, place_id)` prevents duplicate observations

## Error Handling

### Empty Results

**Scenario:** Configured taxon has no observations in any region.

**Handling:**
- Phase 1 returns empty results
- Warning: `"No observations found for {taxon_name} in any configured region"`
- Skip Phase 2 for that taxon
- No rows inserted for that taxon

### API Failures

**Phase 1 failure:**
- If `get_observation_taxonomy` fails, entire sync fails
- Can't proceed without knowing which taxa exist
- `with_retry()` handles transient failures (3 attempts with exponential backoff)

**Phase 2 failure:**
- If batch `get_taxa_by_id` fails, log error and skip that batch
- Continue with remaining batches
- Report failures at end: `"Failed to fetch N taxa: [ids]"`

### Pagination Edge Cases

- Empty page: loop breaks correctly
- Exact multiple of `per_page`: one extra call returns empty, then breaks
- Very large result sets: pagination continues until empty page

### Missing Data

**Scenario:** Taxon has incomplete ancestry chain.

**Handling:** `flatten_taxon_ancestry()` stores NULL for missing ranks (existing behavior).

## Testing Strategy

### New Unit Tests

**tests/test_fetcher.py:**
```python
def test_fetch_regional_taxa_single_page():
    """Test fetching regional taxa with results fitting in one page."""

def test_fetch_regional_taxa_pagination():
    """Test pagination when results span multiple pages."""

def test_fetch_regional_taxa_empty():
    """Test handling empty results (no observations in region)."""
```

**tests/test_sync.py:**
```python
def test_sync_regional_filtering():
    """Test end-to-end sync with regional filtering."""
    # Mock get_observation_taxonomy + get_taxa_by_id
    # Verify correct taxa inserted with ancestors
    # Verify observation counts stored correctly

def test_sync_multiple_regions_deduplication():
    """Test that overlapping taxa across regions don't cause duplicates."""
    # Mock same taxa appearing in multiple regions
    # Verify get_taxa_by_id called once per unique taxon

def test_sync_batch_fetching():
    """Test that taxa are fetched in batches."""
    # Mock 100 regional taxa
    # Verify get_taxa_by_id called 4 times (100 ÷ 30 = 3.33 → 4 batches)
```

### Integration Testing

**Manual test with real API:**
1. Small taxon (e.g., single genus) in one county
2. Verify correct taxa count vs iNaturalist web UI
3. Verify observation counts match
4. Compare database content with old implementation (should be identical)

### Performance Validation

Run both old and new implementations on same config:

**Metrics to compare:**
- Total API calls made
- Time to completion
- Resulting database content (should be identical)
- Memory usage

**Expected results:**
- New: ~100x fewer API calls
- New: ~10-60x faster completion
- Identical database content

## Implementation Phases

### Phase 1: Core Optimization
1. Add `fetch_regional_taxa()` to `fetcher.py`
2. Refactor `sync_database()` to two-phase approach
3. Implement batch fetching in Phase 2
4. Update progress reporting
5. Add user agent configuration

### Phase 2: Polish
1. Error handling improvements
2. Warning messages for empty results
3. Failure tracking and reporting

### Phase 3: Testing
1. Unit tests for new functions
2. Integration tests for full sync
3. Performance comparison with old implementation

### Phase 4: Documentation
1. Update README with performance improvements
2. Update CLAUDE.md if needed
3. Add migration notes (if any breaking changes)

## Migration Notes

### Breaking Changes

None - this is a pure optimization. Database schema and output format remain identical.

### Backwards Compatibility

Old and new implementations produce identical databases. Users can switch between versions without data migration.

### Config Changes

None required. Existing configs work unchanged.

## Open Questions

None - design complete and validated.

## References

- [iNaturalist API Recommended Practices](https://www.inaturalist.org/pages/api+recommended+practices)
- [pyinaturalist Documentation](https://pyinaturalist.readthedocs.io/)
- [get_observation_taxonomy Documentation](https://pyinaturalist.readthedocs.io/en/stable/modules/pyinaturalist.v1.observations.html)
- [Original Design Document](./2026-01-25-flora-query-tool-design.md)
