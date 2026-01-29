"""Breakdown query generation for hierarchical taxonomic queries."""
import sqlite3
from taxa.taxonomy import TAXONOMIC_RANKS


def find_taxon_rank(db, taxon_name):
    """Query each rank column to find where this taxon appears.

    Args:
        db: SQLite database connection
        taxon_name: Name of taxon to search for

    Returns:
        str: The rank where taxon was found

    Raises:
        ValueError: If taxon not found or found at multiple ranks
    """
    cursor = db.cursor()
    found_ranks = []

    # Get available columns in taxa table
    cursor.execute("PRAGMA table_info(taxa)")
    available_columns = {row[1] for row in cursor.fetchall()}

    for rank in TAXONOMIC_RANKS:
        # Skip ranks not present in this database
        if rank not in available_columns:
            continue

        result = cursor.execute(
            f"SELECT 1 FROM taxa WHERE {rank} = ? LIMIT 1",
            (taxon_name,)
        )
        if result.fetchone():
            found_ranks.append(rank)

    if not found_ranks:
        raise ValueError(f"Taxon '{taxon_name}' not found in database")

    if len(found_ranks) > 1:
        raise ValueError(
            f"Ambiguous taxon '{taxon_name}' found at multiple ranks: {', '.join(found_ranks)}\n"
            f"Specify with --rank: taxa breakdown {taxon_name} --rank {found_ranks[0]}"
        )

    return found_ranks[0]
