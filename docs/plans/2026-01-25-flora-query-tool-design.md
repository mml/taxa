# Flora Query Tool Design

**Date:** 2026-01-25
**Status:** Design Complete - Ready for Implementation

## Overview

A Python CLI tool that fetches taxonomic hierarchy and occurrence data from iNaturalist and builds a SQLite database optimized for exploratory SQL queries about local flora. Primary use case: answering questions like "what tribes of Amygdaloideae occur in these 3 counties?"

## Goals

- Query regional flora using natural SQL (not JSON extractions or tree walks)
- Support all taxonomic ranks (including tribe, subfamily, etc.)
- Configure regions and taxa of interest via simple YAML
- Efficient API usage with aggregated endpoints (no individual observations)
- Fast offline queries once data is synced

## Architecture

### High-Level Components

1. **Config reader** - Parses YAML, validates place/taxon IDs
2. **Data fetcher** - Uses `pyinaturalist` library to fetch taxa + observations
3. **DB builder** - Creates SQLite schema and loads data
4. **CLI interface** - Subcommands for sync, query, and ID lookup helpers

### Data Flow
```
config.yaml → pyinaturalist API → SQLite DB → user SQL queries
```

### Tech Stack
- Python 3.10+
- `pyinaturalist` - iNaturalist API wrapper
- `pyyaml` - config parsing
- `sqlite3` (stdlib) - database
- `click` or `argparse` - CLI
- `requests` (via pyinaturalist)

## Development Environment Setup

**Virtual Environment:** All development uses a Python virtual environment to ensure consistent dependencies.

**Setup (one-time):**
```bash
python3 -m venv venv
venv/bin/pip install -e '.[dev]'
```

**Usage (all commands):**
- Run tests: `venv/bin/pytest tests/ -v`
- Run CLI: `venv/bin/python -m taxa.cli`
- Run scripts: `venv/bin/python scripts/poc_performance.py`
- Install new deps: `venv/bin/pip install <package>`

**Important:** Always use explicit `venv/bin/` paths. Never activate the venv - just reference the binaries directly. This ensures all agents and scripts use the same isolated environment without environment variable dependencies.

## Config File Format

**config.yaml:**
```yaml
database: ./flora.db

regions:
  sfba:
    name: "San Francisco Bay Area"
    place_ids: [5245, 5678]
  north_coast:
    name: "North Coast"
    place_ids: [14, 23, 1234]

taxa:
  rosaceae:
    name: "Rosaceae"
    taxon_id: 47125
    notes: "Roses, stone fruits, etc."
  oaks:
    name: "California Oaks"
    taxon_id: 47851

filters:
  quality_grade: research  # research, needs_id, casual, or omit
```

**Design notes:**
- Regions and taxa keyed by short identifiers for easy query filtering
- place_ids are iNaturalist place IDs (use helper command to find)
- taxon_id can be any rank (family, genus, etc.) - tool fetches descendants
- Tool queries all region + taxon combinations

## Database Schema

### Core Tables

```sql
-- Wide table with all possible taxonomic ranks
CREATE TABLE taxa (
  id INTEGER PRIMARY KEY,           -- iNat taxon ID
  scientific_name TEXT NOT NULL,
  common_name TEXT,
  rank TEXT NOT NULL,               -- taxon's own rank

  -- All possible ranks (NULL if not applicable)
  kingdom TEXT,
  phylum TEXT,
  class TEXT,
  order_name TEXT,                  -- 'order' is SQL keyword
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
  iconic_taxon TEXT                 -- Plantae, Fungi, etc.
);

-- Aggregated observation data
CREATE TABLE observations (
  taxon_id INTEGER NOT NULL,
  region_key TEXT NOT NULL,         -- e.g., 'sfba'
  place_id INTEGER NOT NULL,        -- iNat place ID

  observation_count INTEGER,
  observer_count INTEGER,
  research_grade_count INTEGER,

  first_observed DATE,
  last_observed DATE,

  PRIMARY KEY (taxon_id, place_id),
  FOREIGN KEY (taxon_id) REFERENCES taxa(id)
);

-- Region metadata from config
CREATE TABLE regions (
  key TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  place_ids TEXT NOT NULL           -- JSON array
);

-- Sync metadata
CREATE TABLE sync_info (
  key TEXT PRIMARY KEY,
  value TEXT
);
```

### Indexes
```sql
CREATE INDEX idx_taxa_family ON taxa(family);
CREATE INDEX idx_taxa_genus ON taxa(genus);
CREATE INDEX idx_taxa_subfamily ON taxa(subfamily);
CREATE INDEX idx_taxa_tribe ON taxa(tribe);
CREATE INDEX idx_obs_region ON observations(region_key);
```

## Data Fetching Strategy

### Per Region + Taxon Combination

1. **Fetch taxonomic tree:**
   - `get_taxa_by_id()` for configured taxon
   - `get_taxa()` with `taxon_id` to get all descendants
   - Extract full ancestor chain from API responses
   - Flatten into wide table rows in `taxa` table

2. **Fetch aggregated observations:**
   - `get_observation_species_counts(taxon_id, place_id, quality_grade)`
     - Returns taxa with observation counts
   - `get_observation_histogram(taxon_id, place_id, date_field='observed')`
     - Returns temporal distribution → extract min/max dates
   - Check if observer counts included, otherwise separate call
   - Merge into `observations` table

3. **Deduplication:**
   - Primary key: `(taxon_id, place_id)`
   - Multiple regions with same place_id → one row

### Rate Limiting
- pyinaturalist handles API rate limiting (100 req/min)
- Show progress for large queries

### Early Validation Strategy

**Critical:** Test performance before building full tool.

**Proof-of-concept script:**
1. Fetch one large taxon + region (e.g., Plantae in one CA county)
2. Track metrics during fetch:
   - Taxa processed vs. total descendants
   - API calls made and rate
   - Time per taxon/call
3. Configurable timeout (default 5 min)
4. On timeout: print progress report with extrapolated estimates

**Example output:**
```
Progress Report:
  Elapsed: 5m 23s
  Taxa fetched: 1,247 / ~45,000 (estimated)
  API calls made: 342
  Rate: ~1.06 calls/second

Extrapolated estimates:
  Total time at current rate: ~3.2 hours
  Bottleneck: Taxa hierarchy fetching (78%)
```

**Decision point:** If too slow, consider:
- Fetch at higher taxonomic levels only
- Use bulk taxonomy export + aggregate observations differently
- Batch requests differently
- Accept long initial sync, optimize re-sync

**Implementation order:**
1. Set up project structure
2. **Build proof-of-concept fetcher** (stress test)
3. **Evaluate performance** - revise approach if needed
4. Build CLI/config/schema (only after validation)

## CLI Commands

```bash
# Sync data from API to database
taxa sync [config.yaml]
  --timeout SECONDS        # for proof-of-concept mode
  --dry-run               # estimate only

# Query helpers
taxa query "SELECT ..."    # runs query against configured DB
taxa query                 # interactive sqlite3 shell (no args)

# ID lookup helpers
taxa search places QUERY   # find place IDs
taxa search taxa QUERY     # find taxon IDs

# Info
taxa info                  # DB stats, last sync time
```

**Example output during sync:**
```
Loading config from config.yaml...
  Regions: sfba (2 places), north_coast (3 places)
  Taxa: rosaceae, oaks

Validating place IDs... ✓
Validating taxon IDs... ✓

Fetching taxa hierarchy for rosaceae in sfba...
  Progress: 1247/~45000 taxa (2.8%) | 5m 23s elapsed
  Estimated completion: ~3.2 hours
  [Press Ctrl+C to abort]
```

## Error Handling

### Config Validation
- Invalid YAML → parse error with line number
- Missing fields → list what's missing
- Invalid place/taxon IDs → validate before sync, show failures
- Duplicate keys → error with conflicting keys

### API Failures
- Network errors → retry with exponential backoff (3 attempts)
- Rate limit hit → wait and retry (shouldn't happen with pyinaturalist)
- Invalid IDs → fail in validation phase
- Partial results → log warning, continue

### Sync Interruption (Ctrl+C)
- Catch signal gracefully
- Build DB to temporary file: `{database}.new`
- Use transaction, rollback on interrupt
- Only replace old DB if sync succeeds

### Database Replacement Strategy
```python
# Build to temp file
temp_db = f"{config.database}.new"
build_database(temp_db)

# Back up old DB
if os.path.exists(config.database):
    os.rename(config.database, f"{config.database}~")

# Atomic replace
os.rename(temp_db, config.database)
```

**Result:**
- `flora.db` - current database
- `flora.db~` - previous version backup

### Data Edge Cases
- Taxon with no observations → skip `observations` insert, keep in `taxa`
- Incomplete ancestry → store what we have, NULLs for missing ranks
- Zero descendants → still fetch observation data

### User-Friendly Messages
```
ERROR: Invalid taxon ID '99999999' for taxa.rosaceae
  Run: taxa search taxa "Rosaceae" to find the correct ID
```

## Testing Strategy

### Proof-of-Concept Validation
Test progressively larger queries:
1. Small: single genus in one county (~hundreds of taxa)
2. Medium: family in multi-county region (~thousands)
3. Large: order/class in California (~tens of thousands)

Measure and report scaling behavior.

### Unit Tests
- Config parsing (valid/invalid YAML)
- Schema creation
- Taxa flattening (ancestry → wide table)
- Query helpers

### Integration Tests
- Mock pyinaturalist responses
- Test full sync flow with fixture data
- Verify database schema and data integrity
- Test atomic DB replacement

### Manual Testing
- Run with real config (North Coast flora)
- Verify query results
- Test interrupt behavior
- Validate all CLI commands

## Example Queries

**"What tribes of Amygdaloideae occur in these 3 counties?"**
```sql
SELECT DISTINCT tribe
FROM taxa t
JOIN observations o ON o.taxon_id = t.id
WHERE subfamily = 'Amygdaloideae'
  AND tribe IS NOT NULL
  AND o.region_key IN ('mendocino', 'humboldt', 'trinity');
```

**"What Quercus species are in the Bay Area with >50 observations?"**
```sql
SELECT scientific_name, observation_count
FROM taxa t
JOIN observations o ON o.taxon_id = t.id
WHERE genus = 'Quercus'
  AND rank = 'species'
  AND region_key = 'sfba'
  AND observation_count > 50
ORDER BY observation_count DESC;
```

## Implementation Phases

### Phase 1: Proof-of-Concept (Critical Path)
- Basic pyinaturalist integration
- Fetch one large taxon + region
- Track and report metrics
- Timeout with progress estimation
- **Decision point: proceed or revise approach**

### Phase 2: Core Functionality
- Config YAML parsing and validation
- Schema creation
- Data fetching for multiple region/taxa combos
- Database building with atomic replacement

### Phase 3: CLI Polish
- All subcommands (sync, query, search, info)
- Progress reporting
- Error handling
- Helper commands for ID lookup

### Phase 4: Testing & Documentation
- Unit and integration tests
- User guide / README
- Example configs and queries

## Open Questions

None - design complete and validated with user.

## References

- [iNaturalist API Documentation](https://api.inaturalist.org/v1/docs/)
- [pyinaturalist GitHub](https://github.com/pyinat/pyinaturalist)
- [pyinaturalist Documentation](https://pyinaturalist.readthedocs.io/)
