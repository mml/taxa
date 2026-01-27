from taxa.observations import fetch_observation_summary
from unittest.mock import patch, Mock


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


def test_fetch_observation_summary_no_results():
    """Test handling when API returns no results."""
    with patch('taxa.observations.get_observation_species_counts') as mock_counts:
        mock_counts.return_value = {'results': []}

        result = fetch_observation_summary(47125, 14, 'research')
        assert result is None


def test_fetch_observation_summary_histogram_parsing():
    """Test that histogram data is correctly parsed."""
    with patch('taxa.observations.get_observation_species_counts') as mock_counts, \
         patch('taxa.observations.get_observation_histogram') as mock_hist:

        mock_counts.return_value = {
            'results': [{'taxon': {'id': 123}, 'count': 50}]
        }
        mock_hist.return_value = {
            'results': {'month_of_year': {'1': 5, '6': 10, '12': 3}}
        }

        result = fetch_observation_summary(47125, 14)

        # Test actual parsing logic
        assert result['first_observed'] == "Month 1"
        assert result['last_observed'] == "Month 12"


def test_fetch_observation_summary_histogram_failure():
    """Test graceful handling when histogram call fails."""
    with patch('taxa.observations.get_observation_species_counts') as mock_counts, \
         patch('taxa.observations.get_observation_histogram') as mock_hist:

        mock_counts.return_value = {
            'results': [{'taxon': {'id': 123}, 'count': 50}]
        }
        mock_hist.side_effect = KeyError("bad data")

        result = fetch_observation_summary(47125, 14)
        assert result['first_observed'] is None
        assert result['last_observed'] is None


def test_fetch_observation_summary_retries_on_429():
    """Test that 429 errors are retried."""
    error_429 = Exception("429 Client Error: Too Many Requests")

    with patch('taxa.observations.get_observation_species_counts') as mock_counts:
        mock_counts.side_effect = [
            error_429,
            {
                'results': [
                    {'taxon': {'id': 123}, 'count': 50}
                ]
            }
        ]

        with patch('taxa.observations.get_observation_histogram') as mock_hist:
            mock_hist.return_value = {'results': {}}

            with patch('time.sleep'):  # Don't actually sleep in tests
                result = fetch_observation_summary(
                    taxon_id=47125,
                    place_id=14
                )

        assert result is not None
        assert result['taxon_id'] == 123
        assert mock_counts.call_count == 2  # Failed once, succeeded once
