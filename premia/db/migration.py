import os
from typing import cast
import duckdb
from premia.utils import types, config


def connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(config.db_path())


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
    db_path = config.db_path()
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception as e:
            print(
                f"An error occurred while deleting the DB at '{db_path}': {e}"
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
