"""Configuration file parsing and validation."""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigError(Exception):
    """Raised when config file is invalid."""
    pass


class Config:
    """Parsed and validated configuration."""

    def __init__(self, data: Dict[str, Any]):
        self.raw = data
        self.database = data.get('database')
        self.regions = data.get('regions', {})
        self.taxa = data.get('taxa', {})
        self.filters = data.get('filters', {})

        self._validate()

    def _validate(self) -> None:
        """Validate configuration structure."""
        # Check required fields
        if not self.database:
            raise ConfigError("Missing required field: database")

        if not self.regions:
            raise ConfigError("Missing required field: regions")

        if not self.taxa:
            raise ConfigError("Missing required field: taxa")

        # Validate each region
        for key, region in self.regions.items():
            if not isinstance(region, dict):
                raise ConfigError(f"Region '{key}' must be a dictionary")

            if 'name' not in region:
                raise ConfigError(f"Region '{key}' missing required field: name")

            if 'place_ids' not in region:
                raise ConfigError(f"Region '{key}' missing required field: place_ids")

            if not isinstance(region['place_ids'], list):
                raise ConfigError(f"Region '{key}' place_ids must be a list")

        # Validate each taxon
        for key, taxon in self.taxa.items():
            if not isinstance(taxon, dict):
                raise ConfigError(f"Taxon '{key}' must be a dictionary")

            if 'name' not in taxon:
                raise ConfigError(f"Taxon '{key}' missing required field: name")

            if 'taxon_id' not in taxon:
                raise ConfigError(f"Taxon '{key}' missing required field: taxon_id")

            if not isinstance(taxon['taxon_id'], int):
                raise ConfigError(f"Taxon '{key}' taxon_id must be an integer")

    @classmethod
    def from_file(cls, path: Path) -> 'Config':
        """Load and parse config from YAML file."""
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML: {e}")
        except FileNotFoundError:
            raise ConfigError(f"Config file not found: {path}")

        if not isinstance(data, dict):
            raise ConfigError("Config file must contain a YAML dictionary")

        return cls(data)
