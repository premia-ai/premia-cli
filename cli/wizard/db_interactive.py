import click
import os
from cli.dataprovider import twelvedata, polygon, yfinance
from cli.utils import config, types, errors
from cli.db import template, migration

providers_per_instrument = {
    types.InstrumentType.STOCKS: [
        types.DataProvider.YFINANCE,
        types.DataProvider.POLYGON,
        types.DataProvider.TWELVE_DATA,
        types.DataProvider.CSV,
    ],
    types.InstrumentType.OPTIONS: [
        types.DataProvider.POLYGON,
        types.DataProvider.CSV,
    ],
}


def setup() -> None:
    if click.confirm("Do you want to set up a new database for Premia?"):
        config.create_db_config()
    else:
        db_path = click.prompt(
            "What is the path to your existing DuckDB database?"
        )
        config.create_db_config(db_path)

    migrations_dir = config.migrations_dir(True)

    answer = click.prompt(
        "Which instruments do you want to store?",
        type=click.Choice(
            [
                types.InstrumentType.STOCKS.value,
                types.InstrumentType.OPTIONS.value,
                "both",
                "none",
            ]
        ),
    )

    if answer == "none":
        return

    if answer == types.InstrumentType.STOCKS.value or answer == "both":
        add_instrument(types.InstrumentType.STOCKS)

    if answer == types.InstrumentType.OPTIONS.value or answer == "both":
        add_instrument(types.InstrumentType.OPTIONS)

    con = migration.connect(create_if_missing=True)
    migration.setup(con)
    migration.apply_all(con, migrations_dir)


def add_instrument(
    instrument: types.InstrumentType,
) -> None:
    timespan_choices = [t.value for t in types.timespan_info.keys()]
    timespan_value = click.prompt(
        "What is the timespan of your data points?",
        type=click.Choice(timespan_choices),
    )
    timespan = types.Timespan(timespan_value)
    migration.add_instrument_raw_data(instrument, timespan)

    aggregate_timespan_choices = [
        t.value for t in types.timespan_info[timespan].bigger_timespans
    ]
    response = click.prompt(
        f"Do you want to create an aggregate based on your {instrument.value}' raw data?",
        type=click.Choice(aggregate_timespan_choices + ["no"]),
    )
    if response != "no":
        aggregate_timespan = types.Timespan(response)
        migration.add_instrument_aggregates(instrument, {aggregate_timespan})

    feature_name_choices = list(template.get_feature_names())
    response = click.prompt(
        f"Do you want to create a feature table based on your {instrument.value}' raw data?",
        type=click.Choice(feature_name_choices + ["no"]),
    )
    if response != "no":
        migration.add_instrument_features(instrument, {response})

    migration.apply_all(migration.connect(), config.migrations_dir())


def seed():
    try:
        config.get_config()
    except errors.ConfigError:
        raise errors.ConfigError("Config must be set up to seed DB.")

    response = click.prompt(
        "Do you want to import data?",
        type=click.Choice(
            [
                types.InstrumentType.STOCKS.value,
                types.InstrumentType.OPTIONS.value,
                "both",
                "no",
            ]
        ),
    )

    if response == "no":
        return
    if response == types.InstrumentType.STOCKS.value or response == "both":
        import_data(types.InstrumentType.STOCKS)
    if response == types.InstrumentType.OPTIONS.value or response == "both":
        import_data(types.InstrumentType.OPTIONS)


def import_data(
    instrument: types.InstrumentType,
):
    providers = providers_per_instrument[instrument]
    if len(providers) > 1:
        providers_str = [provider.value for provider in providers]
        provider_str = click.prompt(
            f"Which method would you like to use to import the {instrument.value} data?",
            type=click.Choice(providers_str),
        )
        provider = types.DataProvider(provider_str)
    else:
        provider = providers[0]

    try:
        if provider == types.DataProvider.POLYGON:
            import_from_polygon(instrument)
        elif provider == types.DataProvider.TWELVE_DATA:
            import_from_twelvedata()
        elif provider == types.DataProvider.YFINANCE:
            import_from_yfinance()
        elif provider == types.DataProvider.CSV:
            import_from_csv(instrument)
        else:
            raise errors.WizardError(f"Unsupported data provider: {provider}")
    except Exception as e:
        raise errors.WizardError(e)


# TODO: Move the import logic to a separate module
# TODO: Is this a duplication of `premia/db/data_import.py`?
def import_from_csv(
    instrument: types.InstrumentType,
    candles_csv_path="",
    metadata_csv_path="",
    allow_prompts=True,
):
    instrument_config = config.get_instrument_config_or_raise(instrument)
    metadata_table = (
        "contracts"
        if instrument == types.InstrumentType.OPTIONS
        else "companies"
    )

    if not candles_csv_path and not metadata_csv_path and not allow_prompts:
        raise errors.WizardError(
            "You need to either set CSV paths for candles and metadata or allow prompts."
        )
    elif candles_csv_path and metadata_csv_path:
        migration.copy_csv(
            os.path.expanduser(candles_csv_path),
            instrument_config.base_table,
        )
        migration.copy_csv(
            os.path.expanduser(metadata_csv_path),
            metadata_table,
        )
        return

    base_table_columns = migration.columns(instrument_config.base_table)
    candles_csv_path = click.prompt(
        f"""
What is the path to your {instrument.value}' 1 {instrument_config.timespan} candles CSV file?
(The CSV must define the following columns: {', '.join(base_table_columns)})
        """.strip()
    )
    migration.copy_csv(
        os.path.expanduser(candles_csv_path.strip()),
        instrument_config.base_table,
    )

    metadata_table_columns = migration.columns(metadata_table)
    metadata_csv_path = click.prompt(
        f"""
What is the path to your {metadata_table}' CSV file?
(The CSV must define the following columns: {', '.join(metadata_table_columns)})
        """.strip()
    )
    migration.copy_csv(
        os.path.expanduser(metadata_csv_path.strip()),
        metadata_table,
    )


# TODO: Simplify the import_from... functions, lots of duplication.
def import_from_twelvedata():
    symbol = click.prompt(
        "What's the symbol of the instrument you would like to download?"
    )

    start = click.prompt(
        "What should the start date of the entries be?",
        type=click.DateTime(formats=["%Y-%m-%dT%H:%M:%S"]),
    )
    end = click.prompt(
        "What should the end date of the entries be?",
        type=click.DateTime(formats=["%Y-%m-%dT%H:%M:%S"]),
    )

    stocks_config = config.get_instrument_config_or_raise(
        types.InstrumentType.STOCKS
    )
    twelvedata.import_market_data(
        types.ApiParams(
            symbol=symbol,
            timespan=types.Timespan(stocks_config.timespan),
            quantity=1,
            start=start,
            end=end,
            table=stocks_config.base_table,
        )
    )


def import_from_yfinance():
    ticker = click.prompt(
        "What's the ticker of the instrument you would like to download?"
    )

    start = click.prompt(
        "What should the start date of the entries be?",
        type=click.DateTime(formats=["%Y-%m-%dT%H:%M:%S"]),
    )
    end = click.prompt(
        "What should the end date of the entries be?",
        type=click.DateTime(formats=["%Y-%m-%dT%H:%M:%S"]),
    )

    stocks_config = config.get_instrument_config_or_raise(
        types.InstrumentType.STOCKS
    )
    yfinance.import_market_data(
        types.ApiParams(
            symbol=ticker,
            timespan=types.Timespan(stocks_config.timespan),
            quantity=1,
            start=start,
            end=end,
            table=stocks_config.base_table,
        )
    )


def import_from_polygon(instrument: types.InstrumentType):
    symbol = click.prompt(
        "What's the symbol of the instrument you would like to download?"
    )
    start = click.prompt(
        "What should the start date of the entries be?",
        type=click.DateTime(formats=["%Y-%m-%dT%H:%M:%S"]),
    )
    end = click.prompt(
        "What should the end date of the entries be?",
        type=click.DateTime(formats=["%Y-%m-%dT%H:%M:%S"]),
    )

    instrument_config = config.get_instrument_config_or_raise(instrument)
    polygon.import_market_data(
        types.ApiParams(
            symbol=symbol,
            start=start,
            end=end,
            timespan=types.Timespan(instrument_config.timespan),
            quantity=1,
            table=instrument_config.base_table,
        )
    )

    # TODO: Migrate Polygon's metadata import
    # if instrument == config.STOCKS:
    #     polygon.import_company_data(ticker)
    # elif instrument == config.OPTIONS:
    #     polygon.import_contract_data(ticker)
