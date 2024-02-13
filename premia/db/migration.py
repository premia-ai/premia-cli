import os
from typing import cast
import duckdb
from premia.utils import types, config
from premia.db import template


def connect() -> duckdb.DuckDBPyConnection:
    db_config = config.get_db_config_or_raise()
    return duckdb.connect(db_config.path)


def columns(
    table_name: str, con: duckdb.DuckDBPyConnection | None = None
) -> list[str]:
    con = connect() if con is None else con

    with con.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = ?
            """,
            (table_name,),
        )
        result = cursor.fetchall()
        column_names = [column_name for column_name, in result]
        return cast(list[str], column_names)


def setup(con: duckdb.DuckDBPyConnection) -> None:
    with con.cursor() as cursor:
        cursor.execute(
            """
            CREATE SCHEMA premia;
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS premia.schema_migrations (
                version VARCHAR PRIMARY KEY,
                applied BOOLEAN NOT NULL DEFAULT FALSE
            );
        """
        )
        con.commit()


def apply(con: duckdb.DuckDBPyConnection, file_path: str) -> None:
    version = get_migration_version(os.path.basename(file_path))
    with con.cursor() as cursor:
        with open(file_path, "r") as file:
            sql = file.read()
            try:
                cursor.execute(sql)
                cursor.execute(
                    """
                    INSERT INTO premia.schema_migrations (version, applied)
                    VALUES (?, TRUE)
                    ON CONFLICT (version) DO UPDATE SET applied = TRUE;
                """,
                    [version],
                )
                con.commit()
            except Exception as e:
                # con.rollback()
                raise types.MigrationError(
                    f"Error applying migration {file_path}: {e}"
                )


def apply_all(con: duckdb.DuckDBPyConnection, directory: str) -> None:
    """
    Apply all migrations in the specified directory that are newer than the last applied migration.

    :param con: Database connection
    :param directory: Directory containing migration files
    """

    with con.cursor() as cursor:
        cursor.execute(
            """
            SELECT version
            FROM premia.schema_migrations
            WHERE applied = TRUE
            ORDER BY version
            DESC LIMIT 1;
        """
        )
        last_applied_version = cursor.fetchone()
        last_applied_version = (
            last_applied_version[0] if last_applied_version else None
        )

    migration_files = sorted(
        [f for f in os.listdir(directory) if f.endswith(".sql")]
    )
    for filename in migration_files:
        version = get_migration_version(filename)
        if last_applied_version is None or version > last_applied_version:
            apply(con, os.path.join(directory, filename))


def reset() -> None:
    db_config = config.get_db_config_or_raise()

    try:
        os.remove(db_config.path)
    except Exception as e:
        print(
            f"An error occurred while deleting the DB at '{db_config.path}': {e}"
        )

    con = connect()
    setup(con)


def copy_csv(
    csv_path: str, table: str, con: duckdb.DuckDBPyConnection | None = None
) -> None:
    """
    Copy the contents of a CSV file to the designated PostgreSQL table.
    """

    con = connect() if con is None else con
    with con.cursor() as cursor:
        cursor.sql(f"COPY {table} FROM '{csv_path}' DELIMITER ',' CSV HEADER;")
        con.commit()


def get_migration_version(filename: str) -> str:
    version = filename.split("_")[0]
    return version


def add_instrument_raw_data(
    instrument: types.InstrumentType,
    timespan: types.Timespan,
    apply=False,
):
    base_table = f"{instrument.value}_1_{timespan.value}_candles"

    template.create_migration_file(
        "add_candles",
        template.SqlTemplateData(
            instrument=instrument,
            quantity=1,
            timespan=timespan,
        ),
    )

    instrument_config = config.InstrumentConfig(
        base_table=base_table,
        timespan_unit=timespan.value,
    )

    config.update_instrument_config(instrument, instrument_config)

    if instrument == types.InstrumentType.STOCKS:
        template.create_migration_file("add_companies")
    elif instrument == types.InstrumentType.OPTIONS:
        template.create_migration_file("add_contracts")

    if apply:
        apply_all(connect(), config.migrations_dir())


def add_instrument_aggregates(
    instrument: types.InstrumentType,
    timespans: list[types.Timespan],
    apply=False,
) -> None:
    instrument_config = config.get_instrument_config_or_raise(instrument)
    raw_data_timespan = types.Timespan(instrument_config.timespan_unit)
    raw_data_timespan_info = types.timespan_info[raw_data_timespan]

    for timespan in timespans:
        if timespan not in raw_data_timespan_info.bigger_units:
            raise types.MigrationError(
                f"Cannot add a {instrument.value} aggregate table with the frequency '{timespan.value}' for raw data with the frequency '{raw_data_timespan.value}'."
            )

        template.create_migration_file(
            "add_aggregate_candles",
            template.SqlTemplateData(
                instrument=instrument,
                quantity=1,
                timespan=timespan,
                reference_table=instrument_config.base_table,
            ),
        )

    if apply:
        apply_all(connect(), config.migrations_dir())


def add_instrument_features(
    instrument: types.InstrumentType, feature_names: list[str], apply=False
) -> None:
    instrument_config = config.get_instrument_config_or_raise(instrument)
    raw_data_timespan = types.Timespan(instrument_config.timespan_unit)

    for feature_name in feature_names:
        if feature_name not in template.get_feature_names():
            raise types.MigrationError(
                f"Feature with the name '{feature_name}' does not exist."
            )

        template.create_migration_file(
            f"add_{feature_name}",
            template.SqlTemplateData(
                instrument=instrument,
                quantity=1,
                timespan=raw_data_timespan,
                reference_table=instrument_config.base_table,
            ),
        )

    if apply:
        apply_all(connect(), config.migrations_dir())


def add_instrument(
    instrument: types.InstrumentType,
    timespan: types.Timespan,
    aggregate_timespans: list[types.Timespan] = [],
    feature_names: list[str] = [],
    apply=False,
) -> None:
    add_instrument_raw_data(instrument, timespan)
    add_instrument_aggregates(instrument, aggregate_timespans)
    add_instrument_features(instrument, feature_names)

    if apply:
        apply_all(connect(), config.migrations_dir())
