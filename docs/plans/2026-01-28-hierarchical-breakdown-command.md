# Hierarchical Breakdown Command Design

**Date:** 2026-01-28
**Status:** Design
**Author:** Matt + Claude

## Overview

Add a `taxa breakdown` command that generates and executes hierarchical taxonomic breakdown queries with automatic subtotals. This allows users to explore taxonomic hierarchies without writing complex UNION queries manually.

## Motivation

Users frequently want to break down a taxon (e.g., family) into its constituent lower-level groups (e.g., subfamilies, tribes, genera) with observation and species counts at each level. Currently this requires writing complex UNION queries like:

```sql
SELECT subfamily, NULL as tribe, SUM(observations.observation_count) c, COUNT(DISTINCT scientific_name) num_taxa
FROM taxa
JOIN observations ON taxon_id = taxa.id
WHERE family='Asteraceae' AND subfamily IS NOT NULL
GROUP BY subfamily

UNION ALL

SELECT subfamily, tribe, SUM(observations.observation_count) c, COUNT(DISTINCT scientific_name) num_taxa
FROM taxa
JOIN observations ON taxon_id = taxa.id
WHERE family='Asteraceae' AND subfamily IS NOT NULL AND tribe IS NOT NULL
GROUP BY subfamily, tribe

ORDER BY subfamily, tribe NULLS FIRST, c DESC;
```

The new command will generate and execute these queries automatically.

## Command Interface

### Basic Syntax

```bash
taxa breakdown TAXON_NAME [--levels LEVEL1,LEVEL2,...] [--region REGION_KEY] [--database DB_PATH]
```

### Examples

```bash
# Break down Asteraceae to next level (subfamily)
taxa breakdown Asteraceae

# Show subfamily + tribe hierarchy
taxa breakdown Asteraceae --levels subfamily,tribe

# Filter to specific region
taxa breakdown Rosaceae --region north_coast --levels genus

# Skip intermediate levels
taxa breakdown Asteraceae --levels genus  # Skip subfamily, tribe, subtribe

# Specify database
taxa breakdown "Amygdaloideae" --database mml.db --levels tribe
```

### Design Decisions

1. **Interface style:** Structured flags (explicit, scriptable, self-documenting)
2. **Subtotals:** Always included (every breakdown shows parent-level totals)
3. **Taxon identification:** Auto-detect rank from value (simple, minimal typing)
4. **Default behavior:** Show next 1 level only when --levels not specified
5. **Region filtering:** Optional --region flag (consistent with other queries)
6. **Level specification:** Allow skipping intermediate ranks (flexible)

## Implementation Details

### Shared Taxonomy Module

Create `src/taxa/taxonomy.py` to define the taxonomic hierarchy once:

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

def get_next_ranks(current_rank, count=1):
    """Get the next N ranks in hierarchy after current_rank."""
    idx = TAXONOMIC_RANKS.index(current_rank)
    return TAXONOMIC_RANKS[idx+1:idx+1+count]

def validate_rank_sequence(base_rank, requested_ranks):
    """Validate that requested ranks are all below base_rank."""
    base_idx = TAXONOMIC_RANKS.index(base_rank)
    for rank in requested_ranks:
        if TAXONOMIC_RANKS.index(rank) <= base_idx:
            raise ValueError(f"Cannot break down to '{rank}' - it's not below '{base_rank}'")
    return True

def sort_ranks(ranks):
    """Sort ranks by hierarchical order."""
    return sorted(ranks, key=lambda r: TAXONOMIC_RANKS.index(r))
```

### Update schema.py

Refactor `schema.py` to use `TAXONOMIC_RANKS` instead of hardcoding column names.

### Auto-detection Logic

```python
def find_taxon_rank(db, taxon_name):
    """Query each rank column to find where this taxon appears.

    Returns:
        str: The rank where taxon was found

    Raises:
        ValueError: If taxon not found or found at multiple ranks
    """
    found_ranks = []
    for rank in TAXONOMIC_RANKS:
        result = db.execute(
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

### Query Generation

For each requested level, generate a SELECT in the UNION:

```python
def generate_breakdown_query(base_taxon, base_rank, levels, region_key=None):
    """Generate UNION query for hierarchical breakdown.

    Args:
        base_taxon: Name of taxon to break down (e.g., "Asteraceae")
        base_rank: Rank of base taxon (e.g., "family")
        levels: List of ranks to break down to (e.g., ["subfamily", "tribe"])
        region_key: Optional region filter

    Returns:
        str: SQL query with UNION ALL structure
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

### Output Format

Tab-separated columns matching existing `taxa query` format:

```
subfamily       tribe           observation_count       species_count
Asteroideae     NULL            45234                   892
Asteroideae     Anthemideae     12456                   234
Asteroideae     Astereae        8901                    156
```

**Column meanings:**
- Hierarchical columns: Show the taxonomic level names (NULL = subtotal for parent)
- `observation_count`: Sum of all observations for taxa at this level
- `species_count`: Count of distinct species-level taxa

**Sorting:**
1. First level (e.g., subfamily)
2. Second level (e.g., tribe), NULLs first within each group
3. observation_count DESC

## Error Handling

### Taxon not found
```bash
$ taxa breakdown "NotARealPlant"
ERROR: Taxon 'NotARealPlant' not found in database
```

### Ambiguous taxon name
```bash
$ taxa breakdown "Malus"
ERROR: Ambiguous taxon 'Malus' found at multiple ranks: genus, species
Specify with --rank: taxa breakdown Malus --rank genus
```

### Invalid level specification
```bash
$ taxa breakdown Asteraceae --levels kingdom
ERROR: Cannot break down to 'kingdom' - it's higher than starting rank 'family'
Valid levels: subfamily, tribe, subtribe, genus, subgenus, section, subsection, species, subspecies, variety, form
```

### Allow non-consecutive levels
```bash
$ taxa breakdown Asteraceae --levels genus
# Works fine - skips subfamily, tribe, subtribe

$ taxa breakdown Asteraceae --levels subfamily,genus,species
# Shows: subfamily, genus, species (skips tribe, subtribe)
```

### Auto-sort levels
```bash
$ taxa breakdown Asteraceae --levels genus,subfamily
# Automatically reorders to: subfamily, genus
```

### No data at requested level
```bash
$ taxa breakdown Asteraceae --levels subtribe,genus
# If no subtribe data exists, shows only genus breakdowns
```

### Empty results
```bash
$ taxa breakdown Asteraceae --region north_coast
No observations found for Asteraceae in region 'north_coast'
```

## Testing Strategy

### Unit Tests - taxonomy.py

- `test_taxonomic_ranks_order()` - verify hierarchy is correct
- `test_get_next_ranks()` - test getting next N ranks
- `test_get_next_ranks_at_end()` - handle ranks at bottom of hierarchy
- `test_validate_rank_sequence()` - catch invalid rank specifications
- `test_sort_ranks()` - verify sorting by hierarchy

### Unit Tests - Query Generation

- `test_generate_breakdown_query_single_level()` - subfamily only
- `test_generate_breakdown_query_multiple_levels()` - subfamily + tribe
- `test_generate_breakdown_query_skip_levels()` - family → genus
- `test_generate_breakdown_query_with_region()` - region filtering
- `test_auto_sort_levels()` - genus,subfamily → subfamily,genus

### Integration Tests

- `test_breakdown_command_basic()` - family → subfamily
- `test_breakdown_command_multiple_levels()` - full hierarchy
- `test_breakdown_includes_subtotals()` - verify UNION query structure
- `test_breakdown_with_region_filter()` - region-specific results
- `test_breakdown_empty_results()` - no data edge case

### Error Handling Tests

- `test_breakdown_taxon_not_found()` - invalid taxon name
- `test_breakdown_invalid_level()` - level above starting rank
- `test_breakdown_ambiguous_taxon()` - same name at multiple ranks

### CLI Integration Test

```python
def test_breakdown_cli_output():
    result = runner.invoke(cli, ['breakdown', 'Asteraceae', '--levels', 'subfamily'])
    assert result.exit_code == 0
    assert 'Asteroideae' in result.output
    assert 'observation_count' in result.output
```

## Files to Create/Modify

**New files:**
- `src/taxa/taxonomy.py` - Shared taxonomy constants and utilities
- `src/taxa/breakdown.py` - Breakdown query generation logic
- `tests/test_taxonomy.py` - Unit tests for taxonomy utilities
- `tests/test_breakdown.py` - Unit tests for breakdown logic
- `tests/test_breakdown_integration.py` - Integration tests with test database

**Modified files:**
- `src/taxa/schema.py` - Use TAXONOMIC_RANKS constant
- `src/taxa/cli.py` - Add breakdown command
- `tests/conftest.py` - Add fixtures for breakdown tests (if needed)

## Future Enhancements

Not in initial scope, but could be added later:

- `--include-taxon-count` flag - count ALL taxa (not just species)
- `--include-observers` flag - add observer_count column
- `--no-counts` flag - just show hierarchy, no aggregations
- `--format` option - json, csv, or table output formats
- `--rank` flag - disambiguate when taxon name appears at multiple ranks
- Support for multiple base taxa in one query
- Visualization output (tree structure)

## Implementation Plan

See separate implementation plan document (to be created during implementation phase).
