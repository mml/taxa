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


def _rank_to_column_name(rank: str) -> str:
    """Convert rank name to database column name.

    Args:
        rank: Taxonomic rank name

    Returns:
        Column name for the rank, with 'order' mapped to 'order_name'
    """
    return 'order_name' if rank == 'order' else rank


def flatten_taxon_ancestry(taxon: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten taxon with ancestry into wide table row.

    Extracts all taxonomic ranks from the taxon's ancestry chain
    and creates a dictionary suitable for database insertion.

    Args:
        taxon: Taxon dict from iNaturalist API with 'ancestors' key

    Returns:
        Dictionary with id, scientific_name, rank, and all rank columns

    Raises:
        ValueError: If taxon is missing required fields (id, name, rank)
    """
    # Validate required fields
    required_fields = ['id', 'name', 'rank']
    missing = [f for f in required_fields if f not in taxon]
    if missing:
        raise ValueError(f"Taxon missing required fields: {', '.join(missing)}")

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
        # Skip malformed ancestors
        if 'rank' not in ancestor or 'name' not in ancestor:
            continue

        rank = ancestor['rank']
        name = ancestor['name']

        # Map rank to column name (handle 'order' -> 'order_name')
        col_name = _rank_to_column_name(rank)

        if col_name in RANK_COLUMNS:
            row[col_name] = name

    # Add self to appropriate rank column
    self_rank = taxon['rank']
    self_col = _rank_to_column_name(self_rank)

    if self_col in RANK_COLUMNS:
        row[self_col] = taxon['name']

    return row
