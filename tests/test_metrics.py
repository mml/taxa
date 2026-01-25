from taxa.metrics import MetricsTracker
import pytest
from unittest.mock import patch


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


def test_increment_processed_rejects_negative():
    tracker = MetricsTracker(total_items=100)
    with pytest.raises(ValueError, match="count must be non-negative"):
        tracker.increment_processed(-1)


def test_increment_api_calls_rejects_negative():
    tracker = MetricsTracker(total_items=100)
    with pytest.raises(ValueError, match="count must be non-negative"):
        tracker.increment_api_calls(-5)


@patch("taxa.metrics.time.time")
def test_metrics_tracker_calculates_rate(mock_time):
    mock_time.side_effect = [0.0, 1.0]  # start_time=0, elapsed=1
    tracker = MetricsTracker(total_items=100)
    tracker.increment_processed(10)

    rate = tracker.get_processing_rate()
    assert rate == 10.0


@patch("taxa.metrics.time.time")
def test_metrics_tracker_rate_zero_elapsed_time(mock_time):
    mock_time.return_value = 0.0
    tracker = MetricsTracker(total_items=100)
    tracker.increment_processed(10)

    rate = tracker.get_processing_rate()
    assert rate == 0.0


@patch("taxa.metrics.time.time")
def test_estimate_completion_time_when_complete(mock_time):
    mock_time.side_effect = [0.0, 1.0]
    tracker = MetricsTracker(total_items=100)
    tracker.increment_processed(100)

    estimate = tracker.estimate_completion_time()
    assert estimate == 0.0


@patch("taxa.metrics.time.time")
def test_estimate_completion_time_with_progress(mock_time):
    mock_time.side_effect = [0.0, 1.0]
    tracker = MetricsTracker(total_items=100)
    tracker.increment_processed(10)

    estimate = tracker.estimate_completion_time()
    assert estimate > 0
    assert estimate == 9.0  # 90 remaining items / 10 items per second


def test_get_progress_percent_zero_total_items():
    tracker = MetricsTracker(total_items=0)
    tracker.increment_processed(0)
    assert tracker.get_progress_percent() == 0.0


def test_get_progress_percent_normal_case():
    tracker = MetricsTracker(total_items=100)
    tracker.increment_processed(25)
    assert tracker.get_progress_percent() == 25.0


def test_get_progress_percent_full_progress():
    tracker = MetricsTracker(total_items=100)
    tracker.increment_processed(100)
    assert tracker.get_progress_percent() == 100.0


@patch("taxa.metrics.time.time")
def test_format_report_structure(mock_time):
    mock_time.side_effect = [0.0, 1.0, 1.0, 1.0]
    tracker = MetricsTracker(total_items=100)
    tracker.increment_processed(50)
    tracker.increment_api_calls(10)

    report = tracker.format_report()

    assert isinstance(report, str)
    assert "Progress: 50/100 items (50.0%)" in report
    assert "Rate: 50.00 items/sec" in report
    assert "API calls: 10" in report
    assert "Elapsed: 1.0s" in report
    assert "Est. remaining: 1.0s" in report
