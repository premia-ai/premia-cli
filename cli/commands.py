import sys
from datetime import datetime
from typing import Literal
import click
import premia
from premia.config._internal.config import DEFAULT_DATABASE_PATH
from . import utils

TIMESPAN_CHOICES: list[premia.Timespan] = [
    "second",
    "minute",
    "hour",
    "day",
]

INSTRUMENT_CHOICES: list[premia.InstrumentType] = [
    "stocks",
    "options",
]

FEATURE_NAME_CHOICES = list(premia.db.features())

PROVIDER_CHOICES: list[premia.data.ProviderType] = ["csv"]
AI_MODEL_CHOICES: list[premia.ModelType] = ["local", "remote"]


@click.version_option("0.0.2", prog_name="premia")
@click.group()
def premia_cli():
    """Setup, manage and interact with financial data infrastructure."""
    pass


@premia_cli.group("config")
def config_group():
    """Setup and interact with Premia's configuration."""
    pass


@config_group.command("setup")
def config_setup():
    """Setup Premia."""
    try:
        premia.config.setup()
        click.secho("Successfully setup Premia's configuration.", fg="green")
    except Exception as e:
        click.secho(e, fg="red", err=True)


@config_group.group("get", invoke_without_command=True)
@click.pass_context
@click.option(
    "-j",
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Returns the config as a JSON string.",
)
def config_get_group(ctx, as_json: bool):
    """Print configuration to stdout.premia/premia/config/_internal/types.py"""
    if ctx.invoked_subcommand is not None:
        return

    try:
        fmt = "json" if as_json else "yaml"
        click.echo(premia.config.get_str(fmt=fmt))
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@config_get_group.command("ai")
@click.option(
    "-j",
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Returns the config as a JSON string.",
)
def config_get_ai(as_json: bool):
    """Print AI config to stdout."""
    try:
        fmt = "json" if as_json else "yaml"
        click.echo(premia.config.get_ai_str(fmt=fmt))
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@config_get_group.command("db")
@click.option(
    "-j",
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Returns the config as a JSON string.",
)
def config_get_db(as_json: bool):
    """Print DB config to stdout."""
    try:
        fmt = "json" if as_json else "yaml"
        click.echo(premia.config.get_db_str(fmt=fmt))
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@config_get_group.command("providers")
@click.option(
    "-j",
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Returns the config as a JSON string.",
)
def config_get_providers(as_json: bool):
    """Print data providers config to stdout."""
    try:
        fmt = "json" if as_json else "yaml"
        click.echo(premia.config.get_providers_str(fmt=fmt))
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@config_group.group("set")
def config_set_group():
    """Set configuration data"""
    pass


@config_set_group.command("provider")
@click.argument("provider", type=click.Choice(["polygon", "twelvedata"]))
@click.argument("api_key")
def config_set_provider(
    provider: Literal["polygon", "twelvedata"], api_key: str
):
    """Set the API-Key of a data provider."""
    try:
        if provider == "polygon":
            premia.config.set_provider_polygon(api_key)
            click.secho("Successfully set Polygon API-Key.", fg="green")
        elif provider == "twelvedata":
            premia.config.set_provider_twelvedata(api_key)
            click.secho("Successfully set TwelveData API-Key.", fg="green")
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@config_set_group.group("ai")
def config_set_ai_group():
    """Set the AI model you want to use with Premia."""


@config_set_ai_group.command("local")
@click.argument("link", type=str)
@click.option(
    "-f",
    "--force",
    default=False,
    is_flag=True,
    help="Force the download of the local model",
)
def config_set_ai_local(
    link: str,
    force: bool,
):
    """Set local AI model with a huggingface LINK. The link should point to a model's GGUF file."""

    try:
        premia.config.set_ai_local(link, force)
        click.secho("Successfully set local AI model.", fg="green")
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@config_set_ai_group.command("remote")
@click.argument("api_key")
@click.option(
    "-m",
    "--model",
    "model_name",
    type=str,
    help="The OpenAI model you would like to use",
    default="gpt-3.5-turbo",
)
def config_set_ai_remote(
    api_key: str,
    model_name: str,
):
    """Set remote AI model with an OpenAI API_KEY."""
    try:
        premia.config.set_ai_remote(api_key, model_name)
        click.secho("Successfully set remote AI model.", fg="green")
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@config_set_ai_group.command("preference")
@click.argument("model_type", type=click.Choice(AI_MODEL_CHOICES))
def config_set_ai_preference(model_type: premia.ModelType):
    """Select which model you want to use for your queries."""
    try:
        premia.config.update_ai(model_type)
        click.secho(
            f"Premia will use {model_type} model from now on.",
            fg="green",
        )
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@config_group.group("remove")
def config_remove_group():
    """Remove values from the configuration."""
    pass


@config_remove_group.command("ai")
@click.argument("model_type", type=click.Choice(AI_MODEL_CHOICES))
def config_remove_ai(model_type: premia.ModelType):
    """Remove a set up AI model."""
    try:
        premia.config.remove_ai(model_type)
        click.secho(f"Successfully removed {model_type} AI model.", fg="green")
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@premia_cli.group("ai")
def ai_group():
    """Use an AI model to interact with your data infrastructure."""
    pass


@ai_group.command("query")
@click.argument("prompt")
@click.option(
    "-p",
    "--persist",
    is_flag=True,
    default=False,
    help="Persist the result to your DB.",
)
@click.option(
    "-v",
    "--verbose",
    default=False,
    is_flag=True,
    help="Print the execution of the AI model. This option only works with the local model.",
)
@click.option(
    "-r",
    "--rows",
    type=int,
    help="Maximal number of rows displayed. Defaults to 10. For all rows use -1",
    default=10,
)
@click.option(
    "-j",
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print result as JSON.",
)
@click.option(
    "-c",
    "--csv",
    "as_csv",
    is_flag=True,
    default=False,
    help="Print result as CSV.",
)
def ai_query(
    prompt: str,
    persist: bool,
    verbose: bool,
    rows: int,
    as_json: bool,
    as_csv: bool,
):
    """Query your data with the help of an AI model."""
    try:
        result = premia.ai.query(prompt, persist=persist, verbose=verbose)
        utils.echo_df(result.data, rows=rows, as_json=as_json, as_csv=as_csv)
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@ai_group.command("ask")
@click.argument("prompt")
@click.option(
    "-v",
    "--verbose",
    default=False,
    is_flag=True,
    help="Print the execution of the AI model. This option only works with the local model.",
)
def ai_ask(prompt: str, verbose: bool):
    """Ask an AI model about your financial data system."""
    try:
        utils.echo_iter(premia.ai.ask_iter(prompt, verbose))
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@premia_cli.group("db")
def db_group():
    """Setup and manage your data infrastructure."""
    pass


@db_group.command("connect")
@click.option(
    "-p",
    "--path",
    help="The path to your database file. If no path is added a new DB is created.",
)
def db_setup(path: str | None):
    """Connect Premia to a database or create a default database."""
    try:
        premia.db.connect(create_if_missing=True, path=path)
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)

    click.secho(
        f"Successfully set up new database at: {path or DEFAULT_DATABASE_PATH}",
        fg="green",
    )


@db_group.command("schema")
def db_schema():
    """Print schema of your database."""
    try:
        click.echo(premia.db.schema())
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@db_group.command("tables")
@click.option(
    "-j",
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print result as JSON.",
)
@click.option(
    "-c",
    "--csv",
    "as_csv",
    is_flag=True,
    default=False,
    help="Print result as CSV.",
)
def db_tables(as_json: bool, as_csv: bool):
    """Print tables of your database to stdout."""
    try:
        tables = premia.db.tables()
        if tables:
            utils.echo_list(tables, as_json=as_json, as_csv=as_csv)
        else:
            click.secho("No tables set up yet.", fg="red", err=True)
            sys.exit(1)
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@db_group.command("table")
@click.argument("table_name")
@click.option(
    "-r",
    "--rows",
    type=int,
    help="Maximal number of rows displayed. Defaults to 10. For all rows use -1",
    default=10,
)
@click.option(
    "-j",
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print result as JSON.",
)
@click.option(
    "-c",
    "--csv",
    "as_csv",
    is_flag=True,
    default=False,
    help="Print result as CSV.",
)
def db_table(table_name: str, rows: int, as_json: bool, as_csv: bool):
    """Print a preview of the table's content to stdout."""
    try:
        df = premia.db.table(table_name)
        utils.echo_df(df, rows=rows, as_json=as_json, as_csv=as_csv)
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@db_group.command("features")
@click.option(
    "-j",
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print result as JSON.",
)
@click.option(
    "-c",
    "--csv",
    "as_csv",
    is_flag=True,
    default=False,
    help="Print result as CSV.",
)
def db_features(as_json: bool, as_csv: bool):
    """Prints a list of available features to stdout."""
    try:
        utils.echo_list(
            list(premia.db.features()), as_json=as_json, as_csv=as_csv
        )
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@db_group.command("set")
@click.argument(
    "instrument",
    type=click.Choice(INSTRUMENT_CHOICES),
)
@click.option(
    "-r",
    "--raw-frequency",
    "timespan",
    help="The frequency the raw candle data has.",
    type=click.Choice(TIMESPAN_CHOICES),
)
@click.option(
    "-a",
    "--aggregate-frequency",
    "aggregate_timespans",
    multiple=True,
    help="Create aggregate tables based on raw candle data. Value needs to be bigger than frequency",
    type=click.Choice(TIMESPAN_CHOICES),
)
@click.option(
    "-f",
    "--feature",
    "feature_names",
    multiple=True,
    help="Create feature tables based on original data table",
    type=click.Choice(FEATURE_NAME_CHOICES),
)
def db_set_instrument(
    instrument: premia.InstrumentType,
    timespan: premia.Timespan | None,
    aggregate_timespans: list[premia.Timespan],
    feature_names: list[str],
):
    """
    Set database tables for a given instrument. Only use this command when the database is already setup.
    """
    unique_aggregate_timespans = set(aggregate_timespans)
    unique_feature_names = set(feature_names)
    try:
        premia.db.set_instrument(
            instrument,
            timespan,
            unique_aggregate_timespans,
            unique_feature_names,
        )
        # TODO: Differentiate in the message more what actually happened.
        click.secho(f"Successfully set {instrument}.", fg="green")
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@db_group.command("remove")
@click.argument(
    "instrument",
    type=click.Choice(INSTRUMENT_CHOICES),
)
@click.option(
    "-a",
    "--aggregate-frequency",
    "aggregate_timespans",
    multiple=True,
    help="Remove aggregate tables that you have created previously.",
    type=click.Choice(TIMESPAN_CHOICES),
)
@click.option(
    "-f",
    "--feature",
    "feature_names",
    multiple=True,
    help="Remove feature tables that you have created previously.",
    type=click.Choice(FEATURE_NAME_CHOICES),
)
def db_remove_instrument(
    instrument: premia.InstrumentType,
    aggregate_timespans: list[premia.Timespan],
    feature_names: list[str],
):
    """Remove an instrument that you have set up with Premia."""
    unique_feature_names = set(feature_names)
    unique_aggregate_timespans = set(aggregate_timespans)
    try:
        premia.db.remove_instrument(
            instrument, unique_aggregate_timespans, unique_feature_names
        )
        # TODO: Differentiate in the message more what actually happened.
        click.secho(f"Successfully removed {instrument}.", fg="green")
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@db_group.command("reset")
@click.option(
    "-y",
    "--yes",
    default=False,
    is_flag=True,
    help="Reset the database without being prompted.",
)
def db_reset(yes: bool):
    """Reset your database."""
    if yes or click.confirm("Are you sure you want to reset your database?"):
        try:
            premia.db.reset()
            click.secho("Successfully reset the database.", fg="green")
        except Exception as e:
            click.secho(e, fg="red", err=True)
            sys.exit(1)


@db_group.command("purge")
def db_purge():
    """Remove all cached ai responses from your database."""
    try:
        premia.db.purge()
        click.secho("Successfully removed cached AI responses.", fg="green")
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@premia_cli.group("data")
def data_group():
    """Download and import market data"""
    pass


@data_group.group("yfinance")
def data_yfinance_group():
    """Download market data from yfinance"""
    pass


@data_yfinance_group.command("stocks")
@click.argument("symbol")
@click.option(
    "-s",
    "--start",
    type=click.DateTime(),
    help="Start date (in UTC) of the data. Can have the following formats: '2008-09-15', '2008-09-15T09:30:00', '2008-09-15 09:30:00'",
)
@click.option(
    "-e",
    "--end",
    type=click.DateTime(),
    default=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    help="End date (in UTC) of the data. Defaults to the current moment. Can have the following formats: '2008-09-15', '2008-09-15T09:30:00', '2008-09-15 09:30:00'",
)
@click.option(
    "-p",
    "--persist",
    is_flag=True,
    default=False,
    help="Persist the result to your DB.",
)
@click.option(
    "-r",
    "--rows",
    type=int,
    help="Maximal number of rows displayed. Defaults to 10. For all rows use -1",
    default=10,
)
@click.option(
    "-j",
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print result as JSON.",
)
@click.option(
    "-c",
    "--csv",
    "as_csv",
    is_flag=True,
    default=False,
    help="Print result as CSV.",
)
def data_yfinance_stocks(
    symbol: str,
    start: datetime,
    end: datetime,
    persist: bool,
    rows: int,
    as_json: bool,
    as_csv: bool,
):
    try:
        df = premia.data.yfinance.stocks(symbol, start, end, persist)
        utils.echo_df(df, rows=rows, as_json=as_json, as_csv=as_csv)
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@data_group.group("twelvedata")
def data_twelvedata_group():
    """Download market data from twelvedata"""
    pass


@data_twelvedata_group.command("stocks")
@click.argument("symbol")
@click.option(
    "-s",
    "--start",
    type=click.DateTime(),
    help="Start date (in UTC) of the data. Can have the following formats: '2008-09-15', '2008-09-15T09:30:00', '2008-09-15 09:30:00'",
)
@click.option(
    "-e",
    "--end",
    type=click.DateTime(),
    default=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    help="End date (in UTC) of the data. Defaults to the current moment. Can have the following formats: '2008-09-15', '2008-09-15T09:30:00', '2008-09-15 09:30:00'",
)
@click.option(
    "-p",
    "--persist",
    is_flag=True,
    default=False,
    help="Persist the result to your DB.",
)
@click.option(
    "-r",
    "--rows",
    type=int,
    help="Maximal number of rows displayed. Defaults to 10. For all rows use -1",
    default=10,
)
@click.option(
    "-j",
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print result as JSON.",
)
@click.option(
    "-c",
    "--csv",
    "as_csv",
    is_flag=True,
    default=False,
    help="Print result as CSV.",
)
def data_twelvedata_stocks(
    symbol: str,
    start: datetime,
    end: datetime,
    persist: bool,
    rows: int,
    as_json: bool,
    as_csv: bool,
):
    try:
        df = premia.data.twelvedata.stocks(symbol, start, end, persist)
        utils.echo_df(df, rows=rows, as_json=as_json, as_csv=as_csv)
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@data_group.group("polygon")
def data_polygon_group():
    """Download market data from polygon"""
    pass


@data_polygon_group.command("stocks")
@click.argument("symbol")
@click.option(
    "-s",
    "--start",
    type=click.DateTime(),
    help="Start date (in UTC) of the data. Can have the following formats: '2008-09-15', '2008-09-15T09:30:00', '2008-09-15 09:30:00'",
)
@click.option(
    "-e",
    "--end",
    type=click.DateTime(),
    default=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    help="End date (in UTC) of the data. Defaults to the current moment. Can have the following formats: '2008-09-15', '2008-09-15T09:30:00', '2008-09-15 09:30:00'",
)
@click.option(
    "-p",
    "--persist",
    is_flag=True,
    default=False,
    help="Persist the result to your DB.",
)
@click.option(
    "-r",
    "--rows",
    type=int,
    help="Maximal number of rows displayed. Defaults to 10. For all rows use -1",
    default=10,
)
@click.option(
    "-j",
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print result as JSON.",
)
@click.option(
    "-c",
    "--csv",
    "as_csv",
    is_flag=True,
    default=False,
    help="Print result as CSV.",
)
def data_polygon_stocks(
    symbol: str,
    start: datetime,
    end: datetime,
    persist: bool,
    rows: int,
    as_json: bool,
    as_csv: bool,
):
    try:
        df = premia.data.polygon.stocks(symbol, start, end, persist)
        utils.echo_df(df, rows=rows, as_json=as_json, as_csv=as_csv)
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@data_polygon_group.command("options")
@click.option(
    "-s",
    "--start",
    type=click.DateTime(),
    help="Start date (in UTC) of the data. Can have the following formats: '2008-09-15', '2008-09-15T09:30:00', '2008-09-15 09:30:00'",
)
@click.option(
    "-e",
    "--end",
    type=click.DateTime(),
    default=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    help="End date (in UTC) of the data. Defaults to the current moment. Can have the following formats: '2008-09-15', '2008-09-15T09:30:00', '2008-09-15 09:30:00'",
)
@click.option(
    "-p",
    "--persist",
    is_flag=True,
    default=False,
    help="Persist the result to your DB.",
)
@click.option(
    "-r",
    "--rows",
    type=int,
    help="Maximal number of rows displayed. Defaults to 10. For all rows use -1",
    default=10,
)
@click.option(
    "-j",
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print result as JSON.",
)
@click.option(
    "-c",
    "--csv",
    "as_csv",
    is_flag=True,
    default=False,
    help="Print result as CSV.",
)
def polygon_options(
    symbol: str,
    start: datetime,
    end: datetime,
    persist: bool,
    rows: int,
    as_json: bool,
    as_csv: bool,
):
    try:
        df = premia.data.polygon.options(symbol, start, end, persist)
        utils.echo_df(df, rows=rows, as_json=as_json, as_csv=as_csv)
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)


@data_group.group("csv")
def data_csv_group():
    """Import data using CSV files"""


@data_csv_group.command("copy")
@click.argument("file_path")
@click.option(
    "-t",
    "--table",
    "table_name",
    help="Name of the table the data should be stored in.",
)
@click.option(
    "-r",
    "--rows",
    type=int,
    help="Maximal number of rows displayed. Defaults to 10. For all rows use -1",
    default=10,
)
@click.option(
    "-j",
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print result as JSON.",
)
@click.option(
    "-c",
    "--csv",
    "as_csv",
    is_flag=True,
    default=False,
    help="Print result as CSV.",
)
def data_csv_copy(
    file_path: str,
    table_name: str | None,
    rows: int,
    as_json: bool,
    as_csv: bool,
):
    """Copy data from a CSV and optionally store it in your DB by specifying a table name."""
    try:
        df = premia.data.csv.copy(file_path, table_name)
        utils.echo_df(df, rows=rows, as_json=as_json, as_csv=as_csv)
    except Exception as e:
        click.secho(e, fg="red", err=True)
        sys.exit(1)
