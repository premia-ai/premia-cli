import os
from typing import cast
import duckdb
from premia import config
from premia._shared import types, errors
from . import template


def get_instrument_base_table(
    instrument: types.InstrumentType, timespan: types.Timespan
) -> str:
    return f"{instrument}_1_{timespan}_candles"


def connect(
    create_if_missing=False, path: str | None = None
) -> duckdb.DuckDBPyConnection:
    db_config = config.get().get("db")
    if db_config is None and create_if_missing is False:
        if path:
            return duckdb.connect(path)
        else:
            raise errors.MissingDbError()

    if db_config is None:
        db_config = config.create_db(path)

    return duckdb.connect(db_config["path"])


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


def create(con: duckdb.DuckDBPyConnection) -> None:
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
    db_config = config.get_db()
    try:
        config.remove_db()
    except Exception as e:
        raise errors.MigrationError(
            f"An error occurred while reseting your database at '{db_config['path']}': {e}"
        )

    create(connect(create_if_missing=True))


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


def purge(con: duckdb.DuckDBPyConnection | None = None):
    con = connect() if con is None else con
    with con.cursor() as cursor:
        cursor.execute(
            """
SELECT table_name
FROM information_schema.tables
WHERE table_name LIKE 'ai_response%';
"""
        )
        ai_responses = [ai_response for ai_response, in cursor.fetchall()]
        for ai_response in ai_responses:
            cursor.sql(f"DROP VIEW IF EXISTS {ai_response};")


def get_migration_version(filename: str) -> str:
    version = filename.split("_")[0]
    return version


def get_instrument_metadata_table(instrument: types.InstrumentType) -> str:
    if instrument == "options":
        return "contracts"
    else:
        return "companies"


def add_instrument_raw_data(
    instrument: types.InstrumentType,
    timespan: types.Timespan,
    apply=False,
) -> int:
    db_config = config.get_db()
    instrument_config = db_config.get("instruments", {}).get(instrument)
    if instrument_config is not None:
        raise errors.MigrationError(
            f"Instrument {instrument} has already been set up"
        )

    template.create_migration_file(
        "add_candles",
        instrument=instrument,
        timespan=timespan,
    )

    metadata_table = get_instrument_metadata_table(instrument)
    template.create_migration_file(f"add_{metadata_table}")

    if apply:
        apply_all(connect(), config.migrations_dir())
        config.set_db_instrument(
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
    instrument_config = config.get_db_instrument(instrument)
    existing_aggregate_timespans = set(
        instrument_config.get("aggregate_timespans", [])
    )
    new_aggregate_timespans = aggregate_timespans.difference(
        existing_aggregate_timespans
    )

    allowed_timespans = types.timespan_info[
        instrument_config["timespan"]
    ].bigger_timespans

    unapplied_migration_files = 0
    for aggregate_timespan in new_aggregate_timespans:
        if aggregate_timespan not in allowed_timespans:
            # TODO: Create cleanup function that removes not-applied migrations on a MigrationError
            raise errors.MigrationError(
                f"Cannot add a {instrument} aggregate table with the frequency '{aggregate_timespan}' for raw data with the frequency '{instrument_config['timespan']}'."
            )

        template.create_migration_file(
            "add_aggregate_candles",
            instrument=instrument,
            timespan=aggregate_timespan,
            reference_table=instrument_config["base_table"],
        )

        unapplied_migration_files += 1

    if apply and unapplied_migration_files > 0:
        apply_all(connect(), config.migrations_dir())
        all_aggregate_timespans = (
            existing_aggregate_timespans | new_aggregate_timespans
        )
        config.set_db_instrument(
            instrument=instrument, aggregate_timespans=all_aggregate_timespans
        )
        return 0

    return unapplied_migration_files


def add_instrument_features(
    instrument: types.InstrumentType, feature_names: set[str], apply=False
) -> int:
    instrument_config = config.get_db_instrument(instrument)
    existing_feature_names = set(instrument_config.get("feature_names", []))
    new_feature_names = feature_names.difference(existing_feature_names)

    allowed_feature_names = template.features()

    unapplied_migration_files = 0
    for feature_name in new_feature_names:
        # TODO: Maybe this should happen before the loop to avoid abandoned migration files?
        if feature_name not in allowed_feature_names:
            raise errors.MigrationError(
                f"Feature with the name '{feature_name}' does not exist."
            )

        template.create_migration_file(
            f"add_{feature_name}",
            instrument=instrument,
            timespan=instrument_config["timespan"],
            reference_table=instrument_config["base_table"],
        )

        unapplied_migration_files += 1

    if apply and unapplied_migration_files > 0:
        apply_all(connect(), config.migrations_dir())
        all_feature_names = existing_feature_names | new_feature_names
        config.set_db_instrument(
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
    instrument_config = config.get_db_instrument(instrument)
    existing_feature_names = set(instrument_config.get("feature_names", []))
    feature_names_to_remove = (
        feature_names if feature_names else existing_feature_names
    )

    unapplied_migration_files = 0
    for feature_name in feature_names_to_remove:
        # TODO: Maybe this should happen before the loop to avoid abandoned migration files?
        if feature_name not in existing_feature_names:
            raise errors.MigrationError(
                f"Cannot remove {instrument} feature table for '{feature_name}', because it doesn't exist."
            )

        template.create_migration_file(
            f"remove_{feature_name}",
            instrument=instrument,
            timespan=instrument_config["timespan"],
            reference_table=instrument_config["base_table"],
        )
        unapplied_migration_files += 1

    if apply and unapplied_migration_files > 0:
        apply_all(connect(), config.migrations_dir())
        feature_names_left = existing_feature_names - feature_names_to_remove
        config.set_db_instrument(
            instrument=instrument, feature_names=feature_names_left
        )
        return 0

    return unapplied_migration_files


def remove_instrument_aggregates(
    instrument: types.InstrumentType,
    aggregate_timespans: set[types.Timespan] | None = None,
    apply=False,
) -> int:
    instrument_config = config.get_db_instrument(instrument)
    existing_aggregate_timespans = set(
        instrument_config.get("aggregate_timespans", [])
    )
    aggregate_timespans_to_remove = (
        aggregate_timespans
        if aggregate_timespans
        else existing_aggregate_timespans
    )

    unapplied_migration_files = 0
    for aggregate_timespan in aggregate_timespans_to_remove:
        if aggregate_timespan not in existing_aggregate_timespans:
            # TODO: Create cleanup function that removes not-applied migrations on a MigrationError
            raise errors.MigrationError(
                f"Cannot remove {instrument} aggregate table with the frequency '{aggregate_timespan}' for raw data with the frequency '{instrument_config['timespan']}'."
            )

        template.create_migration_file(
            "remove_aggregate_candles",
            instrument=instrument,
            timespan=aggregate_timespan,
            reference_table=instrument_config["base_table"],
        )
        unapplied_migration_files += 1

    if apply and unapplied_migration_files > 0:
        apply_all(connect(), config.migrations_dir())
        aggregate_timespans_left = (
            existing_aggregate_timespans - aggregate_timespans_to_remove
        )
        config.set_db_instrument(
            instrument=instrument, aggregate_timespans=aggregate_timespans_left
        )
        return 0

    return unapplied_migration_files


def remove_instrument_raw_data(
    instrument: types.InstrumentType, apply=False
) -> int:
    instrument_config = config.get_db_instrument(instrument)
    template.create_migration_file(
        "remove_candles",
        instrument=instrument,
        timespan=instrument_config["timespan"],
    )

    metadata_table = get_instrument_metadata_table(instrument)
    template.create_migration_file(f"remove_{metadata_table}")

    if apply:
        apply_all(connect(), config.migrations_dir())
        config.remove_db_instrument(instrument)
        return 0

    return 2


def _remove_instrument(
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


def set_instrument(
    instrument: types.InstrumentType,
    timespan: types.Timespan | None,
    aggregate_timespans: set[types.Timespan],
    feature_names: set[str],
):
    if timespan:
        add_instrument(
            instrument,
            timespan,
            aggregate_timespans,
            feature_names,
            apply=True,
        )
    else:
        update_instrument(
            instrument,
            aggregate_timespans,
            feature_names,
            apply=True,
        )


def remove_instrument(
    instrument: types.InstrumentType,
    aggregate_timespans: set[types.Timespan],
    feature_names: set[str],
):
    if len(aggregate_timespans) == 0 and len(feature_names) == 0:
        _remove_instrument(instrument, apply=True)
        return

    if len(aggregate_timespans) > 0:
        remove_instrument_aggregates(
            instrument, aggregate_timespans=aggregate_timespans, apply=True
        )
    if len(feature_names) > 0:
        remove_instrument_features(
            instrument, feature_names=feature_names, apply=True
        )
