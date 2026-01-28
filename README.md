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

## Performance

The tool uses regional filtering to optimize sync performance:

- **Old approach:** Fetch all global taxa, then query observations for each (~10,000 API calls)
- **New approach:** Discover regional taxa first, then batch fetch details (~7-12 API calls)

**Typical sync times:**
- Small genus (e.g., Malus) in one county: ~1 minute
- Large subfamily (e.g., Amygdaloideae) in one county: ~2-3 minutes
- Multiple taxa across multiple regions: ~5-10 minutes

The tool complies with iNaturalist's recommended API practices (~1 req/sec, ~10k req/day).

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

See [docs/plans/2026-01-25-flora-query-tool-implementation.md](docs/plans/2026-01-25-flora-query-tool-implementation.md) for complete design documentation.

## License

MIT
