"""Batch fetching utilities for iNaturalist API."""
from typing import List, Dict, Any, Callable, Optional
from pyinaturalist import get_taxa_by_id

from taxa.retry import with_retry


def fetch_taxa_batch(
    taxon_ids: List[int],
    batch_size: int = 30,
    callback: Optional[Callable[[int, int], None]] = None
) -> List[Dict[str, Any]]:
    """
    Fetch multiple taxa by ID in batches.

    Uses get_taxa_by_id with multiple IDs per call to reduce API requests.
    iNaturalist API supports fetching multiple taxa in a single request.

    Args:
        taxon_ids: List of iNaturalist taxon IDs to fetch
        batch_size: Number of taxa to fetch per API call (default 30)
        callback: Optional function called after each batch: callback(batch_num, total_batches)

    Returns:
        List of complete taxon dictionaries with full details and ancestors
    """
    all_taxa = []
    total_batches = (len(taxon_ids) + batch_size - 1) // batch_size  # Ceiling division

    for batch_num, i in enumerate(range(0, len(taxon_ids), batch_size), start=1):
        batch = taxon_ids[i:i+batch_size]

        response = with_retry(get_taxa_by_id, batch)
        taxa = response.get('results', [])
        all_taxa.extend(taxa)

        if callback:
            callback(batch_num, total_batches)

    return all_taxa
