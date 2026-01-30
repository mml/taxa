"""Output formatting for taxa commands."""
import sys


def detect_format():
    """Detect appropriate output format based on stdout.

    Returns:
        str: 'table' if stdout is a TTY, 'csv' otherwise
    """
    return 'table' if sys.stdout.isatty() else 'csv'


def transform_null(value, show_null=False):
    """Transform NULL values for display.

    Args:
        value: The value to transform (may be None)
        show_null: If True, render None as 'NULL'; if False, render as ''

    Returns:
        The transformed value
    """
    if value is None:
        return 'NULL' if show_null else ''
    return value
