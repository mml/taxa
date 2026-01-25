"""Fetch taxonomic data from iNaturalist API."""
from typing import Iterator, Dict, Any
from pyinaturalist import get_taxa


def fetch_taxon_descendants(
    taxon_id: int,
    per_page: int = 200,
    max_results: int = None
) -> Iterator[Dict[str, Any]]:
    """
    Fetch all descendant taxa for a given taxon ID.

    Args:
        taxon_id: iNaturalist taxon ID
        per_page: Results per API call (max 200)
        max_results: Maximum total results to fetch (None = all)

    Yields:
        Taxon dictionaries from API
    """
    page = 1
    total_fetched = 0

    while True:
        response = get_taxa(
            taxon_id=taxon_id,
            per_page=per_page,
            page=page
        )

        results = response.get('results', [])
        if not results:
            break

        for taxon in results:
            yield taxon
            total_fetched += 1

            if max_results and total_fetched >= max_results:
                return

        # Check if we've fetched all available results
        total_results = response.get('total_results', 0)
        if total_fetched >= total_results:
            break

        page += 1
