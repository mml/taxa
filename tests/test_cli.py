"""Comprehensive tests for CLI commands using Click's test runner."""
from click.testing import CliRunner
from taxa.cli import main


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
    """Test that sync command works with default config."""
    runner = CliRunner()
    result = runner.invoke(main, ['sync'])
    assert result.exit_code == 0
    assert 'Syncing from config: config.yaml' in result.output
    assert 'Not yet implemented' in result.output


def test_sync_command_custom_config():
    """Test that sync command accepts custom config path."""
    runner = CliRunner()
    result = runner.invoke(main, ['sync', 'custom.yaml'])
    assert result.exit_code == 0
    assert 'Syncing from config: custom.yaml' in result.output


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
    result = runner.invoke(main, ['query', 'SELECT 1'])
    assert result.exit_code == 0
    assert 'Running query: SELECT 1' in result.output


def test_query_command_without_query():
    """Test query command without query (interactive mode)."""
    runner = CliRunner()
    result = runner.invoke(main, ['query'])
    assert result.exit_code == 0
    assert 'Opening interactive SQLite shell' in result.output


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
