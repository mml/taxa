import pytest
from taxa.config import Config, ConfigError
from pathlib import Path


def test_config_loads_valid_yaml(tmp_path):
    """Test loading a valid config file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
database: ./flora.db

regions:
  sfba:
    name: "San Francisco Bay Area"
    place_ids: [5245, 5678]

taxa:
  rosaceae:
    name: "Rosaceae"
    taxon_id: 47125

filters:
  quality_grade: research
""")

    config = Config.from_file(config_file)

    assert config.database == "./flora.db"
    assert "sfba" in config.regions
    assert config.regions["sfba"]["name"] == "San Francisco Bay Area"
    assert config.regions["sfba"]["place_ids"] == [5245, 5678]
    assert "rosaceae" in config.taxa
    assert config.taxa["rosaceae"]["taxon_id"] == 47125
    assert config.filters["quality_grade"] == "research"


def test_config_validates_required_fields(tmp_path):
    """Test that missing required fields raise errors."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
regions:
  sfba:
    name: "SF Bay Area"
    place_ids: [5245]
""")

    with pytest.raises(ConfigError, match="Missing required field: database"):
        Config.from_file(config_file)


def test_config_validates_region_structure(tmp_path):
    """Test that regions must have name and place_ids."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
database: ./flora.db

regions:
  sfba:
    name: "SF Bay Area"
    # Missing place_ids

taxa:
  rosaceae:
    name: "Rosaceae"
    taxon_id: 47125
""")

    with pytest.raises(ConfigError, match="place_ids"):
        Config.from_file(config_file)


def test_config_validates_taxa_structure(tmp_path):
    """Test that taxa must have name and taxon_id."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
database: ./flora.db

regions:
  sfba:
    name: "SF Bay Area"
    place_ids: [5245]

taxa:
  rosaceae:
    name: "Rosaceae"
    # Missing taxon_id
""")

    with pytest.raises(ConfigError, match="taxon_id"):
        Config.from_file(config_file)
