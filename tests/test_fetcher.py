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
