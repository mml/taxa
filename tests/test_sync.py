"""Tests for database sync functionality."""
import sqlite3
import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, Mock
from taxa.sync import sync_database
from taxa.config import Config


@pytest.fixture
def test_config(tmp_path):
    """Create a test config."""
    config_dict = {
        'database': str(tmp_path / 'test.db'),
        'regions': {
            'test_region': {
                'name': 'Test Region',
                'place_ids': [14]
            }
        },
        'taxa': {
            'test_taxon': {
                'name': 'Test Taxon',
                'taxon_id': 47851
            }
        },
        'filters': {
            'quality_grade': 'research'
        }
    }
    return Config(config_dict)


@pytest.fixture
def db_conn(tmp_path):
    """Fixture for database connection with automatic cleanup."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    yield conn
    conn.close()


def test_sync_database_creates_schema(test_config):
    """Test that sync creates database schema."""
    with patch('taxa.sync.fetch_regional_taxa', return_value=[]), \
         patch('taxa.sync.fetch_taxa_batch', return_value=[]):

        sync_database(test_config)

        # Verify database exists and has correct schema
        assert Path(test_config.database).exists()

        conn = sqlite3.connect(test_config.database)
        cursor = conn.cursor()

        # Check that tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert 'taxa' in tables
        assert 'observations' in tables
        assert 'regions' in tables
        assert 'sync_info' in tables

        conn.close()


def test_sync_database_stores_region_metadata(test_config):
    """Test that sync stores region metadata correctly."""
    with patch('taxa.sync.fetch_regional_taxa', return_value=[]), \
         patch('taxa.sync.fetch_taxa_batch', return_value=[]):

        sync_database(test_config)

        conn = sqlite3.connect(test_config.database)
        cursor = conn.cursor()

        cursor.execute("SELECT key, name, place_ids FROM regions WHERE key = ?",
                      ('test_region',))
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == 'test_region'
        assert row[1] == 'Test Region'
        assert json.loads(row[2]) == [14]

        conn.close()


def test_sync_database_stores_taxa(test_config):
    """Test that sync fetches and stores taxa."""
    # Mock the regional discovery returning one taxon
    mock_regional_taxon = {
        'id': 47851,
        'name': 'Plantae',
        'rank': 'kingdom',
        'descendant_obs_count': 100,
        'direct_obs_count': 50
    }

    # Mock the batch fetch returning full taxon details
    mock_batch_taxon = {
        'id': 47851,
        'name': 'Plantae',
        'rank': 'kingdom',
        'preferred_common_name': 'Plants',
        'is_active': True,
        'iconic_taxon_name': 'Plantae',
        'ancestors': []
    }

    with patch('taxa.sync.fetch_regional_taxa', return_value=[mock_regional_taxon]), \
         patch('taxa.sync.fetch_taxa_batch', return_value=[mock_batch_taxon]):

        sync_database(test_config)

        conn = sqlite3.connect(test_config.database)
        cursor = conn.cursor()

        cursor.execute("SELECT id, scientific_name, common_name, rank FROM taxa WHERE id = ?",
                      (47851,))
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == 47851
        assert row[1] == 'Plantae'
        assert row[2] == 'Plants'
        assert row[3] == 'kingdom'

        conn.close()


def test_sync_database_stores_observations(test_config):
    """Test that sync fetches and stores observations."""
    # Mock the regional discovery returning one taxon with observation count
    mock_regional_taxon = {
        'id': 47851,
        'name': 'Plantae',
        'rank': 'kingdom',
        'descendant_obs_count': 100,
        'direct_obs_count': 50
    }

    # Mock the batch fetch returning full taxon details
    mock_batch_taxon = {
        'id': 47851,
        'name': 'Plantae',
        'rank': 'kingdom',
        'ancestors': []
    }

    with patch('taxa.sync.fetch_regional_taxa', return_value=[mock_regional_taxon]), \
         patch('taxa.sync.fetch_taxa_batch', return_value=[mock_batch_taxon]):

        sync_database(test_config)

        conn = sqlite3.connect(test_config.database)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT taxon_id, region_key, place_id, observation_count, observer_count
            FROM observations
            WHERE taxon_id = ? AND place_id = ?
        """, (47851, 14))
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == 47851
        assert row[1] == 'test_region'
        assert row[2] == 14
        assert row[3] == 100  # descendant_obs_count from regional_taxon
        assert row[4] is None  # observer_count not available in new implementation

        conn.close()


def test_sync_database_stores_sync_metadata(test_config):
    """Test that sync stores sync metadata."""
    with patch('taxa.sync.fetch_regional_taxa', return_value=[]), \
         patch('taxa.sync.fetch_taxa_batch', return_value=[]):

        sync_database(test_config)

        conn = sqlite3.connect(test_config.database)
        cursor = conn.cursor()

        cursor.execute("SELECT key, value FROM sync_info WHERE key = ?", ('last_sync',))
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == 'last_sync'
        assert row[1] is not None  # Should be an ISO timestamp

        conn.close()


def test_sync_database_atomic_replacement(test_config, tmp_path):
    """Test that database replacement is atomic with backup."""
    # Create an existing database
    old_db_path = Path(test_config.database)
    old_db_path.parent.mkdir(parents=True, exist_ok=True)
    old_conn = sqlite3.connect(old_db_path)
    old_conn.execute("CREATE TABLE test (id INTEGER)")
    old_conn.execute("INSERT INTO test VALUES (1)")
    old_conn.commit()
    old_conn.close()

    with patch('taxa.sync.fetch_regional_taxa', return_value=[]), \
         patch('taxa.sync.fetch_taxa_batch', return_value=[]):

        sync_database(test_config)

        # Check that backup was created
        backup_path = Path(f"{test_config.database}~")
        assert backup_path.exists()

        # Verify old data is in backup
        backup_conn = sqlite3.connect(backup_path)
        cursor = backup_conn.cursor()
        cursor.execute("SELECT id FROM test")
        assert cursor.fetchone()[0] == 1
        backup_conn.close()

        # Verify new database has new schema
        new_conn = sqlite3.connect(test_config.database)
        cursor = new_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='taxa'")
        assert cursor.fetchone() is not None
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test'")
        assert cursor.fetchone() is None  # Old table should be gone
        new_conn.close()


def test_sync_database_dry_run(test_config, capsys):
    """Test that dry_run mode doesn't create database."""
    sync_database(test_config, dry_run=True)

    # Database should not be created
    assert not Path(test_config.database).exists()

    # Should print dry run message
    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


def test_sync_database_prints_progress(test_config, capsys):
    """Test that sync prints progress messages."""
    with patch('taxa.sync.fetch_regional_taxa', return_value=[]), \
         patch('taxa.sync.fetch_taxa_batch', return_value=[]):

        sync_database(test_config)

        captured = capsys.readouterr()
        assert "Loading config..." in captured.out
        assert "test_region" in captured.out
        assert "test_taxon" in captured.out
        assert "Building database:" in captured.out
        assert "Syncing taxon: Test Taxon (ID: 47851)" in captured.out
        assert "Sync complete!" in captured.out


def test_sync_database_regional_filtering(tmp_path):
    """Test sync uses regional filtering instead of global fetch."""
    config = Config({
        'database': str(tmp_path / "test.db"),
        'regions': {
            'test_region': {
                'name': 'Test Region',
                'place_ids': [123]
            }
        },
        'taxa': {
            'test_taxon': {
                'name': 'Test Taxon',
                'taxon_id': 456
            }
        },
        'filters': {}
    })

    with patch('taxa.sync.fetch_regional_taxa') as mock_regional, \
         patch('taxa.sync.fetch_taxa_batch') as mock_batch:

        # Mock regional discovery returns 3 taxa
        mock_regional.return_value = [
            {'id': 1, 'descendant_obs_count': 10, 'direct_obs_count': 5},
            {'id': 2, 'descendant_obs_count': 20, 'direct_obs_count': 10},
            {'id': 3, 'descendant_obs_count': 15, 'direct_obs_count': 15}
        ]

        # Mock batch fetch returns full details
        mock_batch.return_value = [
            {
                'id': 1,
                'name': 'Taxon 1',
                'rank': 'species',
                'ancestors': []
            },
            {
                'id': 2,
                'name': 'Taxon 2',
                'rank': 'species',
                'ancestors': []
            },
            {
                'id': 3,
                'name': 'Taxon 3',
                'rank': 'species',
                'ancestors': []
            }
        ]

        sync_database(config)

        # Should have called regional fetch once per region
        assert mock_regional.call_count == 1

        # Should have called batch fetch once with all 3 IDs
        assert mock_batch.call_count == 1
        batch_ids = mock_batch.call_args[0][0]
        assert set(batch_ids) == {1, 2, 3}

        # Verify database has the taxa
        conn = sqlite3.connect(config.database)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM taxa")
        assert cursor.fetchone()[0] == 3
        conn.close()
