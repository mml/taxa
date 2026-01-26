"""SQLite schema creation for taxa database."""
import sqlite3


def create_schema(conn: sqlite3.Connection) -> None:
    """
    Create database schema with all tables and indexes.

    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()

    # Taxa table with wide schema (all ranks as columns)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS taxa (
            id INTEGER PRIMARY KEY,
            scientific_name TEXT NOT NULL,
            common_name TEXT,
            rank TEXT NOT NULL,

            -- All possible taxonomic ranks
            kingdom TEXT,
            phylum TEXT,
            class TEXT,
            order_name TEXT,
            family TEXT,
            subfamily TEXT,
            tribe TEXT,
            subtribe TEXT,
            genus TEXT,
            subgenus TEXT,
            section TEXT,
            subsection TEXT,
            species TEXT,
            subspecies TEXT,
            variety TEXT,
            form TEXT,

            -- Metadata
            is_active BOOLEAN,
            iconic_taxon TEXT
        )
    """)

    # Observations table with aggregated data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            taxon_id INTEGER NOT NULL,
            region_key TEXT NOT NULL,
            place_id INTEGER NOT NULL,

            observation_count INTEGER,
            observer_count INTEGER,
            research_grade_count INTEGER,

            first_observed DATE,
            last_observed DATE,

            PRIMARY KEY (taxon_id, place_id),
            FOREIGN KEY (taxon_id) REFERENCES taxa(id)
        )
    """)

    # Regions metadata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regions (
            key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            place_ids TEXT NOT NULL
        )
    """)

    # Sync metadata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_info (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Create indexes for common query patterns
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_taxa_family ON taxa(family)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_taxa_genus ON taxa(genus)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_taxa_subfamily ON taxa(subfamily)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_taxa_tribe ON taxa(tribe)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_region ON observations(region_key)")

    conn.commit()
