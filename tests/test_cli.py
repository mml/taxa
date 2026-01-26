"""Comprehensive tests for CLI commands using Click's test runner."""
from click.testing import CliRunner
from taxa.cli import main
from unittest.mock import patch
import yaml


def test_cli_help():
    """Test that main help command works."""
    runner = CliRunner()
    result = runner.invoke(main, ['--help'])
    assert result.exit_code == 0
    assert 'Query iNaturalist regional flora data' in result.output
    assert 'sync' in result.output
    assert 'query' in result.output
    assert 'search' in result.output
    assert 'info' in result.output


def test_sync_command():
    """Test that sync command works with valid config."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a valid config file
        config = {
            'database': './test.db',
            'regions': {'test': {'name': 'Test', 'place_ids': [1]}},
            'taxa': {'test': {'name': 'Test', 'taxon_id': 1}}
        }
        with open('config.yaml', 'w') as f:
            yaml.dump(config, f)

        # Mock API calls
        with patch('taxa.sync.fetch_taxon_descendants', return_value=[]), \
             patch('taxa.sync.fetch_observation_summary', return_value=None):
            result = runner.invoke(main, ['sync'])

        assert result.exit_code == 0
        assert 'Loading config...' in result.output
        assert 'Sync complete!' in result.output


def test_sync_command_custom_config():
    """Test that sync command accepts custom config path."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a valid custom config file
        config = {
            'database': './custom.db',
            'regions': {'test': {'name': 'Test', 'place_ids': [1]}},
            'taxa': {'test': {'name': 'Test', 'taxon_id': 1}}
        }
        with open('custom.yaml', 'w') as f:
            yaml.dump(config, f)

        # Mock API calls
        with patch('taxa.sync.fetch_taxon_descendants', return_value=[]), \
             patch('taxa.sync.fetch_observation_summary', return_value=None):
            result = runner.invoke(main, ['sync', 'custom.yaml'])

        assert result.exit_code == 0
        assert 'Loading config...' in result.output
        assert 'Sync complete!' in result.output


def test_sync_command_help():
    """Test sync command help."""
    runner = CliRunner()
    result = runner.invoke(main, ['sync', '--help'])
    assert result.exit_code == 0
    assert '--timeout' in result.output
    assert '--dry-run' in result.output


def test_query_command_with_query():
    """Test query command with SQL query."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a test database
        import sqlite3
        conn = sqlite3.connect('flora.db')
        conn.execute('CREATE TABLE test (id INTEGER, name TEXT)')
        conn.execute('INSERT INTO test VALUES (1, "foo"), (2, "bar")')
        conn.commit()
        conn.close()

        result = runner.invoke(main, ['query', 'SELECT * FROM test'])
        assert result.exit_code == 0
        # Verify headers and data
        lines = result.output.strip().split('\n')
        assert lines[0] == 'id\tname'
        assert '1\tfoo' in result.output
        assert '2\tbar' in result.output


def test_query_command_without_query():
    """Test query command without query (interactive mode)."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a test database
        import sqlite3
        conn = sqlite3.connect('flora.db')
        conn.close()

        # Mock subprocess.run to avoid actually launching interactive shell
        with patch('taxa.cli.subprocess.run') as mock_run:
            result = runner.invoke(main, ['query'])
            assert result.exit_code == 0
            # Verify subprocess was called with sqlite3
            mock_run.assert_called_once_with(['sqlite3', 'flora.db'])


def test_query_command_database_not_found():
    """Test query command with missing database."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ['query', 'SELECT 1'])
        assert result.exit_code == 1
        assert 'Database not found' in result.output
        assert 'taxa sync' in result.output


def test_query_command_sql_error():
    """Test query command with invalid SQL."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        import sqlite3
        conn = sqlite3.connect('flora.db')
        conn.close()

        result = runner.invoke(main, ['query', 'INVALID SQL'])
        assert result.exit_code == 1
        assert 'ERROR:' in result.output


def test_query_command_custom_database():
    """Test query command with custom database path."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        import sqlite3
        conn = sqlite3.connect('custom.db')
        conn.execute('CREATE TABLE test (val INTEGER)')
        conn.execute('INSERT INTO test VALUES (42)')
        conn.commit()
        conn.close()

        result = runner.invoke(main, ['query', '--database', 'custom.db', 'SELECT * FROM test'])
        assert result.exit_code == 0
        assert '42' in result.output


def test_search_places_command():
    """Test search places command."""
    runner = CliRunner()
    result = runner.invoke(main, ['search', 'places', 'test'])
    assert result.exit_code == 0
    assert 'Searching places for: test' in result.output


def test_search_taxa_command():
    """Test search taxa command."""
    runner = CliRunner()
    result = runner.invoke(main, ['search', 'taxa', 'Rosaceae'])
    assert result.exit_code == 0
    assert 'Searching taxa for: Rosaceae' in result.output


def test_info_command():
    """Test info command."""
    runner = CliRunner()
    result = runner.invoke(main, ['info'])
    assert result.exit_code == 0
    assert 'Database info:' in result.output


def test_sync_command_missing_config():
    """Test sync command with missing config file."""
    runner = CliRunner()
    result = runner.invoke(main, ['sync', 'nonexistent.yaml'])
    assert result.exit_code != 0


def test_sync_command_invalid_config():
    """Test sync command with invalid config."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create invalid config (missing required fields)
        with open('bad_config.yaml', 'w') as f:
            yaml.dump({'database': './test.db'}, f)

        result = runner.invoke(main, ['sync', 'bad_config.yaml'])
        assert result.exit_code == 1
        assert 'ERROR:' in result.output


def test_sync_command_keyboard_interrupt():
    """Test sync command handles KeyboardInterrupt."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        config = {
            'database': './test.db',
            'regions': {'test': {'name': 'Test', 'place_ids': [1]}},
            'taxa': {'test': {'name': 'Test', 'taxon_id': 1}}
        }
        with open('config.yaml', 'w') as f:
            yaml.dump(config, f)

        # Raise KeyboardInterrupt during fetch
        with patch('taxa.sync.fetch_taxon_descendants', side_effect=KeyboardInterrupt):
            result = runner.invoke(main, ['sync'])

        assert result.exit_code == 1
        assert 'interrupted' in result.output.lower()
