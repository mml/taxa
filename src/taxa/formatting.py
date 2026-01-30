"""Output formatting for taxa commands."""
import sys
import csv


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


def format_csv(headers, rows, show_null=False):
    """Format results as CSV output to stdout.

    Args:
        headers: List of column header strings
        rows: List of tuples containing row data
        show_null: If True, render None as 'NULL'; if False, render as ''
    """
    writer = csv.writer(
        sys.stdout,
        delimiter=',',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator='\n'
    )

    writer.writerow(headers)
    for row in rows:
        transformed_row = [transform_null(val, show_null) for val in row]
        writer.writerow(transformed_row)
