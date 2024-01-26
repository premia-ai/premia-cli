import os
from urllib.parse import urlparse
import psycopg2
from psycopg2.extensions import connection
from utils import types


def connect() -> connection:
    postgres_url = os.getenv("POSTGRES_URL")
    if postgres_url is None:
        raise ValueError("Please set POSTGRES_URL environment variable")

    parsed_url = urlparse(postgres_url)
    return psycopg2.connect(
        dbname=parsed_url.path[1:],
        user=parsed_url.username,
        password=parsed_url.password,
        port=parsed_url.port,
        host=parsed_url.hostname,
    )


def setup(conn: connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR PRIMARY KEY,
                applied BOOLEAN NOT NULL DEFAULT FALSE
            )
        """
        )
        conn.commit()


def apply(conn: connection, file_path: str) -> None:
    version = get_migration_version(os.path.basename(file_path))
    with conn.cursor() as cursor:
        with open(file_path, "r") as file:
            sql = file.read()
            try:
                cursor.execute(sql)
                cursor.execute(
                    """
                    INSERT INTO schema_migrations (version, applied)
                    VALUES (%s, TRUE)
                    ON CONFLICT (version) DO UPDATE SET applied = TRUE
                """,
                    (version,),
                )
                conn.commit()
            except psycopg2.DatabaseError as e:
                conn.rollback()
                raise types.MigrationError(
                    f"Error applying migration {file_path}: {e}"
                )


def apply_all(conn: connection, directory: str) -> None:
    """
    Apply all migrations in the specified directory that are newer than the last applied migration.

    :param conn: Database connection
    :param directory: Directory containing migration files
    """

    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT version FROM schema_migrations WHERE applied = TRUE ORDER BY version DESC LIMIT 1;"
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
            apply(conn, os.path.join(directory, filename))


def reset(conn: connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO postgres, public;
            COMMENT ON SCHEMA public IS 'standard public schema';
        """
        )
        conn.commit()

    setup(conn)


def copy_csv(conn: connection, csv_path: str, table) -> None:
    """
    Copy the contents of a CSV file to the designated PostgreSQL table.
    """
    with conn.cursor() as cursor:
        try:
            with open(csv_path, "r") as csv:
                cursor.copy_expert(
                    f"COPY {table} TO STDIN DELIMITER ',' CSV HEADER;",
                    csv,
                )
            conn.commit()
        except (Exception, psycopg2.DatabaseError) as e:
            conn.rollback()
            raise types.MigrationError(e)


def get_migration_version(filename: str) -> str:
    version = filename.split("_")[0]
    return version
