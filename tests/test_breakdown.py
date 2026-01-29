"""Tests for breakdown query generation."""
import sqlite3
import pytest
from taxa.breakdown import find_taxon_rank


@pytest.fixture
def test_db():
    """Create in-memory test database with sample taxa."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    # Create simplified taxa table
    cursor.execute("""
        CREATE TABLE taxa (
            id INTEGER PRIMARY KEY,
            scientific_name TEXT,
            family TEXT,
            subfamily TEXT,
            tribe TEXT,
            genus TEXT,
            species TEXT
        )
    """)

    # Insert test data
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, family, subfamily, tribe, genus, species)
        VALUES (1, 'Asteraceae family', 'Asteraceae', NULL, NULL, NULL, NULL)
    """)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, family, subfamily, genus, species)
        VALUES (2, 'Taraxacum officinale', 'Asteraceae', 'Cichorioideae', 'Taraxacum', 'officinale')
    """)

    conn.commit()
    yield conn
    conn.close()


def test_find_taxon_rank_family(test_db):
    """Test finding taxon at family rank."""
    rank = find_taxon_rank(test_db, 'Asteraceae')
    assert rank == 'family'


def test_find_taxon_rank_genus(test_db):
    """Test finding taxon at genus rank."""
    rank = find_taxon_rank(test_db, 'Taraxacum')
    assert rank == 'genus'


def test_find_taxon_rank_not_found(test_db):
    """Test error when taxon not found."""
    with pytest.raises(ValueError, match="not found"):
        find_taxon_rank(test_db, 'NotARealTaxon')
