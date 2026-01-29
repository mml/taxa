"""Tests for schema creation."""
import sqlite3
import pytest
from taxa.schema import create_schema
from taxa.taxonomy import TAXONOMIC_RANKS


def test_schema_has_all_rank_columns():
    """Test that taxa table has columns for all taxonomic ranks."""
    conn = sqlite3.connect(':memory:')
    create_schema(conn)

    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(taxa)")
    columns = {row[1] for row in cursor.fetchall()}

    # All ranks from TAXONOMIC_RANKS should be columns
    for rank in TAXONOMIC_RANKS:
        assert rank in columns, f"Missing column for rank: {rank}"

    conn.close()


def test_schema_rank_order_matches_taxonomy():
    """Test that rank columns appear in same order as TAXONOMIC_RANKS."""
    conn = sqlite3.connect(':memory:')
    create_schema(conn)

    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(taxa)")
    all_columns = [row[1] for row in cursor.fetchall()]

    # Extract rank columns in table order
    rank_columns = [col for col in all_columns if col in TAXONOMIC_RANKS]

    # Should match TAXONOMIC_RANKS order
    assert rank_columns == TAXONOMIC_RANKS

    conn.close()
