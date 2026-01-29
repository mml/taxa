"""Shell completion support for taxa CLI."""
import json
import sqlite3
import os
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from taxa.taxonomy import TAXONOMIC_RANKS


def generate_completion_cache(database_path: Path) -> dict:
    """Generate completion data from database.

    Args:
        database_path: Path to flora.db

    Returns:
        Dictionary with completion data

    Raises:
        FileNotFoundError: If database doesn't exist
    """
    database_path = Path(database_path)

    if not database_path.exists():
        raise FileNotFoundError(f"Database not found: {database_path}")

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Get unique taxon names
    cursor.execute("SELECT DISTINCT scientific_name FROM taxa ORDER BY scientific_name")
    taxon_names = [row[0] for row in cursor.fetchall()]

    # Get unique region keys
    cursor.execute("SELECT DISTINCT region_key FROM observations ORDER BY region_key")
    region_keys = [row[0] for row in cursor.fetchall()]

    # Get database stats
    db_stat = database_path.stat()

    conn.close()

    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "database_path": str(database_path.absolute()),
            "database_mtime": db_stat.st_mtime,
            "taxa_count": len(taxon_names),
            "region_count": len(region_keys),
        },
        "taxon_names": taxon_names,
        "region_keys": region_keys,
        "ranks": TAXONOMIC_RANKS,
    }


def write_completion_cache(cache_data: dict, cache_path: Path):
    """Write cache to file with atomic write and flock protection.

    Args:
        cache_data: Dictionary with completion data
        cache_path: Path where cache should be written
    """
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file with exclusive lock
    temp_path = cache_path.with_suffix('.tmp')

    with open(temp_path, 'w') as f:
        # Acquire exclusive lock (blocks if another process has it)
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(cache_data, f, indent=2)
        # Lock released on close

    # Atomic rename
    temp_path.rename(cache_path)


def get_cache_path(database_name: str) -> Path:
    """Get cache file path for a database.

    Args:
        database_name: Database filename (e.g., 'flora.db')

    Returns:
        Path to cache file in XDG cache directory
    """
    # Extract basename without extension
    db_base = Path(database_name).stem

    # Respect XDG_CACHE_HOME or use ~/.cache
    cache_home = os.environ.get('XDG_CACHE_HOME')
    if cache_home:
        cache_dir = Path(cache_home)
    else:
        cache_dir = Path.home() / '.cache'

    return cache_dir / 'taxa' / f'completion-cache-{db_base}.json'
