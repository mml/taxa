"""Command-line interface for taxa tool."""
import click
import sys
from pathlib import Path


@click.group()
def main():
    """Query iNaturalist regional flora data via SQL."""
    pass


@main.command()
@click.argument('config', default='config.yaml')
@click.option('--timeout', type=int, default=0, help='Timeout in seconds (0 = no timeout)')
@click.option('--dry-run', is_flag=True, help='Estimate only, do not fetch/store')
def sync(config, timeout, dry_run):
    """Sync data from iNaturalist API to database."""
    click.echo(f"Syncing from config: {config}")
    click.echo("(Not yet implemented)")


@main.command()
@click.argument('query', required=False)
def query(query):
    """Run SQL query against database or open interactive shell."""
    if query:
        click.echo(f"Running query: {query}")
        click.echo("(Not yet implemented)")
    else:
        click.echo("Opening interactive SQLite shell...")
        click.echo("(Not yet implemented)")


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
