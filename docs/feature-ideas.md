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

## Percentage Breakdown

Show what percentage of observations each child taxon represents relative to the parent taxon.

### Proposed Behavior

Add a percentage column to breakdown output showing each row's proportion of total observations:

```bash
taxa breakdown Rosaceae
subfamily        observation_count  species_count  pct_of_parent
Amygdaloideae    14534             39             28.3%
Dryadoideae      593               1              1.2%
Rosoideae        28348             31             55.2%
NULL             8436              0              16.4%
```

### Implementation Considerations

- Calculate percentage as `(row_observations / sum_all_observations) * 100`
- Round to 1 decimal place for readability
- For multi-level breakdowns, percentage should be relative to the immediate parent group
- Handle division by zero if total observations is 0
- Consider whether this should be always-on or opt-in via `--show-percent` flag

### Use Cases

- Quickly identify dominant taxa in a group
- Understand relative importance of different subfamilies/tribes/genera
- Spot rare vs common taxa at a glance

## Filter by Minimum Observation Count

Add a `--min-observations` flag to filter out taxa with few observations, reducing noise in large breakdowns.

### Proposed Behavior

```bash
taxa breakdown Rosaceae --min-observations 1000
subfamily        observation_count  species_count
Amygdaloideae    14534             39
Rosoideae        28348             31
NULL             8436              0
# Dryadoideae (593 obs) excluded because < 1000
```

### Implementation Considerations

- Filter in SQL query using HAVING clause for better performance
- Should this filter on `observation_count`, `species_count`, or both?
- Probably just observation_count is most useful
- Consider also `--min-species` for filtering by species diversity
- Add to query generation in `generate_breakdown_query()`

### Use Cases

- Focus on major taxonomic groups when exploring large families
- Remove rarely-observed taxa from output
- Make large breakdowns more readable by excluding noise

## Hyperlinks to iNaturalist Taxon Pages

Add clickable hyperlinks to iNaturalist taxon pages in the breakdown output.

### Proposed Behavior

Include a column with URLs to the iNaturalist taxon page:

```bash
taxa breakdown Rosaceae
subfamily        observation_count  species_count  url
Amygdaloideae    14534             39             https://www.inaturalist.org/taxa/[ID]
Dryadoideae      593               1              https://www.inaturalist.org/taxa/[ID]
Rosoideae        28348             31             https://www.inaturalist.org/taxa/[ID]
```

### Alternative: Terminal Hyperlinks

Use OSC 8 escape sequences to make the taxon name itself clickable (if terminal supports it):

```bash
taxa breakdown Rosaceae
# Amygdaloideae would be a clickable link in supporting terminals
# Falls back to plain text in non-supporting terminals
```

### Implementation Considerations

- Need to include taxon ID in the breakdown query
- iNaturalist URL format: `https://www.inaturalist.org/taxa/{id}`
- For OSC 8 hyperlinks: `\033]8;;{url}\033\\{text}\033]8;;\033\\`
- Most modern terminals support OSC 8 (iTerm2, Terminal.app, Windows Terminal, etc.)
- Consider making URLs opt-in with `--show-urls` flag
- For NULL rows, omit the URL (no taxon to link to)

### Use Cases

- Quick navigation to iNaturalist for more details about a taxon
- See photos, maps, and full taxonomy information
- Verify identification or learn more about unfamiliar taxa

## Automatic Paging for Long Output

Automatically invoke a pager (like `less`) when breakdown or query output exceeds terminal height. Prevents long results from scrolling past, similar to `git log` behavior. Would check output line count against terminal height and conditionally pipe to pager when in TTY mode.

## Multi-Column Layout for Wide Terminals

Use horizontal space efficiently by arranging breakdown results in multiple columns when the terminal is wide enough. Instead of one row per line, render items in 2-3-4 columns depending on terminal width. Uses `rich.columns.Columns` to create newspaper-style columnar layout that fits more data on screen.

## Colorize Taxonomic Ranks

Add color-coding to breakdown output to create visual hierarchy. Options include: color-code rank column values (genus=blue, species=green), color entire rows based on rank level, highlight high/low observation counts, or subtle syntax highlighting (bold headers, dimmed data). Deferred until basic table formatting is stable.
