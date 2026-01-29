# Zsh Tab Completion for Taxa Tool

**Date**: 2026-01-28
**Status**: Implemented
**Author**: Matt & Claude

## Overview

Add comprehensive zsh tab completion for the taxa CLI tool with intelligent, context-aware suggestions powered by cached database content.

## Goals

- **Full dynamic completion**: Complete taxon names, region keys, taxonomic ranks, file paths, and all commands/options
- **Fast performance**: Sub-50ms completion via persistent file cache
- **Graceful degradation**: Fall back to static completions when database unavailable
- **Easy installation**: Automated setup via `taxa completion install` command
- **Standards-compliant**: Follow XDG cache directory conventions

## Architecture

### Components

**1. Zsh Completion Script** (`_taxa`)
- Lives in `~/.config/taxa/completions/_taxa`
- Provides static completions (commands, options, flags)
- Loads dynamic completions from cache
- Handles context-aware completion based on current command
- Checks database mtime and triggers background cache regeneration when stale

**2. Cache Generator** (`taxa/completion.py`)
- Queries database to extract completion data
- Generates JSON cache with taxon names, region keys, and ranks
- Includes metadata (database path, mtime, generation timestamp)
- Uses flock for safe concurrent writes

**3. Installation Command** (`taxa completion install`)
- Generates and installs `_taxa` completion script
- Creates initial completion cache
- Provides instructions for `.zshrc` setup
- Future: auto-detect and offer to modify `.zshrc`

## Cache Structure

### Location
- Path: `~/.cache/taxa/completion-cache-{dbname}.json`
- Respects `$XDG_CACHE_HOME` environment variable
- Separate cache per database (based on basename)

### Format
```json
{
  "metadata": {
    "generated_at": "2026-01-28T10:30:00Z",
    "database_path": "/home/user/flora.db",
    "database_mtime": 1738065000.123,
    "taxa_count": 1250,
    "region_count": 45
  },
  "taxon_names": ["Plantae", "Magnoliophyta", "Quercus", ...],
  "region_keys": ["us-ca", "us-or", "us-wa", ...],
  "ranks": ["kingdom", "phylum", "class", "order", "family", "genus", "species"]
}
```

### Invalidation Strategy
The completion script checks on each invocation:
1. Does cache file exist? If not, try to generate (background), use static completions
2. Does database exist? If not, use static completions
3. Has database mtime changed? If yes, regenerate cache (background), use stale cache meanwhile
4. Is cache older than 24 hours? If yes, regenerate as precaution

Background regeneration: fork `taxa completion generate-cache` asynchronously. Current completion uses stale cache, next completion gets fresh data.

## Completion Details

### Completion Function Structure

```zsh
_taxa() {
  local -a commands
  commands=(
    'sync:Sync data from iNaturalist API to database'
    'query:Run SQL query or open interactive shell'
    'search:Search for iNaturalist IDs'
    'info:Show database info and stats'
    'breakdown:Break down taxon into hierarchical levels'
    'completion:Manage shell completions'
  )

  _arguments -C \
    '1: :->command' \
    '*:: :->args'

  case $state in
    command) _describe 'command' commands ;;
    args) _taxa_${words[1]} ;;  # Delegate to subcommand
  esac
}
```

### Context-Aware Completions

Each subcommand has its own completion function:

- `_taxa_breakdown`:
  - Taxon argument: complete from cached taxon names
  - `--levels`: complete from cached rank names
  - `--region`: complete from cached region keys
  - `--database`: complete file paths (*.db files)

- `_taxa_sync`:
  - Config argument: complete file paths (*.yaml files)
  - `--timeout`: no completion (numeric)
  - `--dry-run`: flag only

- `_taxa_query`:
  - Query argument: no completion (free text SQL)
  - `--database`: complete file paths (*.db files)

- `_taxa_search`:
  - Delegates to `_taxa_search_places` and `_taxa_search_taxa`
  - Query argument: no completion (free text search)

- `_taxa_info`:
  - `--database`: complete file paths (*.db files)

### Cache Loading

```zsh
_taxa_load_cache() {
  local cache_file="${XDG_CACHE_HOME:-$HOME/.cache}/taxa/completion-cache-${database_name}.json"
  [[ -f $cache_file ]] || return 1

  # Parse JSON using jq
  taxon_names=("${(@f)$(jq -r '.taxon_names[]' $cache_file 2>/dev/null)}")
  region_keys=("${(@f)$(jq -r '.region_keys[]' $cache_file 2>/dev/null)}")
  ranks=("${(@f)$(jq -r '.ranks[]' $cache_file 2>/dev/null)}")
}
```

## Python Implementation

### CLI Commands

```python
@main.group()
def completion():
    """Manage shell completions."""
    pass

@completion.command()
@click.option('--shell', type=click.Choice(['zsh']), default='zsh')
def install(shell):
    """Install shell completion for taxa."""
    # 1. Create ~/.config/taxa/completions/ directory
    # 2. Write _taxa completion script from embedded template
    # 3. Generate initial cache
    # 4. Check if fpath setup exists in ~/.zshrc
    # 5. Print instructions to add fpath or reload shell

@completion.command()
@click.option('--database', '-d', default='flora.db')
def generate_cache(database):
    """Generate completion cache from database."""
    # Called by install command and by completion script
    # Can be run manually to force cache refresh
```

### Cache Generator Module

```python
# taxa/completion.py

def generate_completion_cache(database_path: Path) -> dict:
    """Generate completion data from database.

    Args:
        database_path: Path to flora.db

    Returns:
        Dictionary with completion data
    """
    if not database_path.exists():
        raise FileNotFoundError(f"Database not found: {database_path}")

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Get unique taxon names
    cursor.execute("SELECT DISTINCT name FROM taxa ORDER BY name")
    taxon_names = [row[0] for row in cursor.fetchall()]

    # Get unique region keys
    cursor.execute("SELECT DISTINCT region_key FROM observations ORDER BY region_key")
    region_keys = [row[0] for row in cursor.fetchall()]

    # Get database stats
    db_stat = database_path.stat()

    conn.close()

    return {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "database_path": str(database_path.absolute()),
            "database_mtime": db_stat.st_mtime,
            "taxa_count": len(taxon_names),
            "region_count": len(region_keys),
        },
        "taxon_names": taxon_names,
        "region_keys": region_keys,
        "ranks": TAXONOMIC_RANKS,  # From taxa.taxonomy
    }

def write_completion_cache(cache_data: dict, cache_path: Path):
    """Write cache to file with flock protection."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file, then atomic rename with flock
    temp_path = cache_path.with_suffix('.tmp')

    with open(temp_path, 'w') as f:
        # Acquire exclusive lock
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(cache_data, f, indent=2)
        # Lock released on close

    # Atomic rename
    temp_path.rename(cache_path)
```

## Data Flow

### Initial Setup
1. User runs `taxa completion install`
2. Command creates `~/.config/taxa/completions/_taxa` from template
3. Command runs `generate_completion_cache()` to create initial cache
4. Command checks `.zshrc` for fpath setup, prints instructions if missing
5. User adds to `.zshrc`: `fpath=(~/.config/taxa/completions $fpath)` and `autoload -Uz compinit && compinit`
6. User reloads shell: `exec zsh`

### Completion Flow (Normal)
1. User types `taxa breakdown <TAB>`
2. Zsh calls `_taxa()` completion function
3. Function loads cache from `~/.cache/taxa/completion-cache-flora.json`
4. Function checks database mtime vs cache metadata
5. If stale: fork background `taxa completion generate-cache`, use current cache
6. If fresh: use cache directly
7. Function returns taxon names as completion candidates
8. Zsh filters by prefix and displays matches

### Completion Flow (Cold Start)
1. User types `taxa <TAB>`
2. Function finds no cache file
3. Function returns static completions only (commands, options)
4. In background: attempt to generate cache if database exists
5. Next completion will have dynamic data

### Cache Refresh
1. User runs `taxa sync` (database modified)
2. Next completion detects mtime change
3. Background regeneration triggers
4. Fresh cache available for subsequent completions

## Error Handling

### Graceful Degradation
- **No database exists**: Static completions only (commands, options, flags)
- **Cache generation fails**: Silent failure, continue with static completions
- **Corrupted cache JSON**: Delete cache, regenerate on next completion
- **Database locked**: Skip cache regeneration, use stale cache
- **Permissions issues**: Log to stderr, fall back to static
- **Missing jq**: Print error to stderr: "jq not found. Install jq for dynamic completions."

### Edge Cases

**Large databases**:
- Cache all taxon names (zsh does prefix filtering automatically)
- Zsh pages results if too many matches
- Cache file might be 500KB+ but load performance is acceptable

**Multiple databases**:
- Cache filename includes database basename: `completion-cache-flora.json`
- Each database gets its own cache
- `--database` option determines which cache to load

**Concurrent cache generation**:
- Use `flock` on cache file during write
- Locks automatically released when process exits
- Other processes wait or skip if can't acquire lock immediately

## Testing

### Unit Tests

```python
# tests/test_completion.py

def test_generate_cache_basic(tmp_path, sample_db):
    """Cache includes taxon names, regions, ranks."""
    cache = generate_completion_cache(sample_db)
    assert "taxon_names" in cache
    assert "Quercus" in cache["taxon_names"]
    assert "region_keys" in cache
    assert "ranks" in cache

def test_generate_cache_empty_database(tmp_path):
    """Empty database produces valid cache structure."""
    # Should not crash, just return empty lists

def test_generate_cache_metadata(tmp_path, sample_db):
    """Metadata includes mtime, path, timestamp."""
    cache = generate_completion_cache(sample_db)
    assert cache["metadata"]["database_path"]
    assert cache["metadata"]["database_mtime"] > 0

def test_write_cache_atomic(tmp_path):
    """Cache write is atomic via temp file."""
    # Verify .tmp file used, then renamed

def test_concurrent_cache_write(tmp_path):
    """Concurrent writes don't corrupt cache."""
    # Simulate two processes writing simultaneously
    # Verify one blocks, cache is valid
```

### Integration Tests

```python
# tests/test_completion_install.py

def test_completion_install_creates_files(tmp_path, monkeypatch):
    """Install creates completion script and cache."""
    # Mock home directory
    # Run taxa completion install
    # Verify _taxa script exists in ~/.config/taxa/completions/
    # Verify cache file created in ~/.cache/taxa/

def test_completion_install_zshrc_instructions(capsys):
    """Install prints fpath setup instructions."""
    # Run install
    # Capture output
    # Verify contains fpath setup line and compinit call
```

### Manual Testing Checklist
- Install completion in real zsh, verify commands complete
- Type `taxa b<TAB>` → suggests `breakdown`
- Type `taxa breakdown Que<TAB>` → suggests Quercus taxa from database
- Type `taxa breakdown --levels <TAB>` → suggests taxonomic ranks
- Type `taxa breakdown --region <TAB>` → suggests region keys
- Run `taxa sync`, verify cache regenerates on next completion
- Delete cache, verify graceful fallback to static completions
- Test with missing database, verify no errors

## Implementation Phases

### Phase 1: Core Infrastructure
- Implement `taxa/completion.py` module
- Add `generate_completion_cache()` function
- Add `write_completion_cache()` with flock
- Add unit tests

### Phase 2: CLI Commands
- Add `taxa completion` command group
- Add `generate-cache` subcommand
- Add `install` subcommand
- Add integration tests

### Phase 3: Zsh Completion Script
- Create `_taxa` completion function template
- Implement static completions
- Implement cache loading
- Implement mtime-based invalidation
- Implement context-aware completions per subcommand

### Phase 4: Polish
- Manual testing in real shell
- Performance optimization if needed
- Documentation in README
- Update CLAUDE.md if shell activation needed for development

## Future Enhancements

- **Bash support**: Add bash completion using similar cache mechanism
- **Fish support**: Add fish completion (different syntax)
- **Smart caching**: Only cache frequently-used taxa (based on completion history)
- **Fuzzy matching**: Integrate with fzf for fuzzy completion
- **Auto-install**: Detect and offer to modify `.zshrc` automatically
- **Completion descriptions**: Show taxon common names or rank in completion menu
