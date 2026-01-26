"""Transform iNaturalist API responses into database rows."""
from typing import Dict, Any


# All taxonomic ranks we might encounter
RANK_COLUMNS = [
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
    'form',
]


def flatten_taxon_ancestry(taxon: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten taxon with ancestry into wide table row.

    Extracts all taxonomic ranks from the taxon's ancestry chain
    and creates a dictionary suitable for database insertion.

    Args:
        taxon: Taxon dict from iNaturalist API with 'ancestors' key

    Returns:
        Dictionary with id, scientific_name, rank, and all rank columns
    """
    row = {
        'id': taxon['id'],
        'scientific_name': taxon['name'],
        'rank': taxon['rank'],
        'common_name': taxon.get('preferred_common_name'),
        'is_active': taxon.get('is_active', True),
        'iconic_taxon': taxon.get('iconic_taxon_name'),
    }

    # Initialize all rank columns to None
    for rank_col in RANK_COLUMNS:
        row[rank_col] = None

    # Fill in ranks from ancestors
    ancestors = taxon.get('ancestors', [])
    for ancestor in ancestors:
        rank = ancestor['rank']
        name = ancestor['name']

        # Map rank to column name (handle 'order' -> 'order_name')
        col_name = 'order_name' if rank == 'order' else rank

        if col_name in RANK_COLUMNS:
            row[col_name] = name

    # Add self to appropriate rank column
    self_rank = taxon['rank']
    self_col = 'order_name' if self_rank == 'order' else self_rank

    if self_col in RANK_COLUMNS:
        row[self_col] = taxon['name']

    return row
