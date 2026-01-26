from taxa.observations import fetch_observation_summary
from unittest.mock import patch


def test_fetch_observation_summary():
    """Test fetching aggregated observation data."""
    with patch('taxa.observations.get_observation_species_counts') as mock_counts, \
         patch('taxa.observations.get_observation_histogram') as mock_hist:

        mock_counts.return_value = {
            'results': [
                {
                    'taxon': {'id': 123},
                    'count': 50
                }
            ]
        }

        mock_hist.return_value = {
            'results': {
                'month_of_year': {
                    '1': 5,
                    '2': 10,
                    '12': 3
                }
            }
        }

        result = fetch_observation_summary(
            taxon_id=47125,
            place_id=14,
            quality_grade='research'
        )

        assert result['taxon_id'] == 123
        assert result['observation_count'] == 50
        assert result['first_observed'] is not None
        assert result['last_observed'] is not None
