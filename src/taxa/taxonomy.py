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
