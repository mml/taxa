"""Breakdown query generation for hierarchical taxonomic queries."""
import sqlite3
from taxa.taxonomy import TAXONOMIC_RANKS, sort_ranks, get_next_ranks


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


def find_first_populated_rank(conn, base_taxon, base_rank):
    """Find the first populated rank below base_rank for the given taxon.

    Checks each rank in hierarchical order to find the first one with
    non-NULL values among descendants of base_taxon.

    Args:
        conn: SQLite database connection
        base_taxon: Name of base taxon (e.g., "Rosaceae")
        base_rank: Rank of base taxon (e.g., "family")

    Returns:
        Tuple of (populated_rank, expected_rank) where:
        - populated_rank: First rank below base_rank with non-NULL data
        - expected_rank: The immediate next rank after base_rank

    Raises:
        ValueError: If no populated ranks found below base_rank
    """
    cursor = conn.cursor()

    # Get all ranks below base_rank
    remaining_ranks = get_next_ranks(base_rank, count=100)

    if not remaining_ranks:
        raise ValueError(f"No levels below '{base_rank}' in taxonomy")

    expected_rank = remaining_ranks[0]

    # Check each rank for non-NULL values
    for candidate_rank in remaining_ranks:
        result = cursor.execute(
            f"SELECT 1 FROM taxa WHERE {base_rank} = ? AND {candidate_rank} IS NOT NULL LIMIT 1",
            (base_taxon,)
        )
        if result.fetchone():
            return (candidate_rank, expected_rank)

    raise ValueError(f"No populated levels below '{base_rank}' in taxonomy")


def generate_breakdown_query(base_taxon, base_rank, levels, region_key=None):
    """Generate UNION query for hierarchical breakdown.

    Args:
        base_taxon: Name of taxon to break down (e.g., "Asteraceae")
        base_rank: Rank of base taxon (e.g., "family")
        levels: List of ranks to break down to (e.g., ["subfamily", "tribe"])
        region_key: Optional region filter

    Returns:
        Tuple of (query_string, params_list)
    """
    # Sort levels to ensure hierarchical order
    levels = sort_ranks(levels)

    queries = []

    # For each level, create a SELECT with all previous levels + current level
    for i, level in enumerate(levels):
        # Columns: all levels up to current (rest are NULL)
        select_cols = []
        group_cols = []

        for j, l in enumerate(levels):
            if j <= i:
                select_cols.append(l)
                group_cols.append(l)
            else:
                select_cols.append(f"NULL as {l}")

        # Add aggregation columns
        select_cols.extend([
            "SUM(observations.observation_count) as observation_count",
            "COUNT(DISTINCT CASE WHEN taxa.rank = 'species' THEN taxa.id END) as species_count"
        ])

        # Build WHERE clause
        where_parts = [f"{base_rank} = ?"]
        params = [base_taxon]

        # Add NOT NULL checks for all levels we're grouping by
        # Skip this for single-level breakdowns to allow grouping of NULL values
        if len(levels) > 1:
            for col in group_cols:
                where_parts.append(f"{col} IS NOT NULL")

        # Add region filter if specified
        if region_key:
            where_parts.append("observations.region_key = ?")
            params.append(region_key)

        query = f"""
        SELECT {', '.join(select_cols)}
        FROM taxa
        JOIN observations ON observations.taxon_id = taxa.id
        WHERE {' AND '.join(where_parts)}
        GROUP BY {', '.join(group_cols)}
        """

        queries.append((query, params))

    # Combine with UNION ALL
    full_query = " UNION ALL ".join(q for q, _ in queries)

    # Add ORDER BY (NULLs first for subtotals, then by observation count)
    order_cols = [f"{level} NULLS FIRST" for level in levels]
    order_cols.append("observation_count DESC")
    full_query += f" ORDER BY {', '.join(order_cols)}"

    # Flatten params
    all_params = [p for _, params in queries for p in params]

    return full_query, all_params
