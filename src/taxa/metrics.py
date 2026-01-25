import time


class MetricsTracker:
    """Tracks metrics for progress monitoring during API data fetching."""

    def __init__(self, total_items: int):
        """Initialize the metrics tracker.

        Args:
            total_items: Total number of items expected to be processed
        """
        self.total_items = total_items
        self.processed = 0
        self.api_calls = 0
        self.start_time = time.time()

    def increment_processed(self, count: int = 1) -> None:
        """Increment the processed items counter.

        Args:
            count: Number of items to add (default: 1)

        Raises:
            ValueError: If count is negative
        """
        if count < 0:
            raise ValueError(f"count must be non-negative, got {count}")
        self.processed += count

    def increment_api_calls(self, count: int = 1) -> None:
        """Increment the API calls counter.

        Args:
            count: Number of API calls to add (default: 1)

        Raises:
            ValueError: If count is negative
        """
        if count < 0:
            raise ValueError(f"count must be non-negative, got {count}")
        self.api_calls += count

    def get_processing_rate(self) -> float:
        """Calculate the current processing rate in items per second.

        Returns:
            Items processed per second
        """
        elapsed_time = time.time() - self.start_time
        if elapsed_time == 0:
            return 0.0
        return self.processed / elapsed_time

    def estimate_completion_time(self) -> float:
        """Estimate remaining time to completion in seconds.

        Returns:
            Estimated seconds remaining to process all items
        """
        rate = self.get_processing_rate()
        if rate == 0:
            return 0.0
        remaining_items = self.total_items - self.processed
        return remaining_items / rate

    def get_progress_percent(self) -> float:
        """Calculate progress as a percentage.

        Returns:
            Percentage of items processed (0-100)
        """
        if self.total_items == 0:
            return 0.0
        return (self.processed / self.total_items) * 100

    def format_report(self) -> str:
        """Format a human-readable progress report.

        Returns:
            Formatted string with progress metrics
        """
        elapsed = time.time() - self.start_time
        rate = self.get_processing_rate()
        estimate = self.estimate_completion_time()
        progress = self.get_progress_percent()

        return (
            f"Progress: {self.processed}/{self.total_items} items ({progress:.1f}%) | "
            f"Rate: {rate:.2f} items/sec | "
            f"API calls: {self.api_calls} | "
            f"Elapsed: {elapsed:.1f}s | "
            f"Est. remaining: {estimate:.1f}s"
        )
