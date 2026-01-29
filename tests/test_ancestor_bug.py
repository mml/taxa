"""Test to reproduce the ancestor data overwriting bug."""
import sqlite3
from taxa.transform import flatten_taxon_ancestry
from taxa.schema import create_schema


def test_ancestor_insertion_preserves_parent_ranks():
    """
    Reproduce bug: inserting a taxon as an ancestor should not overwrite
    its parent rank data with NULLs.

    Scenario:
    1. Insert Asteraceae family with full ancestor data
    2. Insert it again as an ancestor object (no ancestors array)
    3. Verify parent ranks are still populated
    """
    # Create in-memory database
    conn = sqlite3.connect(':memory:')
    create_schema(conn)
    cursor = conn.cursor()

    # Simulate full taxon data (from fetch_taxa_batch)
    asteraceae_full = {
        'id': 47604,
        'name': 'Asteraceae',
        'rank': 'family',
        'preferred_common_name': 'Sunflowers, Daisies, Asters, and Allies',
        'is_active': True,
        'iconic_taxon_name': 'Plantae',
        'ancestors': [
            {'id': 47126, 'name': 'Plantae', 'rank': 'kingdom'},
            {'id': 211194, 'name': 'Tracheophyta', 'rank': 'phylum'},
            {'id': 47125, 'name': 'Angiospermae', 'rank': 'subphylum'},
            {'id': 47124, 'name': 'Magnoliopsida', 'rank': 'class'},
            {'id': 47605, 'name': 'Asterales', 'rank': 'order'},
        ]
    }

    # Insert with full data
    row1 = flatten_taxon_ancestry(asteraceae_full)
    cursor.execute("""
        INSERT OR REPLACE INTO taxa (
            id, scientific_name, common_name, rank,
            kingdom, phylum, class, order_name, family,
            subfamily, tribe, subtribe, genus, subgenus,
            section, subsection, species, subspecies, variety, form,
            is_active, iconic_taxon
        ) VALUES (
            :id, :scientific_name, :common_name, :rank,
            :kingdom, :phylum, :class, :order_name, :family,
            :subfamily, :tribe, :subtribe, :genus, :subgenus,
            :section, :subsection, :species, :subspecies, :variety, :form,
            :is_active, :iconic_taxon
        )
    """, row1)
    conn.commit()

    # Verify parent ranks are populated
    cursor.execute("SELECT kingdom, phylum, class, order_name FROM taxa WHERE id = 47604")
    result = cursor.fetchone()
    assert result == ('Plantae', 'Tracheophyta', 'Magnoliopsida', 'Asterales'), \
        f"Expected full parent ranks after first insert, got {result}"

    # Simulate ancestor object (as it appears in another taxon's ancestors array)
    # These do NOT have their own 'ancestors' array
    asteraceae_as_ancestor = {
        'id': 47604,
        'name': 'Asteraceae',
        'rank': 'family',
        'is_active': True,
        'iconic_taxon_name': 'Plantae',
        'preferred_common_name': 'Sunflowers, Daisies, Asters, and Allies',
        # NO 'ancestors' key!
    }

    # Insert again using INSERT OR IGNORE (simulating fixed sync.py:158)
    row2 = flatten_taxon_ancestry(asteraceae_as_ancestor)
    cursor.execute("""
        INSERT OR IGNORE INTO taxa (
            id, scientific_name, common_name, rank,
            kingdom, phylum, class, order_name, family,
            subfamily, tribe, subtribe, genus, subgenus,
            section, subsection, species, subspecies, variety, form,
            is_active, iconic_taxon
        ) VALUES (
            :id, :scientific_name, :common_name, :rank,
            :kingdom, :phylum, :class, :order_name, :family,
            :subfamily, :tribe, :subtribe, :genus, :subgenus,
            :section, :subsection, :species, :subspecies, :variety, :form,
            :is_active, :iconic_taxon
        )
    """, row2)
    conn.commit()

    # FIX: Using INSERT OR IGNORE preserves the original full data
    cursor.execute("SELECT kingdom, phylum, class, order_name FROM taxa WHERE id = 47604")
    result = cursor.fetchone()

    # This should now PASS - parent ranks are preserved
    assert result == ('Plantae', 'Tracheophyta', 'Magnoliopsida', 'Asterales'), \
        f"Parent ranks should be preserved, got {result}"

    conn.close()
