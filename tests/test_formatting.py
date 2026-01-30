"""Tests for output formatting module."""
import sys
import io
from unittest.mock import Mock
from taxa.formatting import detect_format, transform_null, format_csv, format_table, output_results


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


def test_format_table_creates_table_with_headers(mocker):
    """Table formatter creates table with correct headers."""
    mock_console = Mock()
    mock_table_class = Mock()
    mock_table = Mock()
    mock_table_class.return_value = mock_table

    mocker.patch('taxa.formatting.Console', return_value=mock_console)
    mocker.patch('taxa.formatting.Table', mock_table_class)

    headers = ['name', 'count']
    rows = [('Alice', 10)]

    format_table(headers, rows, show_null=False)

    # Verify Table was created with correct config
    mock_table_class.assert_called_once()
    call_kwargs = mock_table_class.call_args[1]
    assert call_kwargs['show_header'] is True
    assert call_kwargs['header_style'] == 'bold'
    assert call_kwargs['show_lines'] is False

    # Verify columns were added
    assert mock_table.add_column.call_count == 2
    mock_table.add_column.assert_any_call('name')
    mock_table.add_column.assert_any_call('count', justify='right')


def test_format_table_adds_rows_with_null_handling(mocker):
    """Table formatter adds rows with NULL transformation."""
    mock_console = Mock()
    mock_table = Mock()
    mocker.patch('taxa.formatting.Console', return_value=mock_console)
    mocker.patch('taxa.formatting.Table', return_value=mock_table)

    headers = ['name', 'count']
    rows = [('Alice', None), (None, 20)]

    format_table(headers, rows, show_null=False)

    # Verify rows were added with transformed NULLs
    assert mock_table.add_row.call_count == 2
    mock_table.add_row.assert_any_call('Alice', '')
    mock_table.add_row.assert_any_call('', '20')


def test_format_table_prints_to_console(mocker):
    """Table formatter prints table via console."""
    mock_console = Mock()
    mock_table = Mock()
    mocker.patch('taxa.formatting.Console', return_value=mock_console)
    mocker.patch('taxa.formatting.Table', return_value=mock_table)

    headers = ['name']
    rows = [('Alice',)]

    format_table(headers, rows, show_null=False)

    mock_console.print.assert_called_once_with(mock_table)


def test_output_results_with_auto_format_tty(mocker):
    """output_results uses table format for TTY."""
    mock_format_table = mocker.patch('taxa.formatting.format_table')
    mocker.patch('sys.stdout.isatty', return_value=True)

    headers = ['name']
    rows = [('Alice',)]

    output_results(headers, rows, format='auto', show_null=False)

    mock_format_table.assert_called_once_with(headers, rows, show_null=False)


def test_output_results_with_auto_format_pipe(mocker):
    """output_results uses CSV format for pipes."""
    mock_format_csv = mocker.patch('taxa.formatting.format_csv')
    mocker.patch('sys.stdout.isatty', return_value=False)

    headers = ['name']
    rows = [('Alice',)]

    output_results(headers, rows, format='auto', show_null=False)

    mock_format_csv.assert_called_once_with(headers, rows, show_null=False)


def test_output_results_with_explicit_table_format(mocker):
    """output_results respects explicit table format."""
    mock_format_table = mocker.patch('taxa.formatting.format_table')
    mocker.patch('sys.stdout.isatty', return_value=False)  # Even when piped

    headers = ['name']
    rows = [('Alice',)]

    output_results(headers, rows, format='table', show_null=True)

    mock_format_table.assert_called_once_with(headers, rows, show_null=True)


def test_output_results_with_explicit_csv_format(mocker):
    """output_results respects explicit CSV format."""
    mock_format_csv = mocker.patch('taxa.formatting.format_csv')
    mocker.patch('sys.stdout.isatty', return_value=True)  # Even in TTY

    headers = ['name']
    rows = [('Alice',)]

    output_results(headers, rows, format='csv', show_null=False)

    mock_format_csv.assert_called_once_with(headers, rows, show_null=False)


def test_output_results_invalid_format_raises_error():
    """output_results raises ValueError for invalid format."""
    import pytest

    with pytest.raises(ValueError, match="Unknown format: invalid"):
        output_results(['name'], [('Alice',)], format='invalid', show_null=False)
