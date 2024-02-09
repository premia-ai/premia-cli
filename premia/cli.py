import os
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


@cli.group()
def ai():
    """Use an LLM to interact with your data infrastructure."""
    pass


@ai.command("init")
@click.option(
    "-l",
    "--link",
    help="The link of a model's GGUF file hosted on huggingface.",
)
@click.option(
    "-f",
    "--force",
    default=False,
    is_flag=True,
    help="Force the download of the model",
)
def ai_init(force: bool, link: str):
    """Initialize an open source LLM on your machine."""

    if link:
        model.init(link, force)
    else:
        model.init(force=force)


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
        try:
            completion = model.create_local_completion(prompt, verbose=verbose)
        except types.ConfigError as e:
            click.secho(e, fg="red")
            raise click.Abort()

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
def table(table_name: str):
    con = migration.connect()
    con.sql(f"FROM {table_name};").show()


@db.group("add")
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
