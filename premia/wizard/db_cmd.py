import click
from dataprovider import twelvedata, polygon
from utils import config, types
from db import template, migration

providers_per_instrument = {
    types.InstrumentType.Stocks.value: [
        types.DataProvider.Polygon.value,
        types.DataProvider.TwelveData.value,
        types.DataProvider.Csv.value,
    ],
    types.InstrumentType.Options.value: [
        types.DataProvider.Polygon.value,
        types.DataProvider.Csv.value,
    ],
}


def setup() -> None:
    migrations_dir = config.migrations_dir(True)

    template.create_migration_file("add_timescale")

    add_stocks = click.confirm("Do you want to store stock price data?")
    if add_stocks:
        add_instrument_migrations(types.InstrumentType.Stocks)

    add_options = click.confirm("Do you want to store option price data?")
    if add_options:
        add_instrument_migrations(types.InstrumentType.Options)

    migration.apply_all(migration.connect(), migrations_dir)


def add_instrument_migrations(instrument_type: types.InstrumentType) -> None:
    timespan_units = [ti.unit for ti in types.timespan_info.values()]

    timespan_unit = click.prompt(
        "What is the timespan of your data points?",
        type=click.Choice(timespan_units),
    )

    timespan_info = next(
        (ti for ti in types.timespan_info.values() if ti.unit == timespan_unit),
        None,
    )

    if timespan_info is None:
        click.echo("Invalid timespan unit selected.")
        return

    data = template.SqlTemplateData(
        instrument_type=instrument_type,
        quantity=1,
        time_unit=timespan_unit,
    )

    template.create_migration_file("add_candles", data)

    if instrument_type == types.InstrumentType.Stocks:
        template.create_migration_file("add_companies")
    elif instrument_type == types.InstrumentType.Options:
        template.create_migration_file("add_contracts")

    add_aggregate = click.confirm(
        "Do you want to create an aggregate based on your raw data?"
    )

    # TODO: Update config with the base table value
    base_table = f"{instrument_type.value}_1_{timespan_unit}_candles"

    config.update_config(
        instrument_type,
        config.InstrumentConfig(
            base_table=base_table,
            timespan_unit=timespan_unit,
        ),
    )

    if add_aggregate:
        bigger_units = timespan_info.bigger_units

        aggregate_timespan_unit = click.prompt(
            "Which duration should the table have?",
            type=click.Choice(bigger_units),
        )

        aggregate_timespan_info = next(
            (
                timespan_info
                for timespan_info in types.timespan_info.values()
                if timespan_info.unit == aggregate_timespan_unit
            ),
            None,
        )

        if aggregate_timespan_info is None:
            click.secho("Invalid aggregate timespan unit selected.", fg="red")
            return

        template.create_migration_file(
            "add_aggregate_candles",
            template.SqlTemplateData(
                instrument_type=instrument_type,
                quantity=1,
                time_unit=aggregate_timespan_info.unit,
                reference_table=base_table,
            ),
        )

    add_feature = click.confirm(
        "Do you want to create a feature table based on your raw data?"
    )

    if add_feature:
        feature_names = template.get_feature_names()
        feature_name = click.prompt(
            "Which feature would you like to add?",
            type=click.Choice(feature_names),
        )

        template.create_migration_file(
            feature_name,
            template.SqlTemplateData(
                instrument_type=instrument_type,
                quantity=1,
                time_unit=timespan_unit,
                reference_table=base_table,
            ),
        )


def seed():
    config_file_data = config.config()

    if config_file_data is None:
        raise Exception("Config must be set up to seed DB.")

    for instrument_type in config_file_data.instruments.keys():
        providers = providers_per_instrument[instrument_type]

        if not click.confirm(
            f"Do you want to import data for {instrument_type}?"
        ):
            continue

        if len(providers) > 1:
            provider = click.prompt(
                "Which method would you like to use to import the data?",
                type=click.Choice(providers),
            )
        else:
            provider = providers[0]

        import_data(provider, instrument_type)


def import_data(
    provider: str,
    instrument_type: str,
):
    try:
        if provider == types.DataProvider.Polygon.value:
            import_from_polygon(instrument_type)
        elif provider == types.DataProvider.TwelveData.value:
            import_from_twelvedata()
        elif provider == types.DataProvider.Csv.value:
            import_from_csv(instrument_type)
        else:
            raise types.WizardError(f"Unsupported data provider: {provider}")
    except Exception as e:
        raise types.WizardError(e)


def import_from_csv(instrument_type: str):
    config_file_data = config.config()
    if not config_file_data:
        raise types.WizardError("Config must be set up to copy data from CSV.")

    csv_path = click.prompt("What is the path to your CSV file?")
    conn = migration.connect()

    migration.copy_csv(
        conn,
        csv_path,
        config_file_data.instruments[instrument_type].base_table,
    )


def import_from_twelvedata():
    config_file_data = config.config()
    if not config_file_data:
        raise types.WizardError(
            "Config must be set up to import data from Twelvedata."
        )

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

    stocks_config = config_file_data.instruments[
        types.InstrumentType.Stocks.value
    ]

    twelvedata.import_market_data(
        types.ApiParams(
            ticker=ticker,
            timespan_unit=stocks_config.timespan_unit,
            quantity=1,
            start=start,
            end=end,
            table=stocks_config.base_table,
        )
    )


def import_from_polygon(instrument: str):
    config_file_data = config.config()
    if not config_file_data:
        raise types.WizardError(
            "Config must be set up to import data from Polygon.io."
        )

    instrument_config = config_file_data.instruments[instrument]

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

    polygon.import_market_data(
        types.ApiParams(
            ticker=ticker,
            start=start,
            end=end,
            timespan_unit=instrument_config.timespan_unit,
            quantity=1,
            table=instrument_config.base_table,
        )
    )

    # TODO: Migrate Polygon's metadata import
    # if instrument == config.Stocks:
    #     polygon.import_company_data(ticker)
    # elif instrument == config.Options:
    #     polygon.import_contract_data(ticker)
