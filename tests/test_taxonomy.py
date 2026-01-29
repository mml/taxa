"""Tests for taxonomy constants and utilities."""
from taxa.taxonomy import TAXONOMIC_RANKS, get_next_ranks, sort_ranks


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


def test_get_next_ranks_single():
    """Test getting next single rank in hierarchy."""
    assert get_next_ranks('family') == ['subfamily']
    assert get_next_ranks('subfamily') == ['tribe']
    assert get_next_ranks('genus') == ['subgenus']


def test_get_next_ranks_multiple():
    """Test getting multiple next ranks."""
    assert get_next_ranks('family', count=2) == ['subfamily', 'tribe']
    assert get_next_ranks('family', count=3) == ['subfamily', 'tribe', 'subtribe']


def test_get_next_ranks_at_end():
    """Test getting next ranks when near end of hierarchy."""
    # 'form' is last rank, should return empty list
    assert get_next_ranks('form', count=1) == []

    # 'variety' has only 1 rank after it
    assert get_next_ranks('variety', count=2) == ['form']


def test_sort_ranks_already_sorted():
    """Test sorting ranks that are already in order."""
    ranks = ['family', 'subfamily', 'tribe', 'genus']
    assert sort_ranks(ranks) == ['family', 'subfamily', 'tribe', 'genus']


def test_sort_ranks_reverse_order():
    """Test sorting ranks in reverse order."""
    ranks = ['genus', 'tribe', 'subfamily']
    assert sort_ranks(ranks) == ['subfamily', 'tribe', 'genus']


def test_sort_ranks_mixed_order():
    """Test sorting ranks in random order."""
    ranks = ['genus', 'family', 'species', 'tribe']
    assert sort_ranks(ranks) == ['family', 'tribe', 'genus', 'species']


def test_sort_ranks_single():
    """Test sorting single rank."""
    assert sort_ranks(['genus']) == ['genus']


def test_validate_rank_sequence_valid():
    """Test validating correct rank sequences."""
    from taxa.taxonomy import validate_rank_sequence

    # Valid sequences should not raise
    validate_rank_sequence('family', ['subfamily', 'tribe'])
    validate_rank_sequence('family', ['genus'])
    validate_rank_sequence('genus', ['species', 'subspecies'])


def test_validate_rank_sequence_invalid_higher():
    """Test that higher ranks are rejected."""
    import pytest
    from taxa.taxonomy import validate_rank_sequence

    with pytest.raises(ValueError, match="not below"):
        validate_rank_sequence('family', ['kingdom'])

    with pytest.raises(ValueError, match="not below"):
        validate_rank_sequence('genus', ['family'])


def test_validate_rank_sequence_invalid_same():
    """Test that same rank is rejected."""
    import pytest
    from taxa.taxonomy import validate_rank_sequence

    with pytest.raises(ValueError, match="not below"):
        validate_rank_sequence('family', ['family'])


def test_validate_rank_sequence_mixed_valid_invalid():
    """Test mixed valid and invalid ranks."""
    import pytest
    from taxa.taxonomy import validate_rank_sequence

    with pytest.raises(ValueError, match="not below"):
        validate_rank_sequence('family', ['subfamily', 'kingdom'])
