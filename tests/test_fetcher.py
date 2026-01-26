from taxa.fetcher import fetch_taxon_descendants
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
