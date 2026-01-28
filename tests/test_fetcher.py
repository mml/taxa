from taxa.fetcher import fetch_taxon_descendants, fetch_regional_taxa
from unittest.mock import Mock, patch


def test_fetch_taxon_descendants_calls_api():
    """Test that fetch_taxon_descendants makes correct API call."""
    with patch('taxa.fetcher.get_taxa') as mock_get_taxa:
        mock_get_taxa.return_value = {
            'total_results': 1,
            'results': [
                {'id': 1, 'name': 'Test Species', 'rank': 'species'}
            ]
        }

        results = list(fetch_taxon_descendants(taxon_id=47125, per_page=1))

        mock_get_taxa.assert_called_once()
        assert len(results) == 1
        assert results[0]['id'] == 1


def test_fetch_taxon_descendants_handles_pagination():
    """Test that function handles paginated responses."""
    with patch('taxa.fetcher.get_taxa') as mock_get_taxa:
        # Simulate two pages
        mock_get_taxa.side_effect = [
            {
                'total_results': 3,
                'results': [
                    {'id': 1, 'name': 'Species 1', 'rank': 'species'},
                    {'id': 2, 'name': 'Species 2', 'rank': 'species'},
                ]
            },
            {
                'total_results': 3,
                'results': [
                    {'id': 3, 'name': 'Species 3', 'rank': 'species'},
                ]
            }
        ]

        results = list(fetch_taxon_descendants(taxon_id=47125, per_page=2))

        assert len(results) == 3
        assert results[0]['id'] == 1
        assert results[2]['id'] == 3


def test_fetch_taxon_descendants_uses_id_above_for_large_sets():
    """Test that fetcher uses id_above to handle >10k results."""
    with patch('taxa.fetcher.get_taxa') as mock_get_taxa:
        # Simulate hitting the 10k limit, then using id_above
        mock_get_taxa.side_effect = [
            # First batch (pages 1-50)
            {
                'total_results': 20000,
                'results': [{'id': i, 'name': f'Species {i}'} for i in range(1, 201)]
            },
            # More pages until we hit 10k
            *[{
                'total_results': 20000,
                'results': [{'id': i, 'name': f'Species {i}'} for i in range(j*200+1, j*200+201)]
            } for j in range(1, 49)],
            # Last page before limit
            {
                'total_results': 20000,
                'results': [{'id': i, 'name': f'Species {i}'} for i in range(9801, 10001)]
            },
            # Now use id_above=10000
            {
                'total_results': 20000,
                'results': [{'id': i, 'name': f'Species {i}'} for i in range(10001, 10201)]
            },
            # Continue with id_above
            *[{
                'total_results': 20000,
                'results': [{'id': i, 'name': f'Species {i}'} for i in range(j*200+1, min(j*200+201, 20001))]
            } for j in range(51, 100)],
            # Final response: empty results to signal end of data
            {
                'total_results': 20000,
                'results': []
            }
        ]

        results = list(fetch_taxon_descendants(taxon_id=47125, per_page=200))

        # Verify we got all results across the pagination boundary
        assert len(results) == 20000
        # Check that id_above was used in calls after the 50th page
        call_args_list = mock_get_taxa.call_args_list
        # After 50 pages (10k results), should start using id_above
        assert any('id_above' in str(call) for call in call_args_list[50:])


def test_fetch_taxon_descendants_retries_on_network_error():
    """Test that network errors are retried."""
    with patch('taxa.fetcher.get_taxa') as mock_get_taxa:
        mock_get_taxa.side_effect = [
            ConnectionError("Network error"),
            {
                'total_results': 1,
                'results': [
                    {'id': 1, 'name': 'Test Species', 'rank': 'species'}
                ]
            }
        ]

        with patch('time.sleep'):  # Don't actually sleep in tests
            results = list(fetch_taxon_descendants(taxon_id=47125, per_page=1))

        assert len(results) == 1
        assert mock_get_taxa.call_count == 2  # Failed once, succeeded once


def test_fetch_regional_taxa_single_page():
    """Test fetching regional taxa with results in one page."""
    with patch('taxa.fetcher.with_retry') as mock_retry:
        # Mock response with < 200 results
        mock_retry.return_value = {
            'results': [
                {
                    'id': 123,
                    'name': 'Malus domestica',
                    'rank': 'species',
                    'descendant_obs_count': 50,
                    'direct_obs_count': 50
                },
                {
                    'id': 456,
                    'name': 'Prunus avium',
                    'rank': 'species',
                    'descendant_obs_count': 30,
                    'direct_obs_count': 30
                }
            ]
        }

        result = fetch_regional_taxa(
            taxon_id=922110,
            place_id=2764,
            quality_grade='research'
        )

        # Should return all taxa
        assert len(result) == 2
        assert result[0]['id'] == 123
        assert result[1]['id'] == 456

        # Should have called API once
        assert mock_retry.call_count == 1


def test_fetch_regional_taxa_pagination():
    """Test pagination when results span multiple pages."""
    with patch('taxa.fetcher.with_retry') as mock_retry:
        # Mock two pages of results (full page size = 200)
        mock_retry.side_effect = [
            {
                'results': [{'id': i, 'name': f'Taxon {i}'} for i in range(200)]
            },
            {
                'results': [{'id': i, 'name': f'Taxon {i}'} for i in range(200, 250)]
            }
        ]

        result = fetch_regional_taxa(taxon_id=922110, place_id=2764)

        # Should return all taxa from both pages
        assert len(result) == 250

        # Should have called API 2 times (second page has < 200 results, so we stop)
        assert mock_retry.call_count == 2


def test_fetch_regional_taxa_empty():
    """Test handling when no taxa have observations in region."""
    with patch('taxa.fetcher.with_retry') as mock_retry:
        mock_retry.return_value = {'results': []}

        result = fetch_regional_taxa(taxon_id=999999, place_id=2764)

        # Should return empty list
        assert result == []

        # Should have called API once
        assert mock_retry.call_count == 1
