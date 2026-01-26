"""Command-line interface for taxa tool."""
import click
import subprocess
import sqlite3
import sys
from pathlib import Path
from taxa.config import Config, ConfigError
from taxa.sync import sync_database


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
    click.echo(f"Searching places for: {query}")
    click.echo("(Not yet implemented)")


@search.command()
@click.argument('query')
def taxa(query):
    """Search for taxon IDs."""
    click.echo(f"Searching taxa for: {query}")
    click.echo("(Not yet implemented)")


@main.command()
def info():
    """Show database info and stats."""
    click.echo("Database info:")
    click.echo("(Not yet implemented)")


if __name__ == '__main__':
    main()
