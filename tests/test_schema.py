import sqlite3
from taxa.schema import create_schema


def test_create_schema_creates_tables(tmp_path):
    """Test that create_schema creates all required tables."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)

    create_schema(conn)

    cursor = conn.cursor()

    # Check taxa table exists with correct columns
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='taxa'")
    assert cursor.fetchone() is not None

    cursor.execute("PRAGMA table_info(taxa)")
    columns = {row[1] for row in cursor.fetchall()}

    required_columns = {
        'id', 'scientific_name', 'common_name', 'rank',
        'kingdom', 'phylum', 'class', 'order_name', 'family',
        'subfamily', 'tribe', 'genus', 'species'
    }
    assert required_columns.issubset(columns)

    # Check observations table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='observations'")
    assert cursor.fetchone() is not None

    # Check regions table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='regions'")
    assert cursor.fetchone() is not None

    # Check sync_info table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_info'")
    assert cursor.fetchone() is not None

    conn.close()


def test_create_schema_creates_indexes(tmp_path):
    """Test that create_schema creates required indexes."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)

    create_schema(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {row[0] for row in cursor.fetchall()}

    expected_indexes = {
        'idx_taxa_family',
        'idx_taxa_genus',
        'idx_taxa_subfamily',
        'idx_taxa_tribe',
        'idx_obs_region'
    }

    assert expected_indexes.issubset(indexes)

    conn.close()
