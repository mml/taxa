"""Tests for completion cache generation."""
import json
import sqlite3
from pathlib import Path
import pytest
from taxa.completion import generate_completion_cache, write_completion_cache, get_cache_path
from taxa.schema import create_schema


@pytest.fixture
def sample_db(tmp_path):
    """Create test database with sample data."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    create_schema(conn)

    cursor = conn.cursor()

    # Insert sample taxa
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, genus)
        VALUES (1, 'Quercus', 'genus', 'Fagaceae', 'Quercus')
    """)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, genus, species)
        VALUES (2, 'Quercus alba', 'species', 'Fagaceae', 'Quercus', 'alba')
    """)

    # Insert sample observations
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (1, 'us-ca', 123, 100)
    """)
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (2, 'us-or', 456, 200)
    """)

    conn.commit()
    conn.close()

    return db_path


def test_generate_cache_basic_structure(sample_db):
    """Cache includes required top-level keys."""
    cache = generate_completion_cache(sample_db)

    assert "metadata" in cache
    assert "taxon_names" in cache
    assert "region_keys" in cache
    assert "ranks" in cache


def test_generate_cache_taxon_names(sample_db):
    """Cache includes taxon names from database."""
    cache = generate_completion_cache(sample_db)

    assert "Quercus" in cache["taxon_names"]
    assert "Quercus alba" in cache["taxon_names"]
    assert len(cache["taxon_names"]) == 2


def test_generate_cache_metadata_fields(sample_db):
    """Metadata includes all required fields."""
    cache = generate_completion_cache(sample_db)

    metadata = cache["metadata"]
    assert "generated_at" in metadata
    assert "database_path" in metadata
    assert "database_mtime" in metadata
    assert "taxa_count" in metadata
    assert "region_count" in metadata


def test_generate_cache_metadata_values(sample_db):
    """Metadata values are correct."""
    cache = generate_completion_cache(sample_db)

    metadata = cache["metadata"]
    assert metadata["taxa_count"] == 2
    assert metadata["region_count"] == 2
    assert metadata["database_mtime"] > 0
    assert str(sample_db) in metadata["database_path"]


def test_generate_cache_region_keys(sample_db):
    """Cache includes region keys from database."""
    cache = generate_completion_cache(sample_db)

    assert "us-ca" in cache["region_keys"]
    assert "us-or" in cache["region_keys"]
    assert len(cache["region_keys"]) == 2


def test_generate_cache_ranks(sample_db):
    """Cache includes taxonomic ranks."""
    cache = generate_completion_cache(sample_db)

    assert "kingdom" in cache["ranks"]
    assert "genus" in cache["ranks"]
    assert "species" in cache["ranks"]


def test_write_cache_creates_file(tmp_path, sample_db):
    """write_completion_cache creates JSON file."""
    cache_path = tmp_path / "cache.json"
    cache_data = generate_completion_cache(sample_db)

    write_completion_cache(cache_data, cache_path)

    assert cache_path.exists()


def test_write_cache_valid_json(tmp_path, sample_db):
    """Written cache is valid JSON."""
    cache_path = tmp_path / "cache.json"
    cache_data = generate_completion_cache(sample_db)

    write_completion_cache(cache_data, cache_path)

    with open(cache_path) as f:
        loaded = json.load(f)

    assert loaded["taxon_names"] == cache_data["taxon_names"]
    assert loaded["region_keys"] == cache_data["region_keys"]


def test_write_cache_creates_directory(tmp_path, sample_db):
    """write_completion_cache creates parent directories."""
    cache_path = tmp_path / "subdir" / "cache.json"
    cache_data = generate_completion_cache(sample_db)

    write_completion_cache(cache_data, cache_path)

    assert cache_path.exists()


def test_get_cache_path_default():
    """Cache path uses XDG_CACHE_HOME or ~/.cache."""
    cache_path = get_cache_path("flora.db")

    # Should contain either XDG_CACHE_HOME or ~/.cache
    path_str = str(cache_path)
    assert "taxa" in path_str
    assert "completion-cache-flora.json" in path_str


def test_get_cache_path_respects_xdg(tmp_path, monkeypatch):
    """Cache path respects XDG_CACHE_HOME environment variable."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    cache_path = get_cache_path("flora.db")

    assert str(cache_path).startswith(str(tmp_path))
    assert cache_path == tmp_path / "taxa" / "completion-cache-flora.json"


def test_get_cache_path_different_databases():
    """Different database names get different cache files."""
    cache1 = get_cache_path("flora.db")
    cache2 = get_cache_path("test.db")

    assert "flora" in str(cache1)
    assert "test" in str(cache2)
    assert cache1 != cache2


def test_generate_cache_missing_database():
    """generate_completion_cache raises FileNotFoundError for missing DB."""
    with pytest.raises(FileNotFoundError, match="Database not found"):
        generate_completion_cache(Path("/nonexistent/database.db"))


def test_generate_cache_empty_database(tmp_path):
    """Empty database produces valid cache with empty lists."""
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(db_path)
    create_schema(conn)
    conn.close()

    cache = generate_completion_cache(db_path)

    assert cache["taxon_names"] == []
    assert cache["region_keys"] == []
    assert cache["metadata"]["taxa_count"] == 0
    assert cache["metadata"]["region_count"] == 0
