"""Command-line interface for taxa tool."""
import click
import subprocess
import sqlite3
import sys
from pathlib import Path
import pyinaturalist
from taxa.config import Config, ConfigError
from taxa.sync import sync_database
from taxa.breakdown import find_taxon_rank, generate_breakdown_query
from taxa.taxonomy import get_next_ranks, validate_rank_sequence
from pyinaturalist import get_places_autocomplete, get_taxa_autocomplete

# Set user agent to comply with iNaturalist API best practices
pyinaturalist.user_agent = "taxa-flora-query-tool/1.0 (github.com/mml/taxa)"


@click.group()
def main():
    """Query iNaturalist regional flora data via SQL."""
    pass


@main.command()
@click.argument('config', type=click.Path(exists=True), default='config.yaml')
@click.option('--timeout', type=int, default=0, help='Timeout in seconds (0 = no timeout)')
@click.option('--dry-run', is_flag=True, help='Estimate only, do not fetch/store')
def sync(config, timeout, dry_run):
    """Sync data from iNaturalist API to database."""
    try:
        cfg = Config.from_file(Path(config))
        sync_database(cfg, dry_run=dry_run)
    except ConfigError as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\nSync interrupted by user")
        sys.exit(1)


@main.command()
@click.argument('query', required=False)
@click.option('--database', '-d', default='flora.db', help='Database file path')
def query(query, database):
    """Run SQL query against database or open interactive shell."""
    if not Path(database).exists():
        click.echo(f"ERROR: Database not found: {database}", err=True)
        click.echo("Run 'taxa sync' first to create the database")
        sys.exit(1)

    if query:
        # Run single query
        conn = sqlite3.connect(database)
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            results = cursor.fetchall()

            # Print column headers
            if cursor.description:
                headers = [desc[0] for desc in cursor.description]
                click.echo('\t'.join(headers))

            # Print results
            for row in results:
                click.echo('\t'.join(str(val) for val in row))
        except sqlite3.Error as e:
            click.echo(f"ERROR: {e}", err=True)
            sys.exit(1)
        finally:
            conn.close()
    else:
        # Open interactive shell
        subprocess.run(['sqlite3', database])


@main.group()
def search():
    """Search for iNaturalist IDs."""
    pass


@search.command()
@click.argument('query')
def places(query):
    """Search for place IDs."""
    try:
        response = get_places_autocomplete(q=query, per_page=10)
        results = response.get('results', [])

        if not results:
            click.echo(f"No places found for: {query}")
            return

        click.echo(f"Places matching '{query}':\n")
        for place in results:
            click.echo(f"  {place['id']:8d} - {place['display_name']}")
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


@search.command()
@click.argument('query')
def taxa(query):
    """Search for taxon IDs."""
    try:
        response = get_taxa_autocomplete(q=query, per_page=10)
        results = response.get('results', [])

        if not results:
            click.echo(f"No taxa found for: {query}")
            return

        click.echo(f"Taxa matching '{query}':\n")
        for taxon in results:
            common = f" ({taxon.get('preferred_common_name', '')})" if taxon.get('preferred_common_name') else ""
            click.echo(f"  {taxon['id']:8d} - {taxon['name']}{common} [{taxon['rank']}]")
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--database', '-d', default='flora.db', help='Database file path')
def info(database):
    """Show database info and stats."""
    if not Path(database).exists():
        click.echo(f"ERROR: Database not found: {database}", err=True)
        sys.exit(1)

    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    try:
        # Get sync info
        cursor.execute("SELECT value FROM sync_info WHERE key = 'last_sync'")
        row = cursor.fetchone()
        last_sync = row[0] if row else "Never"

        # Get counts
        cursor.execute("SELECT COUNT(*) FROM taxa")
        taxa_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT region_key) FROM observations")
        region_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM observations")
        obs_count = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(observation_count) FROM observations")
        total_obs = cursor.fetchone()[0] or 0

        # Display info
        click.echo(f"Database: {database}")
        click.echo(f"Last sync: {last_sync}")
        click.echo()
        click.echo(f"Taxa: {taxa_count:,}")
        click.echo(f"Regions: {region_count}")
        click.echo(f"Region-taxon combinations: {obs_count:,}")
        click.echo(f"Total observations: {total_obs:,}")

    except sqlite3.Error as e:
        click.echo(f"ERROR: Database error: {e}", err=True)
        sys.exit(1)
    finally:
        conn.close()


@main.command()
@click.argument('taxon_name')
@click.option('--levels', help='Comma-separated list of taxonomic levels to show')
@click.option('--region', help='Filter to specific region')
@click.option('--database', '-d', default='flora.db', help='Database file path')
def breakdown(taxon_name, levels, region, database):
    """Break down a taxon into hierarchical levels with observation counts."""
    if not Path(database).exists():
        click.echo(f"ERROR: Database not found: {database}", err=True)
        click.echo("Run 'taxa sync' first to create the database")
        sys.exit(1)

    try:
        conn = sqlite3.connect(database)

        # Auto-detect taxon rank
        base_rank = find_taxon_rank(conn, taxon_name)

        # Parse levels or use default (next 1 level)
        if levels:
            level_list = [level.strip() for level in levels.split(',')]
            validate_rank_sequence(base_rank, level_list)
        else:
            level_list = get_next_ranks(base_rank, count=1)
            if not level_list:
                click.echo(f"ERROR: No levels below '{base_rank}' in taxonomy", err=True)
                sys.exit(1)

        # Generate and execute query
        query, params = generate_breakdown_query(
            base_taxon=taxon_name,
            base_rank=base_rank,
            levels=level_list,
            region_key=region
        )

        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()

        if not results:
            click.echo(f"No observations found for {taxon_name}" +
                      (f" in region '{region}'" if region else ""))
            sys.exit(0)

        # Print column headers
        if cursor.description:
            headers = [desc[0] for desc in cursor.description]
            click.echo('\t'.join(headers))

        # Print results
        for row in results:
            click.echo('\t'.join(str(val) if val is not None else 'NULL' for val in row))

    except ValueError as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
    except sqlite3.Error as e:
        click.echo(f"ERROR: Database error: {e}", err=True)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
