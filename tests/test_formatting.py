"""Tests for output formatting module."""
import sys
from taxa.formatting import detect_format, transform_null


def test_detect_format_returns_table_for_tty(mocker):
    """When stdout is a TTY, detect_format returns 'table'."""
    mocker.patch('sys.stdout.isatty', return_value=True)
    assert detect_format() == 'table'


def test_detect_format_returns_csv_for_non_tty(mocker):
    """When stdout is not a TTY, detect_format returns 'csv'."""
    mocker.patch('sys.stdout.isatty', return_value=False)
    assert detect_format() == 'csv'


def test_transform_null_to_empty_string():
    """By default, NULL values become empty strings."""
    assert transform_null(None, show_null=False) == ''


def test_transform_null_preserves_other_values():
    """Non-NULL values are returned unchanged."""
    assert transform_null('foo', show_null=False) == 'foo'
    assert transform_null(42, show_null=False) == 42
    assert transform_null(0, show_null=False) == 0


def test_transform_null_with_show_null_flag():
    """When show_null=True, NULL becomes the string 'NULL'."""
    assert transform_null(None, show_null=True) == 'NULL'


def test_transform_null_preserves_values_with_show_null():
    """When show_null=True, non-NULL values still unchanged."""
    assert transform_null('foo', show_null=True) == 'foo'
