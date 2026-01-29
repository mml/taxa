"""Tests for breakdown query generation."""
import sqlite3
import pytest
from taxa.breakdown import find_taxon_rank, generate_breakdown_query, find_first_populated_rank


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


def test_generate_breakdown_query_single_level():
    """Test generating query for single level breakdown."""
    from taxa.breakdown import generate_breakdown_query

    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['subfamily']
    )

    # Should have single SELECT (no UNION)
    assert 'UNION' not in query

    # Should group by subfamily
    assert 'GROUP BY subfamily' in query

    # Should filter by family
    assert 'family = ?' in query

    # Should aggregate observation and species counts
    assert 'SUM(observations.observation_count)' in query
    assert 'COUNT(DISTINCT' in query
    assert 'species' in query.lower()

    # Should order by subfamily, then observation count
    assert 'ORDER BY' in query

    # Params should have base taxon
    assert params == ['Asteraceae']


def test_generate_breakdown_query_multiple_levels():
    """Test generating query with multiple hierarchical levels."""
    from taxa.breakdown import generate_breakdown_query

    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['subfamily', 'tribe']
    )

    # Should have UNION ALL for multiple queries
    assert 'UNION ALL' in query

    # Should have 2 SELECTs (one for subfamily, one for subfamily+tribe)
    assert query.count('SELECT') == 2

    # First query groups by subfamily only
    # Second query groups by subfamily and tribe
    assert 'GROUP BY subfamily' in query
    assert 'GROUP BY subfamily, tribe' in query

    # Should have NULL as tribe in first query
    assert 'NULL as tribe' in query

    # Params should have base taxon twice (once per query)
    assert params == ['Asteraceae', 'Asteraceae']


def test_generate_breakdown_query_with_region():
    """Test generating query with region filter."""
    from taxa.breakdown import generate_breakdown_query

    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['subfamily'],
        region_key='north_coast'
    )

    # Should filter by region
    assert 'observations.region_key = ?' in query

    # Params should have both taxon and region
    assert params == ['Asteraceae', 'north_coast']


def test_generate_breakdown_query_skip_levels():
    """Test generating query that skips intermediate levels."""
    from taxa.breakdown import generate_breakdown_query

    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['genus']  # Skip subfamily, tribe, subtribe
    )

    # Should work without intermediate levels
    assert 'GROUP BY genus' in query
    assert params == ['Asteraceae']


def test_find_first_populated_rank_next_rank_populated(memory_sample_db):
    """When next rank has data, return it without skipping."""
    conn = memory_sample_db

    # Rosaceae family has subfamilies populated
    populated, expected = find_first_populated_rank(conn, "Rosaceae", "family")

    assert populated == "subfamily"
    assert expected == "subfamily"


def test_find_first_populated_rank_skip_one_rank(memory_sample_db):
    """When next rank is NULL, skip to the first populated rank."""
    conn = memory_sample_db

    # Dryadoideae subfamily has NULL tribe, but populated genus
    populated, expected = find_first_populated_rank(conn, "Dryadoideae", "subfamily")

    assert populated == "genus"
    assert expected == "tribe"


def test_find_first_populated_rank_skip_multiple_ranks(memory_sample_db):
    """When multiple ranks are NULL, skip to the first populated rank."""
    conn = memory_sample_db
    cursor = conn.cursor()

    # Create a taxon with NULL tribe and subtribe, but populated genus
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily, tribe, subtribe, genus)
        VALUES (999, 'Test genus', 'genus', 'Rosaceae', 'Testinae', NULL, NULL, 'Testus')
    """)
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (999, 'test_region', 1, 50)
    """)
    conn.commit()

    populated, expected = find_first_populated_rank(conn, "Testinae", "subfamily")

    assert populated == "genus"
    assert expected == "tribe"


def test_find_first_populated_rank_no_populated_ranks(memory_sample_db):
    """When no ranks below base are populated, raise ValueError."""
    conn = memory_sample_db
    cursor = conn.cursor()

    # Create a species with no lower ranks populated
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, genus, species, subspecies, variety)
        VALUES (998, 'Test species', 'species', 'Rosaceae', 'Testus', 'testus', NULL, NULL)
    """)
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (998, 'test_region', 1, 30)
    """)
    conn.commit()

    with pytest.raises(ValueError, match="No populated levels below 'species' in taxonomy"):
        find_first_populated_rank(conn, "testus", "species")


def test_find_first_populated_rank_at_lowest_rank(memory_sample_db):
    """When already at lowest rank, raise ValueError."""
    conn = memory_sample_db

    # 'form' is the lowest rank
    with pytest.raises(ValueError, match="No levels below 'form' in taxonomy"):
        find_first_populated_rank(conn, "some_form", "form")
