"""Sync data from iNaturalist to SQLite database."""
import sqlite3
from pathlib import Path
from typing import Dict, Any
import json
import os

from taxa.config import Config
from taxa.schema import create_schema
from taxa.fetcher import fetch_taxon_descendants
from taxa.transform import flatten_taxon_ancestry
from taxa.observations import fetch_observation_summary


def sync_database(config: Config, dry_run: bool = False) -> None:
    """
    Sync iNaturalist data to SQLite database based on config.

    Args:
        config: Parsed configuration
        dry_run: If True, only estimate work without syncing
    """
    print(f"Loading config...")
    print(f"  Regions: {', '.join(config.regions.keys())}")
    print(f"  Taxa: {', '.join(config.taxa.keys())}")
    print()

    if dry_run:
        print("DRY RUN - estimation only")
        # TODO: Estimate total work
        return

    # Build database to temporary file
    temp_db = f"{config.database}.new"

    print(f"Building database: {temp_db}")
    conn = sqlite3.connect(temp_db)

    try:
        # Create schema
        create_schema(conn)

        # Store region metadata
        cursor = conn.cursor()
        for key, region in config.regions.items():
            cursor.execute(
                "INSERT INTO regions (key, name, place_ids) VALUES (?, ?, ?)",
                (key, region['name'], json.dumps(region['place_ids']))
            )

        # Sync each taxon
        for taxon_key, taxon_config in config.taxa.items():
            print(f"\nFetching taxon: {taxon_config['name']} (ID: {taxon_config['taxon_id']})")

            # Progress reporting callback
            def progress_callback(items_fetched):
                if items_fetched % 100 == 0:
                    print(f"Fetched {items_fetched} taxa...")

            # Fetch all descendant taxa
            taxon_id = taxon_config['taxon_id']
            for taxon in fetch_taxon_descendants(taxon_id, progress_callback=progress_callback):
                # Flatten and insert taxon
                row = flatten_taxon_ancestry(taxon)

                cursor.execute("""
                    INSERT OR REPLACE INTO taxa (
                        id, scientific_name, common_name, rank,
                        kingdom, phylum, class, order_name, family,
                        subfamily, tribe, subtribe, genus, subgenus,
                        section, subsection, species, subspecies, variety, form,
                        is_active, iconic_taxon
                    ) VALUES (
                        :id, :scientific_name, :common_name, :rank,
                        :kingdom, :phylum, :class, :order_name, :family,
                        :subfamily, :tribe, :subtribe, :genus, :subgenus,
                        :section, :subsection, :species, :subspecies, :variety, :form,
                        :is_active, :iconic_taxon
                    )
                """, row)

                # Fetch observations for this taxon in each region
                for region_key, region in config.regions.items():
                    for place_id in region['place_ids']:
                        quality = config.filters.get('quality_grade')

                        obs = fetch_observation_summary(
                            taxon_id=taxon['id'],
                            place_id=place_id,
                            quality_grade=quality
                        )

                        if obs:
                            cursor.execute("""
                                INSERT OR REPLACE INTO observations (
                                    taxon_id, region_key, place_id,
                                    observation_count, observer_count,
                                    research_grade_count,
                                    first_observed, last_observed
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                obs['taxon_id'],
                                region_key,
                                place_id,
                                obs['observation_count'],
                                obs['observer_count'],
                                obs['research_grade_count'],
                                obs['first_observed'],
                                obs['last_observed']
                            ))

            conn.commit()

        # Store sync metadata
        from datetime import datetime
        cursor.execute(
            "INSERT INTO sync_info (key, value) VALUES (?, ?)",
            ('last_sync', datetime.now().isoformat())
        )
        conn.commit()

        print("\nSync complete!")

    finally:
        conn.close()

    # Atomic database replacement
    try:
        if os.path.exists(config.database):
            backup = f"{config.database}~"
            print(f"Backing up old database to: {backup}")
            os.rename(config.database, backup)

        print(f"Replacing database: {config.database}")
        os.rename(temp_db, config.database)
    except OSError as e:
        # Clean up temp file on failure
        if os.path.exists(temp_db):
            os.remove(temp_db)
        raise RuntimeError(f"Failed to replace database: {e}")
