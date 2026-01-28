from unittest.mock import patch
from taxa.batch import fetch_taxa_batch


def test_fetch_taxa_batch_single_batch():
    """Test fetching small number of taxa in one batch."""
    with patch('taxa.batch.with_retry') as mock_retry:
        mock_retry.return_value = {
            'results': [
                {'id': 1, 'name': 'Taxon 1', 'ancestors': []},
                {'id': 2, 'name': 'Taxon 2', 'ancestors': []},
                {'id': 3, 'name': 'Taxon 3', 'ancestors': []}
            ]
        }

        result = fetch_taxa_batch([1, 2, 3])

        # Should return all taxa
        assert len(result) == 3
        assert result[0]['id'] == 1

        # Should have called API once with list of IDs
        assert mock_retry.call_count == 1
        call_args = mock_retry.call_args[0]
        assert call_args[1] == [1, 2, 3]


def test_fetch_taxa_batch_multiple_batches():
    """Test batching when taxa count exceeds batch size."""
    with patch('taxa.batch.with_retry') as mock_retry:
        # Mock responses for two batches
        mock_retry.side_effect = [
            {'results': [{'id': i, 'name': f'Taxon {i}'} for i in range(30)]},
            {'results': [{'id': i, 'name': f'Taxon {i}'} for i in range(30, 35)]}
        ]

        # Fetch 35 taxa (should be 2 batches of 30)
        taxon_ids = list(range(35))
        result = fetch_taxa_batch(taxon_ids, batch_size=30)

        # Should return all taxa
        assert len(result) == 35

        # Should have called API twice
        assert mock_retry.call_count == 2


def test_fetch_taxa_batch_with_callback():
    """Test progress callback invoked after each batch."""
    with patch('taxa.batch.with_retry') as mock_retry:
        mock_retry.side_effect = [
            {'results': [{'id': i} for i in range(30)]},
            {'results': [{'id': i} for i in range(30, 40)]}
        ]

        batches_completed = []

        def callback(batch_num, total_batches):
            batches_completed.append((batch_num, total_batches))

        result = fetch_taxa_batch(list(range(40)), batch_size=30, callback=callback)

        # Callback should have been called twice
        assert batches_completed == [(1, 2), (2, 2)]
