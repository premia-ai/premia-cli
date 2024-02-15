import os
from typing import cast
import duckdb
from premia.utils import types, config, errors
from premia.db import template


def connect(create_if_missing=False) -> duckdb.DuckDBPyConnection:
    db_config = config.get_db_config()
    if not db_config and create_if_missing:
        db_config = config.create_db_config()
    elif not db_config:
        raise errors.MissingDbError()

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
            CREATE SCHEMA IF NOT EXISTS premia;
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
                    VALUES (?, TRUE);
                """,
                    [version],
                )
                con.commit()
            except Exception as e:
                cursor.execute(
                    """
                    INSERT INTO premia.schema_migrations (version, applied)
                    VALUES (?, FALSE);
                """,
                    [version],
                )
                con.commit()
                raise errors.MigrationError(
                    f"Error applying migration {file_path}: {e}. You need to fix the migration before applying further ones."
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
        config.remove_db_or_raise()
    except Exception as e:
        raise errors.MigrationError(
            f"An error occurred while reseting your database at '{db_config.path}': {e}"
        )

    setup(connect(create_if_missing=True))


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


def get_instrument_base_table(
    instrument: types.InstrumentType, timespan: types.Timespan
) -> str:
    return f"{instrument.value}_1_{timespan.value}_candles"


def get_instrument_metadata_table(instrument: types.InstrumentType) -> str:
    if instrument == types.InstrumentType.OPTIONS:
        return "contracts"
    else:
        return "companies"


def add_instrument_raw_data(
    instrument: types.InstrumentType,
    timespan: types.Timespan,
    apply=False,
) -> int:
    if config.get_instrument_config(instrument):
        raise errors.MigrationError(
            f"Instrument {instrument} has already been set up"
        )

    template.create_migration_file(
        "add_candles",
        template.SqlTemplateData(
            instrument=instrument,
            quantity=1,
            timespan=timespan,
        ),
    )

    metadata_table = get_instrument_metadata_table(instrument)
    template.create_migration_file(f"add_{metadata_table}")

    if apply:
        apply_all(connect(), config.migrations_dir())
        config.update_instrument_config(
            instrument=instrument,
            timespan=timespan,
            base_table=get_instrument_base_table(instrument, timespan),
            metadata_table=metadata_table,
        )
        return 0
    return 2


def add_instrument_aggregates(
    instrument: types.InstrumentType,
    aggregate_timespans: set[types.Timespan],
    apply=False,
) -> int:
    instrument_config = config.get_instrument_config_or_raise(instrument)
    new_aggregate_timespans = aggregate_timespans.difference(
        instrument_config.aggregate_timespans
    )

    allowed_timespan_values = types.timespan_info[
        instrument_config.timespan
    ].bigger_units

    unapplied_migration_files = 0
    for aggregate_timespan in new_aggregate_timespans:
        if aggregate_timespan.value not in allowed_timespan_values:
            # TODO: Create cleanup function that removes not-applied migrations on a MigrationError
            raise errors.MigrationError(
                f"Cannot add a {instrument.value} aggregate table with the frequency '{aggregate_timespan.value}' for raw data with the frequency '{instrument_config.timespan.value}'."
            )

        template.create_migration_file(
            "add_aggregate_candles",
            template.SqlTemplateData(
                instrument=instrument,
                quantity=1,
                timespan=aggregate_timespan,
                reference_table=instrument_config.base_table,
            ),
        )

        unapplied_migration_files += 1

    if apply and unapplied_migration_files > 0:
        apply_all(connect(), config.migrations_dir())
        all_aggregate_timespans = (
            instrument_config.aggregate_timespans | new_aggregate_timespans
        )
        config.update_instrument_config(
            instrument=instrument, aggregate_timespans=all_aggregate_timespans
        )
        return 0

    return unapplied_migration_files


def add_instrument_features(
    instrument: types.InstrumentType, feature_names: set[str], apply=False
) -> int:
    instrument_config = config.get_instrument_config_or_raise(instrument)
    new_feature_names = feature_names.difference(
        instrument_config.feature_names
    )

    allowed_feature_names = template.get_feature_names()

    unapplied_migration_files = 0
    for feature_name in new_feature_names:
        # TODO: Maybe this should happen before the loop to avoid abandoned migration files?
        if feature_name not in allowed_feature_names:
            raise errors.MigrationError(
                f"Feature with the name '{feature_name}' does not exist."
            )

        template.create_migration_file(
            f"add_{feature_name}",
            template.SqlTemplateData(
                instrument=instrument,
                quantity=1,
                timespan=instrument_config.timespan,
                reference_table=instrument_config.base_table,
            ),
        )

        unapplied_migration_files += 1

    if apply and unapplied_migration_files > 0:
        apply_all(connect(), config.migrations_dir())
        all_feature_names = instrument_config.feature_names | new_feature_names
        config.update_instrument_config(
            instrument=instrument, feature_names=all_feature_names
        )
        return 0

    return unapplied_migration_files


def add_instrument(
    instrument: types.InstrumentType,
    timespan: types.Timespan,
    aggregate_timespans: set[types.Timespan] = set(),
    feature_names: set[str] = set(),
    apply=False,
) -> int:
    unapplied_migration_files = 0
    unapplied_migration_files += add_instrument_raw_data(
        instrument, timespan, apply
    )
    unapplied_migration_files += add_instrument_aggregates(
        instrument, aggregate_timespans, apply
    )
    unapplied_migration_files += add_instrument_features(
        instrument, feature_names, apply
    )
    return unapplied_migration_files


def update_instrument(
    instrument: types.InstrumentType,
    aggregate_timespans: set[types.Timespan] | None = None,
    feature_names: set[str] | None = None,
    apply=False,
) -> int:
    unapplied_migration_files = 0
    if aggregate_timespans:
        unapplied_migration_files = add_instrument_aggregates(
            instrument, aggregate_timespans, apply
        )
    if feature_names:
        unapplied_migration_files = add_instrument_features(
            instrument, feature_names, apply
        )
    return unapplied_migration_files


def remove_instrument_features(
    instrument: types.InstrumentType,
    feature_names: set[str] | None = None,
    apply=False,
) -> int:
    instrument_config = config.get_instrument_config_or_raise(instrument)
    feature_names_to_remove = (
        instrument_config.feature_names
        if feature_names is None
        else feature_names
    )

    unapplied_migration_files = 0
    for feature_name in feature_names_to_remove:
        # TODO: Maybe this should happen before the loop to avoid abandoned migration files?
        if feature_name not in instrument_config.feature_names:
            raise errors.MigrationError(
                f"Cannot remove {instrument.value} feature table for '{feature_name}', because it doesn't exist."
            )

        template.create_migration_file(
            f"remove_{feature_name}",
            template.SqlTemplateData(
                instrument=instrument,
                quantity=1,
                timespan=instrument_config.timespan,
                reference_table=instrument_config.base_table,
            ),
        )
        unapplied_migration_files += 1

    if apply and unapplied_migration_files > 0:
        apply_all(connect(), config.migrations_dir())
        feature_names_left = (
            instrument_config.feature_names - feature_names_to_remove
        )
        config.update_instrument_config(
            instrument=instrument, feature_names=feature_names_left
        )
        return 0

    return unapplied_migration_files


def remove_instrument_aggregates(
    instrument: types.InstrumentType,
    aggregate_timespans: set[types.Timespan] | None = None,
    apply=False,
) -> int:
    instrument_config = config.get_instrument_config_or_raise(instrument)

    aggregate_timespans_to_remove = (
        instrument_config.aggregate_timespans
        if aggregate_timespans is None
        else aggregate_timespans
    )

    unapplied_migration_files = 0
    for aggregate_timespan in aggregate_timespans_to_remove:
        if aggregate_timespan not in instrument_config.aggregate_timespans:
            # TODO: Create cleanup function that removes not-applied migrations on a MigrationError
            raise errors.MigrationError(
                f"Cannot remove {instrument.value} aggregate table with the frequency '{aggregate_timespan.value}' for raw data with the frequency '{instrument_config.timespan.value}'."
            )

        template.create_migration_file(
            "remove_aggregate_candles",
            template.SqlTemplateData(
                instrument=instrument,
                quantity=1,
                timespan=aggregate_timespan,
                reference_table=instrument_config.base_table,
            ),
        )
        unapplied_migration_files += 1

    if apply and unapplied_migration_files > 0:
        apply_all(connect(), config.migrations_dir())
        aggregate_timespans_left = (
            instrument_config.aggregate_timespans
            - aggregate_timespans_to_remove
        )
        config.update_instrument_config(
            instrument=instrument, aggregate_timespans=aggregate_timespans_left
        )
        return 0

    return unapplied_migration_files


def remove_instrument_raw_data(
    instrument: types.InstrumentType, apply=False
) -> int:
    instrument_config = config.get_instrument_config_or_raise(instrument)
    template.create_migration_file(
        "remove_candles",
        template.SqlTemplateData(
            instrument=instrument,
            quantity=1,
            timespan=instrument_config.timespan,
        ),
    )

    metadata_table = get_instrument_metadata_table(instrument)
    template.create_migration_file(f"remove_{metadata_table}")

    if apply:
        apply_all(connect(), config.migrations_dir())
        config.remove_instrument_config(instrument)
        return 0

    return 2


def remove_instrument(
    instrument: types.InstrumentType,
    apply=False,
) -> int:
    unapplied_migration_files = 0
    unapplied_migration_files += remove_instrument_features(
        instrument, apply=apply
    )

    unapplied_migration_files += remove_instrument_aggregates(
        instrument, apply=apply
    )

    unapplied_migration_files += remove_instrument_raw_data(
        instrument, apply=apply
    )
    return unapplied_migration_files
