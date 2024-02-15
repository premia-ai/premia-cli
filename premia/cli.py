import sys
import click
from openai import OpenAI
from premia.ai import model
from premia.db import internals, migration, template, data_import
from premia.utils import config, types, errors
from premia.wizard import db_interactive, ai_cmd

TIMESPAN_CHOICES = [
    types.Timespan.SECOND.value,
    types.Timespan.MINUTE.value,
    types.Timespan.HOUR.value,
    types.Timespan.DAY.value,
]

INSTRUMENT_CHOICES = [
    types.InstrumentType.STOCKS.value,
    types.InstrumentType.OPTIONS.value,
]

PROVIDER_CHOICES = [types.DataProvider.CSV.value]
AI_MODEL_CHOICES: list[types.AiModel] = ["local", "remote"]


def convert_required_instrument_type(
    ctx, param: str, value: str
) -> types.InstrumentType:
    return types.InstrumentType(value)


def convert_required_data_provider(
    ctx, param: str, value: str
) -> types.DataProvider:
    return types.DataProvider(value)


def convert_optional_timespan(
    ctx, param: str, value: str | None
) -> types.Timespan | None:
    if value is None:
        return value
    return types.Timespan(value)


def convert_timespans(
    ctx, param: str, value: list[str]
) -> list[types.Timespan]:
    return [types.Timespan(v) for v in value]


@click.version_option("0.0.2", prog_name="premia")
@click.group()
def cli():
    """A cli to setup, manage and interact with financial data infrastructure."""
    pass


@cli.group("ai")
def ai_group():
    """Use an AI model to interact with your data infrastructure."""
    pass


@ai_group.command("config")
def ai_config():
    """Print AI config to stdout."""
    ai_config = config.get_ai_config_or_raise()

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

    output = f"""\
Preference: {ai_config.preference}
{remote_config_str}{local_config_str}"""

    click.echo(output.strip())


@ai_group.command("remove")
@click.argument("model_type", type=click.Choice(AI_MODEL_CHOICES))
def ai_remove(model_type: types.AiModel):
    """Remove a set up AI model."""
    config.remove_ai_model_config(model_type)
    click.secho(f"Successfully removed {model_type} AI model.", fg="green")


@ai_group.group("add")
def ai_add():
    """Add the AI model you want to use with Premia."""


@ai_add.command("local")
@click.argument("link", type=str)
@click.option(
    "-f",
    "--force",
    default=False,
    is_flag=True,
    help="Force the download of the local model",
)
def ai_add_local(
    link: str,
    force: bool,
):
    """Add a local AI model with a huggingface LINK. The link should point to a model's GGUF file."""

    model.get_local_model_path(link, force)
    config.update_ai_config(model_type="local")
    click.secho("Successfully set up local AI model.", fg="green")


@ai_add.command("remote")
@click.argument("api_key", type=str)
@click.option(
    "-m",
    "--model",
    "model_name",
    type=str,
    help="The OpenAI model you would like to use",
    default="gpt-3.5-turbo",
)
def ai_add_remote(
    api_key: str,
    model_name: str,
):
    """Add a remote AI model with an OpenAI API_KEY."""
    model.setup_remote_model(api_key, model_name)
    config.update_ai_config(model_type="remote")
    click.secho("Successfully set up remote AI model.", fg="green")


@ai_group.command("preference")
@click.argument("model_type", type=click.Choice(AI_MODEL_CHOICES))
def ai_set_preference(model_type: types.AiModel):
    """Select which model you want to use for your queries."""
    try:
        config.update_ai_config(model_type)
    except errors.ConfigError as e:
        click.secho(e, fg="red")
        sys.exit(1)

    click.secho(
        f"Premia will use {model_type} model from now on.",
        fg="green",
    )


@ai_group.command("query")
@click.argument("prompt")
@click.option(
    "-v",
    "--verbose",
    default=False,
    is_flag=True,
    help="Print the execution of the AI model. This option only works with the local model.",
)
def ai_query(prompt: str, verbose: bool):
    """Query your data with the help of an AI model."""
    ai_config = config.get_ai_config()
    if not ai_config:
        click.secho(
            "Please setup an AI model before running a query.", fg="red"
        )
        sys.exit(1)

    if ai_config.preference == "remote" and ai_config.remote:
        client = OpenAI(api_key=ai_config.remote.api_key)
        completion = model.create_remote_completion(prompt, client)
    else:
        try:
            completion = model.create_local_completion(prompt, verbose=verbose)
        except errors.ConfigError as e:
            click.secho(e, fg="red")
            sys.exit(1)

    ai_cmd.execute_completion(completion)


@cli.group("db")
def db_group():
    """Setup and manage your data infrastructure."""
    pass


@db_group.command("config")
def db_config():
    """Print DB config to stdout."""
    db_config = config.get_db_config_or_raise()

    instruments = ""
    for instrument, instrument_config in db_config.instruments.items():
        if not instruments:
            instruments = "Instruments:\n"

        instruments = (
            instruments
            + f"""\
  {instrument.value.capitalize()}:
    Metadata Table: {instrument_config.metadata_table}
    Raw Data Timespan: {instrument_config.timespan.value}
"""
        )

        if len(instrument_config.aggregate_timespans):
            aggregate_timespan_values = [
                a.value for a in instrument_config.aggregate_timespans
            ]
            instruments = (
                instruments
                + f"""\
    Aggregate Timespans: {', '.join(aggregate_timespan_values)}
"""
            )

        if len(instrument_config.feature_names):
            instruments = (
                instruments
                + f"""\
    Features: {', '.join(instrument_config.feature_names)}
"""
            )

    output = f"""\
Type: {db_config.type}
{instruments}"""

    click.echo(output.strip())


@db_group.command("schema")
def db_schema():
    """Print schema of your database."""
    try:
        db_schema = internals.inspect()
        click.echo(db_schema)
    except Exception as e:
        click.secho(e, fg="red")
        sys.exit(1)


@db_group.command("tables")
def db_tables():
    """List tables in your database."""
    try:
        tables = internals.tables()
        if tables:
            click.echo("\n".join(tables))
        else:
            click.echo("No tables set up yet.")
    except ValueError as e:
        click.secho(e, fg="red")
        sys.exit(1)


@db_group.command("setup")
@click.option(
    "-p",
    "--path",
    help="A path to where your database is located",
)
def db_setup(path: str | None):
    """Connect Premia to a database or create a default database."""
    if not path:
        db_config = config.create_db_config()
        migration.connect(create_if_missing=True)
        click.secho(
            f"Successfully set up new database at: {db_config.path}",
            fg="green",
        )


@db_group.command("init")
def db_init():
    """Initialize a financial database."""
    config.setup_config_dir()

    try:
        db_interactive.setup()
    except Exception as e:
        click.secho(e, fg="red")
        sys.exit(1)

    if not click.confirm("Do you want to seed the db?"):
        return

    try:
        db_interactive.seed()
    except Exception as e:
        click.secho(e, fg="red")
        sys.exit(1)


@db_group.command("import")
@click.argument(
    "instrument",
    type=click.Choice(INSTRUMENT_CHOICES),
    callback=convert_required_instrument_type,
)
@click.option(
    "-p",
    "--provider",
    "data_provider",
    help="Which provider to use for the import. Defaults to CSV.",
    type=click.Choice(PROVIDER_CHOICES),
    default=types.DataProvider.CSV.value,
    callback=convert_required_data_provider,
)
@click.option(
    "-c",
    "--candles-path",
    help="File path for the instrument's candles data stored in a CSV to seed the table.",
)
# TODO: This should be much better explained. We should explain how the different tables look like for instruments that are set up.
@click.option(
    "-m",
    "--metadata-path",
    help="File path for the metadata stored in a CSV to seed the instrument's table.",
)
@click.option(
    "-i",
    "--interactive",
    default=False,
    is_flag=True,
    help="Set up the instrument using interactive prompts. This ignores all other flags.",
)
def db_import(
    instrument: types.InstrumentType,
    data_provider: types.DataProvider,
    candles_path: str | None,
    metadata_path: str | None,
    interactive: bool,
):
    """
    Import data from common financial data vendors.
    """
    if interactive:
        try:
            db_interactive.import_data(instrument)
            return
        except Exception as e:
            click.secho(e, fg="red")
            sys.exit(1)

    if (
        data_provider == types.DataProvider.CSV
        and candles_path
        and metadata_path
    ):
        data_import.raw_data_from_csv(
            instrument,
            candles_csv_path=candles_path,
            metadata_csv_path=metadata_path,
        )
        click.secho(
            f"Successfully imported data from '{candles_path}' and '{metadata_path}'",
            fg="green",
        )
    elif data_provider == types.DataProvider.CSV and candles_path:
        data_import.raw_data_from_csv(instrument, candles_csv_path=candles_path)
        click.secho(
            f"Successfully imported data from '{candles_path}'", fg="green"
        )
    elif data_provider == types.DataProvider.CSV and metadata_path:
        data_import.raw_data_from_csv(
            instrument, metadata_csv_path=candles_path
        )
        click.secho(
            f"Successfully imported data from '{metadata_path}'", fg="green"
        )
    else:
        # TODO: This needs to be implemented
        click.secho(
            "This command has not been finished yet. Other dataproviders and import methods will follow soon.",
            fg="red",
        )
        sys.exit(1)


@db_group.command("table")
@click.argument("table_name")
def db_table(table_name: str):
    con = migration.connect()
    con.sql(f"FROM {table_name};").show()


@db_group.command("available-features")
def db_available_features():
    click.echo("\n".join(template.get_feature_names()))


@db_group.command("add")
@click.argument(
    "instrument",
    type=click.Choice(INSTRUMENT_CHOICES),
    callback=convert_required_instrument_type,
)
@click.option(
    "-r",
    "--raw-frequency",
    "timespan",
    help="The frequency the raw candle data has.",
    type=click.Choice(TIMESPAN_CHOICES),
    callback=convert_optional_timespan,
)
@click.option(
    "-a",
    "--aggregate-frequency",
    "aggregate_timespans",
    multiple=True,
    help="Create aggregate tables based on raw candle data. Value needs to be bigger than frequency",
    type=click.Choice(TIMESPAN_CHOICES),
    callback=convert_timespans,
)
@click.option(
    "-f",
    "--feature",
    "feature_names",
    multiple=True,
    help="Create feature tables based on original data table",
    type=click.Choice(template.get_feature_names()),
)
@click.option(
    "-i",
    "--interactive",
    default=False,
    is_flag=True,
    help="Set up the instrument using interactive prompts. This ignores all other flags.",
)
def db_add(
    instrument: types.InstrumentType,
    timespan: types.Timespan | None,
    aggregate_timespans: list[types.Timespan],
    feature_names: list[str],
    interactive: bool,
):
    """
    Add database tables for a given instrument type. Only use this command when the database is already setup. Prefer `init` otherwise.
    """
    if interactive:
        db_interactive.add_instrument(instrument)
    elif timespan:
        try:
            migration.add_instrument(
                instrument,
                timespan,
                aggregate_timespans,
                feature_names,
                apply=True,
            )
        except errors.MigrationError as e:
            click.secho(e, fg="red")

        click.secho(
            f"Successfully set up {instrument.value}.",
            fg="green",
        )
    else:
        try:
            migration.update_instrument(
                instrument,
                aggregate_timespans,
                feature_names,
                apply=True,
            )
        except errors.MigrationError as e:
            click.secho(e, fg="red")

        click.secho(
            f"Successfully updated {instrument.value}.",
            fg="green",
        )


@db_group.command("remove")
@click.argument(
    "instrument",
    type=click.Choice(INSTRUMENT_CHOICES),
    callback=convert_required_instrument_type,
)
@click.option(
    "-a",
    "--aggregate-frequency",
    "aggregate_timespans",
    multiple=True,
    help="Remove aggregate tables that you have created previously.",
    type=click.Choice(TIMESPAN_CHOICES),
    callback=convert_timespans,
)
@click.option(
    "-f",
    "--feature",
    "feature_names",
    multiple=True,
    help="Remove feature tables that you have created previously.",
    type=click.Choice(template.get_feature_names()),
)
def db_remove(
    instrument: types.InstrumentType,
    aggregate_timespans: list[types.Timespan],
    feature_names: list[str],
):
    """Remove an instrument that you have set up with Premia."""
    # TODO: Can this be simplified? It seems awkward
    # TODO: The success messages are kind of lazy. We should give more details.
    try:
        if len(aggregate_timespans) == 0 and len(feature_names) == 0:
            migration.remove_instrument(instrument, apply=True)
            click.secho(
                f"Successfully removed {instrument.value} from your system.",
                fg="green",
            )
            return

        if len(aggregate_timespans) > 0:
            migration.remove_instrument_aggregates(
                instrument, aggregate_timespans=aggregate_timespans, apply=True
            )
            click.secho(
                f"Successfully removed {instrument.value}' aggregate tables from your system.",
                fg="green",
            )
        if len(feature_names) > 0:
            migration.remove_instrument_features(
                instrument, feature_names=feature_names, apply=True
            )
            click.secho(
                f"Successfully removed {instrument.value}' feature tables from your system.",
                fg="green",
            )
    except errors.MigrationError as e:
        click.secho(e, fg="red")
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
    if yes or click.confirm("Are you sure you want to reset your database?"):
        migration.reset()
        click.secho("Successfully reset the database.", fg="green")
