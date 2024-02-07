import click
import os
from premia.dataprovider import twelvedata, polygon, yfinance
from premia.utils import config, types
from premia.db import template, migration

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
        add_instrument_migrations(types.InstrumentType.STOCKS)

    if answer == types.InstrumentType.OPTIONS.value or answer == "both":
        add_instrument_migrations(types.InstrumentType.OPTIONS)

    con = migration.connect()
    migration.setup(con)
    migration.apply_all(con, migrations_dir)


# TODO: Can we cleaner separate the prompting from the non-prompting flow?
# TODO: Maybe split the function in smaller sub parts
def add_instrument_migrations(
    instrument: types.InstrumentType,
    timespan: types.Timespan | None = None,
    allow_prompts=True,
) -> None:
    if not timespan and not allow_prompts:
        raise types.WizardError(
            "You need to either set a timespan or allow prompts."
        )

    if not timespan:
        timespan_units = [ti.unit for ti in types.timespan_info.values()]
        timespan_unit = click.prompt(
            "What is the timespan of your data points?",
            type=click.Choice(timespan_units),
        )
        timespan = types.Timespan(timespan_unit)

    timespan_info = types.timespan_info.get(timespan)

    if timespan_info is None:
        click.secho("Selected invalid timespan unit.", fg="red")
        raise click.Abort()

    base_table = f"{instrument.value}_1_{timespan.value}_candles"
    config.update_config(
        instrument,
        config.InstrumentConfig(
            base_table=base_table,
            timespan_unit=timespan.value,
        ),
    )

    template.create_migration_file(
        "add_candles",
        template.SqlTemplateData(
            instrument=instrument,
            quantity=1,
            timespan=timespan,
        ),
    )

    if instrument == types.InstrumentType.STOCKS:
        template.create_migration_file("add_companies")
    elif instrument == types.InstrumentType.OPTIONS:
        template.create_migration_file("add_contracts")

    if not allow_prompts:
        return

    response = click.prompt(
        f"Do you want to create an aggregate based on your {instrument.value}' raw data?",
        type=click.Choice(timespan_info.bigger_units + ["no"]),
    )
    if response != "no":
        aggregate_timespan = types.Timespan(response)
        if aggregate_timespan is None:
            click.secho("Invalid aggregate timespan unit selected.", fg="red")
            raise click.Abort()

        template.create_migration_file(
            "add_aggregate_candles",
            template.SqlTemplateData(
                instrument=instrument,
                quantity=1,
                timespan=aggregate_timespan,
                reference_table=base_table,
            ),
        )

    feature_names = template.get_feature_names()
    response = click.prompt(
        f"Do you want to create a feature table based on your {instrument.value}' raw data?",
        type=click.Choice(feature_names + ["no"]),
    )

    if response != "no":
        template.create_migration_file(
            response,
            template.SqlTemplateData(
                instrument=instrument,
                quantity=1,
                timespan=timespan,
                reference_table=base_table,
            ),
        )


# TODO: Move the import logic to a separate module
def seed():
    try:
        config.config()
    except types.ConfigError:
        raise Exception("Config must be set up to seed DB.")

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
            "Which method would you like to use to import the data?",
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
            raise types.WizardError(f"Unsupported data provider: {provider}")
    except Exception as e:
        raise types.WizardError(e)


def import_from_csv(
    instrument: types.InstrumentType,
    candles_csv_path="",
    metadata_csv_path="",
    allow_prompts=True,
):
    instrument_config = config.config().instruments[instrument]
    metadata_table = (
        "contracts"
        if instrument == types.InstrumentType.OPTIONS
        else "companies"
    )

    if not candles_csv_path and not metadata_csv_path and not allow_prompts:
        raise types.WizardError(
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
What is the path to your {instrument.value}' 1 {instrument_config.timespan_unit} candles CSV file?
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

    stocks_config = config.config().instruments[types.InstrumentType.STOCKS]
    twelvedata.import_market_data(
        types.ApiParams(
            symbol=symbol,
            timespan=types.Timespan(stocks_config.timespan_unit),
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

    stocks_config = config.config().instruments[types.InstrumentType.STOCKS]
    yfinance.import_market_data(
        types.ApiParams(
            symbol=ticker,
            timespan=types.Timespan(stocks_config.timespan_unit),
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

    instrument_config = config.config().instruments[instrument]
    polygon.import_market_data(
        types.ApiParams(
            symbol=symbol,
            start=start,
            end=end,
            timespan=types.Timespan(instrument_config.timespan_unit),
            quantity=1,
            table=instrument_config.base_table,
        )
    )

    # TODO: Migrate Polygon's metadata import
    # if instrument == config.STOCKS:
    #     polygon.import_company_data(ticker)
    # elif instrument == config.OPTIONS:
    #     polygon.import_contract_data(ticker)
