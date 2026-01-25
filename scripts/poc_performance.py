#!/usr/bin/env python3
"""
Proof-of-concept: Test performance of fetching large taxon in a region.

Usage:
    python scripts/poc_performance.py --taxon-id 47125 --timeout 300

This script validates whether the API fetching approach scales acceptably.
It runs with a timeout and reports progress metrics for extrapolation.
"""
import argparse
import signal
import sys
from taxa.fetcher import fetch_taxon_descendants
from taxa.metrics import MetricsTracker
from pyinaturalist import get_taxa


class TimeoutError(Exception):
    """Raised when timeout is exceeded."""
    pass


def timeout_handler(signum, frame):
    """Handle timeout signal."""
    raise TimeoutError()


def estimate_total_descendants(taxon_id: int) -> int:
    """Make a quick API call to get total descendant count."""
    response = get_taxa(taxon_id=taxon_id, per_page=1)
    return response.get('total_results', 0)


def run_poc(taxon_id: int, timeout_seconds: int) -> None:
    """
    Run proof-of-concept fetch with timeout and progress reporting.

    Args:
        taxon_id: iNaturalist taxon ID to fetch
        timeout_seconds: Timeout in seconds (0 = no timeout)
    """
    print(f"Estimating total descendants for taxon {taxon_id}...")
    total = estimate_total_descendants(taxon_id)
    print(f"Estimated total: {total:,} taxa\n")

    if total == 0:
        print("ERROR: No descendants found. Check taxon ID.")
        sys.exit(1)

    tracker = MetricsTracker(total_items=total)

    # Set up timeout if specified
    if timeout_seconds > 0:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        print(f"Running with {timeout_seconds}s timeout...\n")
    else:
        print("Running without timeout (Ctrl+C to abort)...\n")

    try:
        for taxon in fetch_taxon_descendants(taxon_id):
            tracker.increment_processed()

            # Track API calls (approximately 1 per page of 200)
            if tracker.processed % 200 == 0:
                tracker.increment_api_calls()

            # Print progress every 100 taxa
            if tracker.processed % 100 == 0:
                print(f"Progress: {tracker.processed:,} / {total:,} taxa...")

        # Completed successfully
        if timeout_seconds > 0:
            signal.alarm(0)  # Cancel timeout

        print("\n" + "="*60)
        print("COMPLETED SUCCESSFULLY")
        print("="*60)
        print(tracker.format_report())

    except (TimeoutError, KeyboardInterrupt):
        # Timeout or user interrupt
        if timeout_seconds > 0:
            signal.alarm(0)  # Cancel timeout

        print("\n" + "="*60)
        print("INTERRUPTED - PERFORMANCE ESTIMATE")
        print("="*60)
        print(tracker.format_report())
        print("\nConclusion:")

        est_time = tracker.estimate_completion_time()
        if est_time:
            hours = est_time / 3600
            if hours > 2:
                print(f"  ⚠️  Full sync would take ~{hours:.1f} hours")
                print("  Consider revising approach:")
                print("    - Fetch at higher taxonomic levels")
                print("    - Use bulk taxonomy export + aggregate observations only")
                print("    - Batch requests differently")
            elif hours > 0.5:
                print(f"  ⚠️  Full sync would take ~{hours*60:.0f} minutes")
                print("  Acceptable but slow. Consider optimizations.")
            else:
                print(f"  ✓ Full sync would take ~{hours*60:.0f} minutes")
                print("  Performance looks acceptable.")


def main():
    parser = argparse.ArgumentParser(
        description="Proof-of-concept: Test API fetch performance"
    )
    parser.add_argument(
        '--taxon-id',
        type=int,
        required=True,
        help='iNaturalist taxon ID to test (e.g., 47125 for Rosaceae)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Timeout in seconds (default: 300, 0 = no timeout)'
    )

    args = parser.parse_args()

    print("="*60)
    print("TAXA PROOF-OF-CONCEPT PERFORMANCE TEST")
    print("="*60)
    print()

    run_poc(args.taxon_id, args.timeout)


if __name__ == '__main__':
    main()
