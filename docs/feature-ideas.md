# Feature Ideas

## Debug Mode for SQL Queries

Add a `--debug` flag to commands that execute SQL queries to print the generated queries to stderr. This would make it easier to investigate issues and understand what queries are being executed.

### Use Cases

- Debugging unexpected query results
- Understanding performance characteristics
- Learning how the breakdown query generation works
- Troubleshooting issues without needing to read source code

### Proposed Implementation

Add a global `--debug` flag that prints:
- Generated SQL queries
- Query parameters
- Query execution time
- Number of rows returned

Example usage:
```bash
taxa --debug breakdown Dryadoideae
# Output to stderr:
# [DEBUG] Executing query:
# SELECT tribe, SUM(observations.observation_count) as observation_count, ...
# FROM taxa JOIN observations ON observations.taxon_id = taxa.id
# WHERE subfamily = ?
# GROUP BY tribe
# [DEBUG] Parameters: ['Dryadoideae']
# [DEBUG] Query time: 0.023s
# [DEBUG] Rows returned: 1
```

### Affected Commands

- `breakdown` - Show generated breakdown queries
- `query` - Show the actual SQL being executed (if needed)
- Any future commands that generate dynamic SQL

## Auto-Fallthrough to Next Populated Rank

When breaking down a taxon, automatically skip to the next populated taxonomic rank if the immediate next rank has only NULL values.

### Problem

Currently, when breaking down a taxon like Dryadoideae (subfamily) by the next rank (tribe), if all taxa have NULL tribe values, the breakdown shows a single row with `tribe=NULL` and the total observations. While this is technically correct, it doesn't provide a useful breakdown of the data.

### Proposed Behavior

Detect when the next rank is entirely unpopulated and automatically fall through to the next rank that has actual data.

Example:
```bash
taxa breakdown Dryadoideae
# Current output (after NULL fix):
# tribe  observation_count  species_count
# NULL   593                1

# Proposed output:
# [Notice: tribe is unpopulated, showing genus breakdown instead]
# genus         observation_count  species_count
# Cercocarpus   593                1
```

### Implementation Considerations

- Should this be automatic or opt-in via a flag like `--auto-fallthrough`?
- How many ranks should we skip before giving up?
- Should we show a notice/warning when falling through?
- What if multiple consecutive ranks are unpopulated?
- For multi-level breakdowns (`--levels subfamily,tribe,genus`), should we skip only the empty intermediate levels?

### Alternative: Smart Default Level Selection

Instead of always using the next rank as default, analyze the taxonomy and choose the first populated rank as the default breakdown level.

```bash
taxa breakdown Dryadoideae
# Instead of defaulting to tribe (unpopulated)
# Automatically detect that genus is the first populated child rank
# and use that as the default
```
