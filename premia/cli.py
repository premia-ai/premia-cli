import os
import click
from openai import OpenAI
from premia.ai import model
from premia.db import internals, migration
from premia.utils import config, types
from premia.wizard import db_cmd, ai_cmd


@click.version_option("0.0.1", prog_name="premia")
@click.group()
def cli():
    """A cli to setup, manage and interact with financial data infrastructure."""
    pass


@cli.group()
def ai():
    """Use an LLM to interact with your data infrastructure."""
    pass


@ai.command("init")
@click.option("-f", "--force", default=False, is_flag=True)
@click.option(
    "-r",
    "--repo",
    help="The name of a model's huggingface repo (including the username)",
)
@click.option(
    "-f", "--file", help="The file name inside the repo you want to download"
)
def ai_init(force: bool, repo: str, file: str):
    """Initialize an open source LLM on your machine."""

    if (repo and not file) or (file and not repo):
        click.secho(
            "Error: You need to define both a repo and a file",
            err=True,
            fg="red",
        )
        raise click.Abort()

    model.init(force=force, model_repo=repo, model_file=file)


@ai.command()
@click.argument("prompt")
@click.option(
    "-v",
    "--verbose",
    default=False,
    is_flag=True,
    help="Print the execution of the LLM",
)
@click.option(
    "-r",
    "--remote",
    default=False,
    is_flag=True,
    help="Use a remotely hosted LLM",
)
def query(prompt: str, verbose: bool, remote: bool):
    """Query your data with the help of an LLM."""
    if remote:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        completion = model.create_remote_completion(prompt, client)
    else:
        completion = model.create_local_completion(prompt, verbose=verbose)

    ai_cmd.execute_completion(completion)


@cli.group()
def db():
    """Setup and manage your data infrastructure."""
    pass


@db.command()
def schema():
    """Print schema of your database."""
    try:
        db_schema = internals.inspect()
        click.echo(db_schema)
    except Exception as e:
        click.secho(e, fg="red")
        raise click.Abort()


@db.command()
def tables():
    """List tables in your database."""
    try:
        tables = internals.tables()
        click.echo("\n".join(tables))
    except ValueError as e:
        click.secho(e, fg="red")
        raise click.Abort()


@db.command("init")
def db_init():
    """Initialize a financial database."""
    config.setup_config_dir()

    try:
        db_cmd.setup()
    except Exception as e:
        click.secho(e, fg="red")
        raise click.Abort()

    if not click.confirm("Do you want to seed the db?"):
        return

    try:
        db_cmd.seed()
    except Exception as e:
        click.secho(e, fg="red")
        raise click.Abort()


@db.command("import")
def db_import():
    """
    Import data from common financial data vendors.
    """
    try:
        db_cmd.seed()
    except Exception as e:
        click.secho(e, fg="red")
        raise click.Abort()


@db.command()
@click.argument("table_name")
def show(table_name: str):
    con = migration.connect()
    con.sql(f"FROM {table_name};").show()


@db.command("add")
@click.argument(
    "instrument_type",
    type=click.Choice(
        [types.InstrumentType.STOCKS.value, types.InstrumentType.OPTIONS.value]
    ),
)
def db_add(instrument_type: str):
    """
    Add database tables for a given instrument type. Only use this command when the database is already setup. Prefer `init` otherwise.
    """
    config_file_data = config.config()

    if config_file_data.instruments.get(instrument_type):
        click.secho(
            f"{instrument_type.capitalize()} have already been setup.", fg="red"
        )
        raise click.Abort()

    db_cmd.add_instrument_migrations(types.InstrumentType(instrument_type))
    migration.apply_all(migration.connect(), config.migrations_dir())
    click.echo(f"Finished setting up {instrument_type} for your system.")
