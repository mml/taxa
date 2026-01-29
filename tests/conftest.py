"""Shared test fixtures."""
import sqlite3
import pytest
from click.testing import CliRunner
from pathlib import Path


@pytest.fixture
def memory_sample_db():
    """Create in-memory test database with Rosaceae family test data.

    Includes:
    - Rosaceae family with Dryadoideae subfamily (populated)
    - Dryadoideae subfamily with NULL tribe but Cercocarpus genus
    """
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    # Create taxa table with full schema
    cursor.execute("""
        CREATE TABLE taxa (
            id INTEGER PRIMARY KEY,
            scientific_name TEXT,
            rank TEXT,
            kingdom TEXT,
            phylum TEXT,
            class TEXT,
            order_name TEXT,
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
            form TEXT
        )
    """)

    # Create observations table
    cursor.execute("""
        CREATE TABLE observations (
            taxon_id INTEGER,
            region_key TEXT,
            place_id INTEGER,
            observation_count INTEGER
        )
    """)

    # Insert Rosaceae family row
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family)
        VALUES (1, 'Rosaceae', 'family', 'Rosaceae')
    """)

    # Insert Dryadoideae subfamily (subfamily is populated for Rosaceae)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily)
        VALUES (2, 'Dryadoideae', 'subfamily', 'Rosaceae', 'Dryadoideae')
    """)

    # Insert Cercocarpus genus (tribe is NULL, genus is populated)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily, tribe, genus)
        VALUES (3, 'Cercocarpus', 'genus', 'Rosaceae', 'Dryadoideae', NULL, 'Cercocarpus')
    """)

    # Insert observations for all taxa
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (1, 'test_region', 1, 100)
    """)
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (2, 'test_region', 1, 80)
    """)
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (3, 'test_region', 1, 60)
    """)

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def sample_db(tmp_path):
    """Create file-based test database with Rosaceae family test data.

    Returns a Path object pointing to the database file.
    """
    db_path = tmp_path / "sample.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create taxa table with full schema
    cursor.execute("""
        CREATE TABLE taxa (
            id INTEGER PRIMARY KEY,
            scientific_name TEXT,
            rank TEXT,
            kingdom TEXT,
            phylum TEXT,
            class TEXT,
            order_name TEXT,
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
            form TEXT
        )
    """)

    # Create observations table
    cursor.execute("""
        CREATE TABLE observations (
            taxon_id INTEGER,
            region_key TEXT,
            place_id INTEGER,
            observation_count INTEGER
        )
    """)

    # Insert Rosaceae family row
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family)
        VALUES (1, 'Rosaceae', 'family', 'Rosaceae')
    """)

    # Insert Dryadoideae subfamily (subfamily is populated for Rosaceae)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily)
        VALUES (2, 'Dryadoideae', 'subfamily', 'Rosaceae', 'Dryadoideae')
    """)

    # Insert Cercocarpus genus (tribe is NULL, genus is populated)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily, tribe, genus)
        VALUES (3, 'Cercocarpus', 'genus', 'Rosaceae', 'Dryadoideae', NULL, 'Cercocarpus')
    """)

    # Insert observations for all taxa
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (1, 'test_region', 1, 100)
    """)
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (2, 'test_region', 1, 80)
    """)
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (3, 'test_region', 1, 60)
    """)

    conn.commit()
    conn.close()
    yield str(db_path)


@pytest.fixture
def cli_runner():
    """Return Click test runner."""
    return CliRunner()
