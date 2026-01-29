# Auto-Fallthrough to First Populated Rank - Design

**Date:** 2026-01-29
**Status:** Approved

## Problem

When running `taxa breakdown Dryadoideae` (a subfamily), the tool defaults to showing the next rank (tribe). If all Dryadoideae taxa have NULL tribe values, the breakdown shows a single unhelpful row with `tribe=NULL`. Users doing exploratory analysis want to see actual data, not an all-NULL result.

## Solution

Implement **smart default selection**: when no `--levels` is explicitly specified, detect and use the first populated rank instead of blindly using the next rank.

## Key Principles

1. **Respect explicit requests** - If user specifies `--levels tribe`, show tribe even if it's all NULL. That NULL result is informative ("this rank isn't used here").
2. **Be smart for exploration** - When no levels specified, assume the user wants useful data, not NULLs.
3. **Be transparent** - Always show a notice when we skip ranks, so users understand what happened.
4. **Check all ranks** - Don't give up after 2-3 ranks; search the entire hierarchy for populated data.

## User-Facing Behavior

### Current Behavior
```bash
taxa breakdown Dryadoideae
# Output:
# tribe  observation_count  species_count
# NULL   593                1
```

### New Behavior
```bash
taxa breakdown Dryadoideae
# Stderr: [Notice: tribe unpopulated, showing genus instead]
# Stdout:
# genus         observation_count  species_count
# Cercocarpus   593                1
```

### With Explicit Levels (Unchanged)
```bash
taxa breakdown Dryadoideae --levels tribe
# Output:
# tribe  observation_count  species_count
# NULL   593                1
```

### When Nothing is Populated
```bash
taxa breakdown SomeSpecies
# ERROR: No populated levels below 'species' in taxonomy
```

## Implementation

### New Function in `breakdown.py`

Add `find_first_populated_rank()` alongside the existing `find_taxon_rank()`:

```python
def find_first_populated_rank(conn, base_taxon, base_rank):
    """Find the first populated rank below base_rank for the given taxon.

    Checks each rank in hierarchical order to find the first one with
    non-NULL values among descendants of base_taxon.

    Args:
        conn: SQLite database connection
        base_taxon: Name of base taxon (e.g., "Rosaceae")
        base_rank: Rank of base taxon (e.g., "family")

    Returns:
        Tuple of (populated_rank, expected_rank) where:
        - populated_rank: First rank below base_rank with non-NULL data
        - expected_rank: The immediate next rank after base_rank

    Raises:
        ValueError: If no populated ranks found below base_rank
    """
```

**Algorithm:**
1. Get all remaining ranks using `get_next_ranks(base_rank, count=100)` (or slice from TAXONOMIC_RANKS)
2. Store `expected_rank = remaining_ranks[0]` (the immediate next rank)
3. For each candidate rank in remaining_ranks:
   - Execute: `SELECT 1 FROM taxa WHERE {base_rank} = ? AND {candidate_rank} IS NOT NULL LIMIT 1`
   - If any row returned, return `(candidate_rank, expected_rank)`
4. If loop completes without finding data, raise `ValueError(f"No populated levels below '{base_rank}' in taxonomy")`

### Changes to `cli.py:breakdown()`

Modify the default level selection logic (currently lines 189-197):

**Current code:**
```python
if levels:
    level_list = [level.strip() for level in levels.split(',')]
    validate_rank_sequence(base_rank, level_list)
else:
    level_list = get_next_ranks(base_rank, count=1)
    if not level_list:
        click.echo(f"ERROR: No levels below '{base_rank}' in taxonomy", err=True)
        sys.exit(1)
```

**New code:**
```python
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
```

## Testing Strategy

### Unit Tests
- Test `find_first_populated_rank()` with various scenarios:
  - Next rank is populated (no skip)
  - Next rank is NULL, second rank is populated (skip one)
  - Multiple ranks are NULL (skip several)
  - No ranks are populated (raises ValueError)
  - Edge case: already at lowest rank

### Integration Tests
- Test `breakdown` command with:
  - Default behavior on taxon with unpopulated next rank
  - Verify stderr notice appears
  - Verify correct rank is shown
  - Explicit `--levels` still shows NULL values
  - Error case when no populated ranks exist

## Edge Cases

1. **Already at lowest rank** - `get_next_ranks()` returns empty list, should error appropriately
2. **All remaining ranks are NULL** - Raise ValueError with clear message
3. **Database schema missing some ranks** - Query will fail gracefully (column doesn't exist)
4. **Performance** - Quick `LIMIT 1` checks should be fast even on large databases

## Future Enhancements

This design explicitly does NOT include:
- Auto-fallthrough for multi-level breakdowns (`--levels subfamily,tribe,genus`)
- A flag to disable smart defaults
- Caching of populated rank information

These could be added later if needed, but YAGNI for now.
