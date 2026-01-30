"""Output formatting for taxa commands."""
import sys


def detect_format():
    """Detect appropriate output format based on stdout.

    Returns:
        str: 'table' if stdout is a TTY, 'csv' otherwise
    """
    return 'table' if sys.stdout.isatty() else 'csv'
