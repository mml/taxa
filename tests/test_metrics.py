from taxa.metrics import MetricsTracker
import time


def test_metrics_tracker_initialization():
    tracker = MetricsTracker(total_items=100)
    assert tracker.total_items == 100
    assert tracker.processed == 0
    assert tracker.api_calls == 0


def test_metrics_tracker_increments():
    tracker = MetricsTracker(total_items=100)
    tracker.increment_processed(5)
    tracker.increment_api_calls(2)

    assert tracker.processed == 5
    assert tracker.api_calls == 2


def test_metrics_tracker_calculates_rate():
    tracker = MetricsTracker(total_items=100)
    tracker.increment_processed(10)
    time.sleep(0.1)

    rate = tracker.get_processing_rate()
    assert rate > 0


def test_metrics_tracker_estimates_completion():
    tracker = MetricsTracker(total_items=100)
    tracker.increment_processed(10)
    time.sleep(0.1)

    estimate = tracker.estimate_completion_time()
    assert estimate > 0
