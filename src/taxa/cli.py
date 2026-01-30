"""Command-line interface for taxa tool."""
import click
import subprocess
import sqlite3
import sys
from pathlib import Path
import pyinaturalist
from taxa.config import Config, ConfigError
from taxa.sync import sync_database
from taxa.breakdown import find_taxon_rank, generate_breakdown_query, find_first_populated_rank
from taxa.taxonomy import get_next_ranks, validate_rank_sequence
from taxa.completion import generate_completion_cache, write_completion_cache, get_cache_path
from taxa.formatting import output_results
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
@click.option(
    '--format',
    type=click.Choice(['auto', 'table', 'csv'], case_sensitive=False),
    default='auto',
    help='Output format (default: auto-detect)'
)
@click.option('--show-null', is_flag=True, help='Show NULL instead of empty strings')
def query(query, database, format, show_null):
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

            # Format and output results
            if cursor.description:
                headers = [desc[0] for desc in cursor.description]
                output_results(headers, results, format=format, show_null=show_null)

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
@click.option(
    '--format',
    type=click.Choice(['auto', 'table', 'csv'], case_sensitive=False),
    default='auto',
    help='Output format (default: auto-detect)'
)
@click.option('--show-null', is_flag=True, help='Show NULL instead of empty strings')
def breakdown(taxon_name, levels, region, database, format, show_null):
    """Break down a taxon into hierarchical levels with observation counts."""
    if not Path(database).exists():
        click.echo(f"ERROR: Database not found: {database}", err=True)
        click.echo("Run 'taxa sync' first to create the database")
        sys.exit(1)

    try:
        conn = sqlite3.connect(database)

        # Auto-detect taxon rank
        base_rank = find_taxon_rank(conn, taxon_name)

        # Parse levels or use smart default
        if levels:
            # Explicit levels - use as-is
            level_list = [level.strip() for level in levels.split(',')]
            validate_rank_sequence(base_rank, level_list)
        else:
            # Smart default - find first populated rank
            try:
                populated_rank, expected_rank = find_first_populated_rank(
                    conn, taxon_name, base_rank
                )
                level_list = [populated_rank]

                # Show notice if we skipped ranks
                if populated_rank != expected_rank:
                    click.echo(
                        f"[Notice: {expected_rank} unpopulated, showing {populated_rank} instead]",
                        err=True
                    )
            except ValueError as e:
                click.echo(f"ERROR: {e}", err=True)
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

        # Format and output results
        headers = [desc[0] for desc in cursor.description]
        output_results(headers, results, format=format, show_null=show_null)

    except ValueError as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
    except sqlite3.Error as e:
        click.echo(f"ERROR: Database error: {e}", err=True)
        sys.exit(1)
    finally:
        conn.close()


@main.group()
def completion():
    """Manage shell completions."""
    pass


@completion.command('generate-cache')
@click.option('--database', '-d', default='flora.db', help='Database file path')
def generate_cache(database):
    """Generate completion cache from database."""
    try:
        db_path = Path(database)
        cache_data = generate_completion_cache(db_path)
        cache_path = get_cache_path(database)
        write_completion_cache(cache_data, cache_path)

        click.echo(f"Generated completion cache: {cache_path}")
        click.echo(f"  Taxa: {cache_data['metadata']['taxa_count']}")
        click.echo(f"  Regions: {cache_data['metadata']['region_count']}")
    except FileNotFoundError as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"ERROR: Failed to generate cache: {e}", err=True)
        sys.exit(1)


@completion.command()
@click.option('--shell', type=click.Choice(['zsh']), default='zsh', help='Shell type')
def install(shell):
    """Install shell completion for taxa."""
    try:
        config_dir = Path.home() / '.config' / 'taxa' / 'completions'
        config_dir.mkdir(parents=True, exist_ok=True)

        completion_script = config_dir / '_taxa'

        # Read template from package
        template_path = Path(__file__).parent / 'completion_template.zsh'
        completion_content = template_path.read_text()

        # Write completion script
        completion_script.write_text(completion_content)

        click.echo(f"Installed completion script: {completion_script}")

        # Generate initial cache if database exists
        default_db = Path('flora.db')
        if default_db.exists():
            try:
                cache_data = generate_completion_cache(default_db)
                cache_path = get_cache_path('flora.db')
                write_completion_cache(cache_data, cache_path)
                click.echo(f"Generated initial cache: {cache_path}")
            except Exception as e:
                click.echo(f"Warning: Could not generate cache: {e}", err=True)

        click.echo("\nTo enable completions, add to your ~/.zshrc:")
        click.echo("  fpath=(~/.config/taxa/completions $fpath)")
        click.echo("  autoload -Uz compinit && compinit")
        click.echo("\nThen reload your shell:")
        click.echo("  exec zsh")
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
