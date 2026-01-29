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
