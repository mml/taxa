"""Fetch taxonomic data from iNaturalist API."""
from typing import Iterator, Dict, Any, Optional
from pyinaturalist import get_taxa


# iNaturalist API limit: 10,000 results per search
MAX_RESULTS_PER_SEARCH = 10000


def fetch_taxon_descendants(
    taxon_id: int,
    per_page: int = 200,
    max_results: Optional[int] = None
) -> Iterator[Dict[str, Any]]:
    """
    Fetch all descendant taxa for a given taxon ID.

    Handles iNaturalist's 10,000 result limit by using id_above parameter
    to paginate through large result sets.

    Args:
        taxon_id: iNaturalist taxon ID
        per_page: Results per API call (max 200)
        max_results: Maximum total results to fetch (None = all)

    Yields:
        Taxon dictionaries from API
    """
    total_fetched = 0
    id_above = None

    while True:
        page = 1
        batch_count = 0

        # Fetch up to 10k results in this batch
        while batch_count < MAX_RESULTS_PER_SEARCH:
            params = {
                'taxon_id': taxon_id,
                'per_page': per_page,
                'page': page
            }

            if id_above is not None:
                params['id_above'] = id_above

            response = get_taxa(**params)
            results = response.get('results', [])

            if not results:
                # No more results
                return

            for taxon in results:
                yield taxon
                total_fetched += 1
                batch_count += 1

                if max_results and total_fetched >= max_results:
                    return

            page += 1

            # Check if result set is incomplete (fewer than per_page items returned).
            # This indicates we've reached the end of the dataset.
            if len(results) < per_page:
                return

            # Also check total_results, but only when it's reliably below the API limit
            # (if total_results == 10000, it may be capped by the API's search limit)
            total_results = response.get('total_results', 0)
            if total_results > 0 and total_results < MAX_RESULTS_PER_SEARCH:
                if total_fetched >= total_results:
                    return

            # Break before hitting exactly 10k results to leave room for one more page
            # (prevents exceeding the API's 10,000 result limit)
            if batch_count >= MAX_RESULTS_PER_SEARCH - per_page:
                break

        # Note: Assumes API returns results in ascending ID order, allowing us to use
        # the max ID from the final page as the starting point for the next batch
        if results:
            id_above = max(taxon['id'] for taxon in results)
        else:
            break
