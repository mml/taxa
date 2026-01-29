"""Taxonomic hierarchy constants and utilities."""

# Taxonomic ranks in hierarchical order (highest to lowest)
TAXONOMIC_RANKS = [
    'kingdom',
    'phylum',
    'class',
    'order_name',  # 'order' is SQL keyword
    'family',
    'subfamily',
    'tribe',
    'subtribe',
    'genus',
    'subgenus',
    'section',
    'subsection',
    'species',
    'subspecies',
    'variety',
    'form'
]


def get_next_ranks(current_rank, count=1):
    """Get the next N ranks in hierarchy after current_rank.

    Args:
        current_rank: Current taxonomic rank
        count: Number of ranks to return (default 1)

    Returns:
        List of next N rank names, may be shorter if near end of hierarchy

    Raises:
        ValueError: If current_rank not in TAXONOMIC_RANKS
    """
    if current_rank not in TAXONOMIC_RANKS:
        raise ValueError(f"Unknown rank: {current_rank}")

    idx = TAXONOMIC_RANKS.index(current_rank)
    return TAXONOMIC_RANKS[idx+1:idx+1+count]


def sort_ranks(ranks):
    """Sort ranks by hierarchical order.

    Args:
        ranks: List of rank names to sort

    Returns:
        List of ranks sorted from highest to lowest in hierarchy

    Raises:
        ValueError: If any rank is not in TAXONOMIC_RANKS
    """
    for rank in ranks:
        if rank not in TAXONOMIC_RANKS:
            raise ValueError(f"Unknown rank: {rank}")

    return sorted(ranks, key=lambda r: TAXONOMIC_RANKS.index(r))


def validate_rank_sequence(base_rank, requested_ranks):
    """Validate that requested ranks are all below base_rank in hierarchy.

    Args:
        base_rank: Starting rank
        requested_ranks: List of ranks to validate

    Returns:
        True if all ranks are valid

    Raises:
        ValueError: If any requested rank is not below base_rank
    """
    if base_rank not in TAXONOMIC_RANKS:
        raise ValueError(f"Unknown rank: {base_rank}")

    base_idx = TAXONOMIC_RANKS.index(base_rank)

    for rank in requested_ranks:
        if rank not in TAXONOMIC_RANKS:
            raise ValueError(f"Unknown rank: {rank}")

        rank_idx = TAXONOMIC_RANKS.index(rank)
        if rank_idx <= base_idx:
            raise ValueError(
                f"Cannot break down to '{rank}' - it's not below '{base_rank}'"
            )

    return True
