"""Integration tests for breakdown command with realistic database."""
import sqlite3
import pytest
from pathlib import Path
from taxa.schema import create_schema
from taxa.breakdown import find_taxon_rank, generate_breakdown_query


@pytest.fixture
def populated_db(tmp_path):
    """Create test database with realistic taxonomic data."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    create_schema(conn)

    cursor = conn.cursor()

    # Insert family-level taxa
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family)
        VALUES (1, 'Asteraceae', 'family', 'Asteraceae')
    """)

    # Insert subfamily-level taxa
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily)
        VALUES (2, 'Asteroideae sp.', 'species', 'Asteraceae', 'Asteroideae')
    """)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily)
        VALUES (3, 'Cichorioideae sp.', 'species', 'Asteraceae', 'Cichorioideae')
    """)

    # Insert tribe-level taxa
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily, tribe)
        VALUES (4, 'Anthemideae sp.', 'species', 'Asteraceae', 'Asteroideae', 'Anthemideae')
    """)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily, tribe)
        VALUES (5, 'Astereae sp.', 'species', 'Asteraceae', 'Asteroideae', 'Astereae')
    """)

    # Insert observations
    for taxon_id in [2, 3, 4, 5]:
        cursor.execute("""
            INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
            VALUES (?, 'test_region', 1, ?)
        """, (taxon_id, taxon_id * 100))

    conn.commit()
    yield conn
    conn.close()


def test_breakdown_single_level_integration(populated_db):
    """Test breakdown with single level using real database."""
    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['subfamily']
    )

    cursor = populated_db.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()

    # Should have 2 subfamilies
    assert len(results) == 2

    # Check that subfamilies are present
    subfamilies = [row[0] for row in results]
    assert 'Asteroideae' in subfamilies
    assert 'Cichorioideae' in subfamilies

    # Check observation counts
    for row in results:
        assert row[1] > 0  # observation_count


def test_breakdown_multiple_levels_integration(populated_db):
    """Test breakdown with multiple levels using real database."""
    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['subfamily', 'tribe']
    )

    cursor = populated_db.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()

    # Should have subfamily totals + tribe breakdowns
    # 2 subfamilies + 2 tribes under Asteroideae = 4 rows
    assert len(results) >= 2

    # First row should be subfamily total (tribe=NULL)
    assert results[0][1] is None  # tribe column


def test_breakdown_with_region_filter_integration(populated_db):
    """Test breakdown with region filter using real database."""
    query, params = generate_breakdown_query(
        base_taxon='Asteraceae',
        base_rank='family',
        levels=['subfamily'],
        region_key='test_region'
    )

    cursor = populated_db.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()

    # Should still have results for test_region
    assert len(results) > 0


def test_breakdown_with_all_null_values_at_level():
    """Test single-level breakdown when all taxa have NULL at requested level.

    Reproduces the Dryadoideae bug: when all taxa in a group have NULL
    at the breakdown level, should return one row with NULL value showing
    total observations, not zero rows.
    """
    db_path = Path(':memory:')
    conn = sqlite3.connect(str(db_path))
    create_schema(conn)
    cursor = conn.cursor()

    # Create subfamily with no tribe values (like Dryadoideae)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily, genus)
        VALUES (1, 'Cercocarpus', 'genus', 'Rosaceae', 'Dryadoideae', 'Cercocarpus')
    """)
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, subfamily, genus)
        VALUES (2, 'Cercocarpus betuloides', 'species', 'Rosaceae', 'Dryadoideae', 'Cercocarpus')
    """)

    # Add observations
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (1, 'test', 1, 400)
    """)
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (2, 'test', 1, 193)
    """)

    conn.commit()

    # Break down by tribe (all NULL)
    query, params = generate_breakdown_query(
        base_taxon='Dryadoideae',
        base_rank='subfamily',
        levels=['tribe']
    )

    cursor.execute(query, params)
    results = cursor.fetchall()

    # Should get one row with tribe=NULL and total observations
    assert len(results) == 1
    assert results[0][0] is None  # tribe column
    assert results[0][1] == 593  # observation_count
    assert results[0][2] == 1  # species_count

    conn.close()
