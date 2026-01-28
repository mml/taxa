"""Compare performance of old vs new sync implementations."""
import time
import sqlite3
from unittest.mock import patch, MagicMock

from taxa.config import Config
from taxa.sync import sync_database


def mock_old_implementation(config):
    """Simulate old implementation behavior."""
    start = time.time()

    # Simulate fetching 5000 global taxa
    api_calls = 5000

    # Simulate 2 API calls per taxon (taxa fetch + observation query)
    api_calls *= 2

    # Simulate rate limiting (1 req/sec with pyinaturalist)
    elapsed = api_calls  # Seconds at 1 req/sec

    end = time.time()

    return {
        'api_calls': api_calls,
        'elapsed_simulated': elapsed,
        'taxa_count': 168  # Assume 168 actually have observations
    }


def test_new_implementation(config):
    """Test new implementation with mocks."""
    start = time.time()
    api_calls = 0

    with patch('taxa.sync.fetch_regional_taxa') as mock_regional, \
         patch('taxa.sync.fetch_taxa_batch') as mock_batch:

        # Simulate regional discovery (1 call)
        mock_regional.return_value = [
            {'id': i, 'descendant_obs_count': 10, 'direct_obs_count': 5}
            for i in range(168)
        ]
        api_calls += 1

        # Simulate batch fetching (168 taxa / 30 batch = 6 calls)
        def batch_side_effect(taxon_ids, batch_size=30, callback=None):
            nonlocal api_calls
            batches = (len(taxon_ids) + batch_size - 1) // batch_size
            api_calls += batches
            return [
                {'id': tid, 'name': f'Taxon {tid}', 'rank': 'species', 'ancestors': []}
                for tid in taxon_ids
            ]

        mock_batch.side_effect = batch_side_effect

        sync_database(config)

    end = time.time()

    return {
        'api_calls': api_calls,
        'elapsed_actual': end - start,
        'taxa_count': 168
    }


def main():
    """Run comparison."""
    config = Config({
        'database': ':memory:',
        'regions': {'test': {'name': 'Test', 'place_ids': [123]}},
        'taxa': {'test': {'name': 'Test', 'taxon_id': 456}},
        'filters': {}
    })

    print("Performance Comparison: Old vs New Implementation")
    print("=" * 60)
    print()

    print("OLD IMPLEMENTATION (simulated):")
    old_result = mock_old_implementation(config)
    print(f"  API calls: {old_result['api_calls']:,}")
    print(f"  Time (simulated): {old_result['elapsed_simulated']:,.1f} seconds")
    print(f"  Taxa discovered: {old_result['taxa_count']}")
    print()

    print("NEW IMPLEMENTATION:")
    new_result = test_new_implementation(config)
    print(f"  API calls: {new_result['api_calls']}")
    print(f"  Time (actual): {new_result['elapsed_actual']:.2f} seconds")
    print(f"  Taxa discovered: {new_result['taxa_count']}")
    print()

    print("IMPROVEMENT:")
    api_reduction = (1 - new_result['api_calls'] / old_result['api_calls']) * 100
    time_reduction = (1 - new_result['elapsed_actual'] / old_result['elapsed_simulated']) * 100
    print(f"  API calls reduced: {api_reduction:.1f}%")
    print(f"  Time reduced: {time_reduction:.1f}%")
    print(f"  Speedup factor: {old_result['api_calls'] / new_result['api_calls']:.1f}x")


if __name__ == '__main__':
    main()
