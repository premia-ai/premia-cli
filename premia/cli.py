from typing import Literal
import click
from openai import OpenAI
from premia.ai import model
from premia.db import internals, migration
from premia.utils import config, types
from premia.wizard import db_cmd, ai_cmd


@click.version_option("0.0.2", prog_name="premia")
@click.group()
def cli():
    """A cli to setup, manage and interact with financial data infrastructure."""
    pass


@cli.group("config")
def config_group():
    """Access Config information."""
    pass


@config_group.command("ai")
def config_ai():
    """Print AI config to stdout."""
    ai_config = config.config().ai
    if not ai_config:
        click.echo("No AI model set up yet.")
        return

    remote_config_str = ""
    if ai_config.remote:
        remote_config_str = f"""\
Remote:
  OpenAI Details:
    API-Key: {ai_config.remote.api_key}
    Model: {ai_config.remote.model}
"""
    local_config_str = ""
    if ai_config.local:
        local_config_str = f"""\
Local:
  Huggingface Details:
    User: {ai_config.local.user}
    Repo: {ai_config.local.repo}
    Filename: {ai_config.local.filename}
"""

    click.echo(
        f"""\
Preference: {ai_config.preference}
{remote_config_str}{local_config_str}
"""
    )


@cli.group("ai")
def ai_group():
    """Use an LLM to interact with your data infrastructure."""
    pass


@ai_group.group("setup")
def ai_setup():
    """Setup the LLM you want to use with Premia."""


@ai_setup.command("local")
@click.argument("link", type=str)
@click.option(
    "-f",
    "--force",
    default=False,
    is_flag=True,
    help="Force the download of the local model",
)
def ai_setup_local(
    link: str,
    force: bool,
):
    """Setup a local LLM with a huggingface LINK. The link should point to a model's GGUF file."""

    model.get_local_model_path(link, force)


@ai_setup.command("remote")
@click.argument("api_key", type=str)
@click.option(
    "-m",
    "--model",
    "model_name",
    type=str,
    help="The OpenAI model you would like to use",
    default="gpt-3.5-turbo",
)
def ai_setup_remote(
    api_key: str,
    model_name: str,
):
    """Setup a remote LLM with an OpenAI API_KEY."""
    model.setup_remote_model(api_key, model_name)


@ai_group.command("preference")
@click.argument("ai_type", type=click.Choice(["local", "remote"]))
def ai_set_preference(preference: Literal["local", "remote"]):
    """Set the preference on whether to use a local or remote model. Check your current setup with `config ai`"""
    config.update_ai_config(preference)


@ai_group.command("query")
@click.argument("prompt")
@click.option(
    "-v",
    "--verbose",
    default=False,
    is_flag=True,
    help="Print the execution of the LLM",
)
def ai_query(prompt: str, verbose: bool, remote: bool):
    """Query your data with the help of an LLM."""
    ai_config = config.config().ai
    if not ai_config:
        raise types.AiError("Please setup an AI model before running a query.")

    if ai_config.preference == "remote" and ai_config.remote:
        client = OpenAI(api_key=ai_config.remote.api_key)
        completion = model.create_remote_completion(prompt, client)
    else:
        try:
            completion = model.create_local_completion(prompt, verbose=verbose)
        except types.ConfigError as e:
            click.secho(e, fg="red")
            raise click.Abort()

    ai_cmd.execute_completion(completion)


@cli.group("db")
def db_group():
    """Setup and manage your data infrastructure."""
    pass


@db_group.command("schema")
def db_schema():
    """Print schema of your database."""
    try:
        db_schema = internals.inspect()
        click.echo(db_schema)
    except Exception as e:
        click.secho(e, fg="red")
        raise click.Abort()


@db_group.command("tables")
def db_tables():
    """List tables in your database."""
    try:
        tables = internals.tables()
        click.echo("\n".join(tables))
    except ValueError as e:
        click.secho(e, fg="red")
        raise click.Abort()


@db_group.command("setup")
@click.option(
    "-p",
    "--path",
    type=str,
    help="A path to where your database is located",
)
def db_setup(path: str):
    """Connect Premia to a database or create a default database."""
    if not path:
        config.update_db_config()
        migration.connect()
        click.secho(
            f"Successfully set up new database at: {config.DEFAULT_DATABASE_PATH}",
            fg="green",
        )
    else:
        config.update_db_config(path)
        click.secho(
            f"Successfully connected to database at: {path}",
            fg="green",
        )


@db_group.command("init")
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


@db_group.command("import")
def db_import():
    """
    Import data from common financial data vendors.
    """
    try:
        db_cmd.seed()
    except Exception as e:
        click.secho(e, fg="red")
        raise click.Abort()


@db_group.command("table")
@click.argument("table_name")
def db_table(table_name: str):
    con = migration.connect()
    con.sql(f"FROM {table_name};").show()


@db_group.group("add")
def db_add():
    """
    Add database tables for a given instrument type. Only use this command when the database is already setup. Prefer `init` otherwise.
    """
    pass


@db_add.command("stocks")
@click.option(
    "-f",
    "--frequency",
    help="The frequency the candle data has.",
    default=None,
    type=click.Choice(
        [
            types.Timespan.SECOND.value,
            types.Timespan.MINUTE.value,
            types.Timespan.HOUR.value,
            types.Timespan.DAY.value,
        ]
    ),
)
@click.option(
    "--candles-path",
    default=None,
    help="File path for the stock candles data stored in a CSV to seed the new table.",
)
@click.option(
    "--companies-path",
    default=None,
    help="File path for the company data stored in a CSV to seed the new table.",
)
def add_stocks(
    frequency: str | None, candles_path: str | None, companies_path: str | None
):
    """
    Add database tables for stocks.
    """
    add_instrument(
        types.InstrumentType.STOCKS, frequency, candles_path, companies_path
    )


@db_add.command("options")
@click.option(
    "-f",
    "--frequency",
    help="The frequency the candle data has.",
    default=None,
    type=click.Choice(
        [
            types.Timespan.SECOND.value,
            types.Timespan.MINUTE.value,
            types.Timespan.HOUR.value,
            types.Timespan.DAY.value,
        ]
    ),
)
@click.option(
    "--candles-path",
    default=None,
    help="File path for the option candles data stored in a CSV to seed the new table.",
)
@click.option(
    "--contracts-path",
    default=None,
    help="File path for the contract data stored in a CSV to seed the new table.",
)
def add_options(
    frequency: str | None, candles_path: str | None, contracts_path: str | None
):
    """
    Add database tables for options.
    """
    add_instrument(
        types.InstrumentType.OPTIONS, frequency, candles_path, contracts_path
    )


def add_instrument(
    instrument: types.InstrumentType,
    frequency: str | None,
    candles_path: str | None,
    metadata_path: str | None,
):
    if config.config().instruments.get(instrument):
        click.secho(
            f"{instrument.value.capitalize()} have already been setup.",
            fg="red",
        )
        raise click.Abort()

    if frequency:
        timespan = types.Timespan(frequency)
    else:
        timespan = None

    db_cmd.add_instrument_migrations(
        instrument, timespan, allow_prompts=(not timespan)
    )
    migration.apply_all(migration.connect(), config.migrations_dir())

    if candles_path and metadata_path:
        db_cmd.import_from_csv(instrument, candles_path, metadata_path)

    click.secho(
        f"Finished setting up {instrument.value} for your system.", fg="green"
    )
