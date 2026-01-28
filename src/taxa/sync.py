"""Sync data from iNaturalist to SQLite database."""
import sqlite3
from pathlib import Path
from typing import Dict, Any
import json
import os

from tqdm import tqdm
from taxa.config import Config
from taxa.schema import create_schema
from taxa.fetcher import fetch_regional_taxa
from taxa.batch import fetch_taxa_batch
from taxa.transform import flatten_taxon_ancestry
from pyinaturalist import get_taxa_by_id


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

        # Sync each taxon using regional filtering
        for taxon_key, taxon_config in config.taxa.items():
            print(f"\nSyncing taxon: {taxon_config['name']} (ID: {taxon_config['taxon_id']})")

            # Phase 1: Discover which taxa occur in regions
            print(f"Discovering regional taxa...")

            # Calculate total queries for progress
            total_queries = sum(len(region['place_ids']) for region in config.regions.values())

            print(f"  Regions: {len(config.regions)}")
            print(f"  Total queries: {total_queries}\n")

            regional_taxa = {}  # taxon_id -> {region_key -> {place_id -> obs_data}}

            with tqdm(total=total_queries, desc="Querying regions", unit="query") as pbar:
                for region_key, region in config.regions.items():
                    for place_id in region['place_ids']:
                        # Update progress bar with current query
                        pbar.set_postfix_str(
                            f"{taxon_config['name'][:20]} in {region['name'][:20]}"
                        )

                        # Fetch all taxa with observations in this place
                        taxa = fetch_regional_taxa(
                            taxon_id=taxon_config['taxon_id'],
                            place_id=place_id,
                            quality_grade=config.filters.get('quality_grade')
                        )

                        # Store observation data by taxon/region/place
                        for taxon in taxa:
                            taxon_id = taxon['id']

                            if taxon_id not in regional_taxa:
                                regional_taxa[taxon_id] = {}
                            if region_key not in regional_taxa[taxon_id]:
                                regional_taxa[taxon_id][region_key] = {}

                            regional_taxa[taxon_id][region_key][place_id] = {
                                'observation_count': taxon['descendant_obs_count'],
                                'direct_count': taxon.get('direct_obs_count', 0)
                            }

                        pbar.update(1)

            print(f"\nTotal unique taxa discovered: {len(regional_taxa)}")

            if not regional_taxa:
                print(f"WARNING: No observations found for {taxon_config['name']} in any configured region")
                continue

            # Phase 2: Batch fetch full details
            print(f"\nFetching taxonomic details for {len(regional_taxa)} taxa...")

            taxon_ids = list(regional_taxa.keys())

            with tqdm(total=len(taxon_ids), desc="Processing taxa", unit="taxon") as pbar:

                def update_progress(batch_num, total_batches):
                    # Update progress bar by batch size (approximation)
                    pass  # tqdm updates happen per taxon below

                taxa = fetch_taxa_batch(taxon_ids, batch_size=30, callback=update_progress)

                # Track which taxa were successfully fetched
                fetched_ids = {taxon['id'] for taxon in taxa}
                missing_ids = set(taxon_ids) - fetched_ids

                if missing_ids:
                    print(f"\nWARNING: Failed to fetch {len(missing_ids)} taxa: {sorted(list(missing_ids)[:10])}")
                    if len(missing_ids) > 10:
                        print(f"  ... and {len(missing_ids) - 10} more")

                for taxon in taxa:
                    taxon_id = taxon['id']

                    # Insert main taxon
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

                    # Insert all ancestors (for complete hierarchy)
                    ancestors = taxon.get('ancestors', [])
                    for ancestor in ancestors:
                        ancestor_row = flatten_taxon_ancestry(ancestor)
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
                        """, ancestor_row)

                    # Insert observation data (already collected in Phase 1)
                    for region_key, places in regional_taxa[taxon_id].items():
                        for place_id, obs_data in places.items():
                            cursor.execute("""
                                INSERT OR REPLACE INTO observations (
                                    taxon_id, region_key, place_id,
                                    observation_count, observer_count,
                                    research_grade_count,
                                    first_observed, last_observed
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                taxon_id,
                                region_key,
                                place_id,
                                obs_data['observation_count'],
                                None,  # observer_count not available
                                None,  # research_grade_count not available
                                None,  # first_observed not available
                                None   # last_observed not available
                            ))

                    pbar.update(1)

            conn.commit()

        # Store sync metadata
        from datetime import datetime
        cursor.execute(
            "INSERT INTO sync_info (key, value) VALUES (?, ?)",
            ('last_sync', datetime.now().isoformat())
        )
        conn.commit()

        print("\n\nSync complete!")

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
