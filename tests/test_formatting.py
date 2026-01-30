"""Tests for output formatting module."""
import sys
from taxa.formatting import detect_format


def test_detect_format_returns_table_for_tty(mocker):
    """When stdout is a TTY, detect_format returns 'table'."""
    mocker.patch('sys.stdout.isatty', return_value=True)
    assert detect_format() == 'table'


def test_detect_format_returns_csv_for_non_tty(mocker):
    """When stdout is not a TTY, detect_format returns 'csv'."""
    mocker.patch('sys.stdout.isatty', return_value=False)
    assert detect_format() == 'csv'
