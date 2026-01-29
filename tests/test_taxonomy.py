"""Tests for taxonomy constants and utilities."""
from taxa.taxonomy import TAXONOMIC_RANKS


def test_taxonomic_ranks_exists():
    """Test that TAXONOMIC_RANKS is defined and has expected structure."""
    assert isinstance(TAXONOMIC_RANKS, list)
    assert len(TAXONOMIC_RANKS) > 0


def test_taxonomic_ranks_order():
    """Test that ranks are in correct hierarchical order."""
    expected_order = [
        'kingdom', 'phylum', 'class', 'order_name', 'family',
        'subfamily', 'tribe', 'subtribe', 'genus', 'subgenus',
        'section', 'subsection', 'species', 'subspecies', 'variety', 'form'
    ]
    assert TAXONOMIC_RANKS == expected_order
