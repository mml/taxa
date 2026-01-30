"""Tests for output formatting module."""
import sys
import io
from taxa.formatting import detect_format, transform_null, format_csv


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


def test_format_csv_basic_output(capsys):
    """CSV formatter outputs RFC 4180 compliant CSV."""
    headers = ['name', 'count']
    rows = [('Alice', 10), ('Bob', 20)]

    format_csv(headers, rows, show_null=False)

    captured = capsys.readouterr()
    assert captured.out == 'name,count\nAlice,10\nBob,20\n'


def test_format_csv_with_null_values(capsys):
    """CSV formatter handles NULL values correctly."""
    headers = ['name', 'count']
    rows = [('Alice', None), (None, 20)]

    format_csv(headers, rows, show_null=False)

    captured = capsys.readouterr()
    assert captured.out == 'name,count\nAlice,\n,20\n'


def test_format_csv_with_show_null_flag(capsys):
    """CSV formatter shows NULL when show_null=True."""
    headers = ['name', 'count']
    rows = [('Alice', None)]

    format_csv(headers, rows, show_null=True)

    captured = capsys.readouterr()
    assert captured.out == 'name,count\nAlice,NULL\n'


def test_format_csv_escapes_values_with_commas(capsys):
    """CSV formatter properly escapes values containing commas."""
    headers = ['name', 'description']
    rows = [('Alice', 'Hello, world')]

    format_csv(headers, rows, show_null=False)

    captured = capsys.readouterr()
    assert captured.out == 'name,description\nAlice,"Hello, world"\n'
