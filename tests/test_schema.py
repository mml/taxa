import sqlite3
import pytest
from taxa.schema import create_schema


@pytest.fixture
def db_conn(tmp_path):
    """Fixture for database connection with automatic cleanup."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    yield conn
    conn.close()


def test_create_schema_creates_tables(db_conn):
    """Test that create_schema creates all required tables."""
    create_schema(db_conn)

    cursor = db_conn.cursor()

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


def test_create_schema_creates_indexes(db_conn):
    """Test that create_schema creates required indexes."""
    create_schema(db_conn)

    cursor = db_conn.cursor()
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


def test_create_schema_idempotent(db_conn):
    """Test that create_schema can be called multiple times."""
    create_schema(db_conn)
    create_schema(db_conn)  # Should not raise error

    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    assert 'taxa' in tables


def test_create_schema_creates_all_rank_columns(db_conn):
    """Test that all rank columns are created in taxa table."""
    create_schema(db_conn)

    cursor = db_conn.cursor()
    cursor.execute("PRAGMA table_info(taxa)")
    columns = {row[1] for row in cursor.fetchall()}

    all_rank_columns = {
        'kingdom', 'phylum', 'class', 'order_name', 'family',
        'subfamily', 'tribe', 'subtribe', 'genus', 'subgenus',
        'section', 'subsection', 'species', 'subspecies', 'variety', 'form'
    }
    assert all_rank_columns.issubset(columns)


def test_create_schema_creates_foreign_key(db_conn):
    """Test that foreign key constraint is created on observations table."""
    create_schema(db_conn)

    cursor = db_conn.cursor()
    cursor.execute("PRAGMA foreign_key_list(observations)")
    fks = cursor.fetchall()

    # Should have one foreign key referencing taxa table
    assert len(fks) > 0
    assert fks[0][2] == 'taxa'  # Referenced table name
