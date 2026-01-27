"""Fetch observation data from iNaturalist API."""
from typing import Dict, Any, Optional
from pyinaturalist import get_observation_species_counts, get_observation_histogram
from requests.exceptions import RequestException

from taxa.retry import with_retry


def fetch_observation_summary(
    taxon_id: int,
    place_id: int,
    quality_grade: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch aggregated observation data for a taxon in a place.

    Uses retry logic to handle rate limits and network errors.

    Args:
        taxon_id: iNaturalist taxon ID
        place_id: iNaturalist place ID
        quality_grade: Filter by quality (research, needs_id, casual, or None)

    Returns:
        Dictionary with observation_count, observer_count, date ranges
    """
    params = {
        'taxon_id': taxon_id,
        'place_id': place_id,
    }

    if quality_grade:
        params['quality_grade'] = quality_grade

    # Get species counts (includes observation counts) with retry
    counts_response = with_retry(
        get_observation_species_counts,
        **params
    )

    if not counts_response.get('results'):
        return None

    # Take first result (should be the taxon itself)
    result = counts_response['results'][0]

    summary = {
        'taxon_id': result['taxon']['id'],
        'observation_count': result['count'],
        'observer_count': None,  # Not available in this endpoint
        'research_grade_count': None,  # Would need separate call
        'first_observed': None,
        'last_observed': None,
    }

    # Get histogram for date range with retry
    try:
        hist_response = with_retry(
            get_observation_histogram,
            date_field='observed',
            **params
        )

        # Extract date range from histogram
        # Histogram returns month_of_year or other intervals
        if hist_response.get('results'):
            histogram = hist_response['results']

            # Try to get month_of_year data to determine first and last observed
            if 'month_of_year' in histogram:
                months = histogram['month_of_year']
                if months:
                    # Find first and last months with observations
                    month_nums = sorted([int(m) for m in months.keys() if months[m] > 0])
                    if month_nums:
                        summary['first_observed'] = f"Month {month_nums[0]}"
                        summary['last_observed'] = f"Month {month_nums[-1]}"
    except (KeyError, ValueError, RequestException):
        # Histogram call might fail, not critical
        pass

    return summary
