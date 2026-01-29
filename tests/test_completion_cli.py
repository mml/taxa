"""Tests for completion CLI commands."""
import json
from pathlib import Path
from click.testing import CliRunner
from taxa.cli import main


def test_completion_command_exists():
    """Completion command group exists."""
    runner = CliRunner()
    result = runner.invoke(main, ['completion', '--help'])

    assert result.exit_code == 0
    assert 'Manage shell completions' in result.output


def test_completion_shows_subcommands():
    """Completion command lists subcommands."""
    runner = CliRunner()
    result = runner.invoke(main, ['completion', '--help'])

    assert 'generate-cache' in result.output
    assert 'install' in result.output


def test_generate_cache_command_creates_cache(tmp_path, monkeypatch):
    """generate-cache command creates cache file."""
    import sqlite3
    from taxa.schema import create_schema

    # Create sample database
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    create_schema(conn)

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, genus)
        VALUES (1, 'Quercus', 'genus', 'Fagaceae', 'Quercus')
    """)
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (1, 'us-ca', 123, 100)
    """)
    conn.commit()
    conn.close()

    cache_dir = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

    runner = CliRunner()
    result = runner.invoke(main, ['completion', 'generate-cache', '--database', str(db_path)])

    assert result.exit_code == 0

    # Check cache file was created
    cache_file = cache_dir / 'taxa' / f'completion-cache-{db_path.stem}.json'
    assert cache_file.exists()


def test_generate_cache_command_missing_database():
    """generate-cache command fails gracefully for missing database."""
    runner = CliRunner()
    result = runner.invoke(main, ['completion', 'generate-cache', '--database', '/nonexistent.db'])

    assert result.exit_code != 0
    assert 'Database not found' in result.output or 'ERROR' in result.output


def test_install_command_exists():
    """Install command exists."""
    runner = CliRunner()
    result = runner.invoke(main, ['completion', 'install', '--help'])

    assert result.exit_code == 0
    assert 'Install shell completion' in result.output


def test_install_command_creates_completion_script(tmp_path, monkeypatch):
    """Install command creates completion script."""
    monkeypatch.setenv("HOME", str(tmp_path))

    runner = CliRunner()
    result = runner.invoke(main, ['completion', 'install'])

    assert result.exit_code == 0

    # Check completion script was created
    completion_script = tmp_path / '.config' / 'taxa' / 'completions' / '_taxa'
    assert completion_script.exists()


def test_install_generates_initial_cache(tmp_path, monkeypatch):
    """Install command generates initial cache if database exists."""
    import sqlite3
    import shutil
    from taxa.schema import create_schema

    # Create sample database in temp location
    db_path = tmp_path / "flora.db"
    conn = sqlite3.connect(db_path)
    create_schema(conn)

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, genus)
        VALUES (1, 'Quercus', 'genus', 'Fagaceae', 'Quercus')
    """)
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (1, 'us-ca', 123, 100)
    """)
    conn.commit()
    conn.close()

    # Set HOME and cache directory
    monkeypatch.setenv("HOME", str(tmp_path))
    cache_dir = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

    # Copy db to current directory for install to find
    cwd_db = Path.cwd() / "flora.db"
    shutil.copy(db_path, cwd_db)

    try:
        runner = CliRunner()
        result = runner.invoke(main, ['completion', 'install'])

        assert result.exit_code == 0

        # Check cache was created
        cache_file = cache_dir / 'taxa' / 'completion-cache-flora.json'
        assert cache_file.exists()
    finally:
        if cwd_db.exists():
            cwd_db.unlink()


def test_full_install_workflow(tmp_path, monkeypatch):
    """Test complete install workflow with cache generation."""
    import sqlite3
    import shutil
    from taxa.schema import create_schema

    # Create sample database
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    create_schema(conn)

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO taxa (id, scientific_name, rank, family, genus)
        VALUES (1, 'Quercus', 'genus', 'Fagaceae', 'Quercus')
    """)
    cursor.execute("""
        INSERT INTO observations (taxon_id, region_key, place_id, observation_count)
        VALUES (1, 'us-ca', 123, 100)
    """)
    conn.commit()
    conn.close()

    # Set environment
    monkeypatch.setenv("HOME", str(tmp_path))
    cache_dir = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

    # Copy db to current directory for install to find
    cwd_db = Path.cwd() / "flora.db"
    shutil.copy(db_path, cwd_db)

    try:
        runner = CliRunner()

        # Run install
        result = runner.invoke(main, ['completion', 'install'])
        assert result.exit_code == 0
        assert 'Installed completion script' in result.output
        assert 'Generated initial cache' in result.output

        # Verify completion script exists
        completion_script = tmp_path / '.config' / 'taxa' / 'completions' / '_taxa'
        assert completion_script.exists()
        assert '#compdef taxa' in completion_script.read_text()

        # Verify cache exists
        cache_file = cache_dir / 'taxa' / 'completion-cache-flora.json'
        assert cache_file.exists()

        # Verify cache content
        cache_data = json.loads(cache_file.read_text())
        assert 'taxon_names' in cache_data
        assert 'region_keys' in cache_data
        assert 'ranks' in cache_data

        # Run generate-cache with different database
        result2 = runner.invoke(main, ['completion', 'generate-cache', '--database', str(db_path)])
        assert result2.exit_code == 0

        # Verify second cache created
        cache_file2 = cache_dir / 'taxa' / f'completion-cache-{db_path.stem}.json'
        assert cache_file2.exists()

    finally:
        if cwd_db.exists():
            cwd_db.unlink()
