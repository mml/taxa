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
        with patch('taxa.sync.fetch_regional_taxa', return_value=[]), \
             patch('taxa.sync.fetch_taxa_batch', return_value=[]):
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
        with patch('taxa.sync.fetch_regional_taxa', return_value=[]), \
             patch('taxa.sync.fetch_taxa_batch', return_value=[]):
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

    with patch('taxa.cli.get_places_autocomplete') as mock_places:
        mock_places.return_value = {
            'results': [
                {'id': 123, 'display_name': 'Test Place, CA, US'},
                {'id': 456, 'display_name': 'Another Test'}
            ]
        }

        result = runner.invoke(main, ['search', 'places', 'test'])

    assert result.exit_code == 0
    assert "Places matching 'test':" in result.output
    assert '123' in result.output
    assert 'Test Place, CA, US' in result.output


def test_search_taxa_command():
    """Test search taxa command."""
    runner = CliRunner()

    with patch('taxa.cli.get_taxa_autocomplete') as mock_taxa:
        mock_taxa.return_value = {
            'results': [
                {
                    'id': 47125,
                    'name': 'Rosaceae',
                    'rank': 'family',
                    'preferred_common_name': 'rose family'
                }
            ]
        }

        result = runner.invoke(main, ['search', 'taxa', 'Rosaceae'])

    assert result.exit_code == 0
    assert "Taxa matching 'Rosaceae':" in result.output
    assert '47125' in result.output
    assert 'Rosaceae' in result.output
    assert 'rose family' in result.output


def test_info_command():
    """Test info command."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        import sqlite3
        from taxa.schema import create_schema
        from datetime import datetime

        # Create database with schema
        conn = sqlite3.connect('flora.db')
        create_schema(conn)

        # Insert some test data
        conn.execute("INSERT INTO sync_info (key, value) VALUES (?, ?)",
                    ('last_sync', datetime.now().isoformat()))
        conn.execute("INSERT INTO taxa (id, scientific_name, rank) VALUES (1, 'Test', 'species')")
        conn.execute("INSERT INTO observations (taxon_id, region_key, place_id, observation_count) VALUES (1, 'test', 123, 10)")
        conn.commit()
        conn.close()

        result = runner.invoke(main, ['info'])

        assert result.exit_code == 0
        assert 'Database: flora.db' in result.output
        assert 'Taxa: 1' in result.output
        assert 'Total observations: 10' in result.output


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
        with patch('taxa.sync.fetch_regional_taxa', side_effect=KeyboardInterrupt):
            result = runner.invoke(main, ['sync'])

        assert result.exit_code == 1
        assert 'interrupted' in result.output.lower()


def test_breakdown_command_help():
    """Test that breakdown command help works."""
    runner = CliRunner()
    result = runner.invoke(main, ['breakdown', '--help'])
    assert result.exit_code == 0
    assert 'breakdown' in result.output.lower()
    assert '--levels' in result.output
    assert '--region' in result.output


def test_breakdown_command_basic():
    """Test basic breakdown command execution."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create test database with sample data
        import sqlite3
        from taxa.schema import create_schema

        conn = sqlite3.connect('test.db')
        create_schema(conn)

        # Insert test taxa
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO taxa (id, scientific_name, rank, family, subfamily)
            VALUES (1, 'Plant 1', 'species', 'Asteraceae', 'Asteroideae')
        """)
        cursor.execute("""
            INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
            VALUES (1, 'test', 1, 100)
        """)
        conn.commit()
        conn.close()

        result = runner.invoke(main, ['breakdown', 'Asteraceae', '--database', 'test.db'])

        assert result.exit_code == 0
        assert 'Asteroideae' in result.output
        assert 'observation_count' in result.output


def test_breakdown_command_taxon_not_found():
    """Test breakdown with non-existent taxon."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        import sqlite3
        from taxa.schema import create_schema

        conn = sqlite3.connect('test.db')
        create_schema(conn)
        conn.close()

        result = runner.invoke(main, ['breakdown', 'NotARealTaxon', '--database', 'test.db'])

        assert result.exit_code == 1
        assert 'not found' in result.output


def test_breakdown_command_invalid_level():
    """Test breakdown with invalid level specification."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        import sqlite3
        from taxa.schema import create_schema

        conn = sqlite3.connect('test.db')
        create_schema(conn)

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO taxa (id, scientific_name, rank, family)
            VALUES (1, 'Asteraceae', 'family', 'Asteraceae')
        """)
        conn.commit()
        conn.close()

        # Try to break down to higher rank
        result = runner.invoke(main, [
            'breakdown', 'Asteraceae',
            '--levels', 'kingdom',
            '--database', 'test.db'
        ])

        assert result.exit_code == 1
        assert 'not below' in result.output


def test_breakdown_command_database_not_found():
    """Test breakdown with missing database."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ['breakdown', 'Asteraceae', '--database', 'missing.db'])

        assert result.exit_code == 1
        assert 'Database not found' in result.output


def test_breakdown_command_empty_results():
    """Test breakdown with no matching observations."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        import sqlite3
        from taxa.schema import create_schema

        conn = sqlite3.connect('test.db')
        create_schema(conn)

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO taxa (id, scientific_name, rank, family)
            VALUES (1, 'Asteraceae', 'family', 'Asteraceae')
        """)
        conn.commit()
        conn.close()

        # No observations inserted, should get empty result
        result = runner.invoke(main, ['breakdown', 'Asteraceae', '--database', 'test.db'])

        assert result.exit_code == 0
        assert 'No observations found' in result.output


def test_breakdown_command_auto_fallthrough(sample_db, cli_runner):
    """Breakdown without --levels skips unpopulated ranks and shows notice."""
    result = cli_runner.invoke(
        main,
        ['breakdown', 'Dryadoideae', '--database', sample_db]
    )

    assert result.exit_code == 0
    # Should show genus (not tribe which is NULL)
    assert 'genus' in result.output
    assert 'Cercocarpus' in result.output
    # Should show notice to stderr
    assert '[Notice: tribe unpopulated, showing genus instead]' in result.stderr


def test_breakdown_command_explicit_levels_show_null(sample_db, cli_runner):
    """Breakdown with explicit --levels shows NULL values without fallthrough."""
    result = cli_runner.invoke(
        main,
        ['breakdown', 'Dryadoideae', '--levels', 'tribe', '--database', sample_db]
    )

    assert result.exit_code == 0
    # Should show tribe (even though it's NULL)
    assert 'tribe' in result.output
    assert 'NULL' in result.output
    # Should NOT show notice to stderr
    assert '[Notice:' not in result.stderr


def test_breakdown_command_no_notice_when_next_rank_populated(sample_db, cli_runner):
    """Breakdown shows no notice when next rank is populated."""
    result = cli_runner.invoke(
        main,
        ['breakdown', 'Rosaceae', '--database', sample_db]
    )

    assert result.exit_code == 0
    # Should show subfamily (which is populated)
    assert 'subfamily' in result.output
    # Should NOT show notice since we didn't skip
    assert '[Notice:' not in result.stderr
