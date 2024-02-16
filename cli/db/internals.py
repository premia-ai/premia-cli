from dataclasses import dataclass, field
from typing import Literal, cast
from cli.db import migration

DB_SCHEMA = "premia"


@dataclass
class Column:
    name: str
    data_type: str
    is_nullable: bool

    def sql_string(self) -> str:
        nullable = "NULL" if self.is_nullable else "NOT NULL"
        return f"{self.name} {self.data_type.upper()} {nullable}"


@dataclass
class Table:
    name: str
    type: Literal["TABLE", "VIEW"]
    view_definition: str = ""
    columns: list[Column] = field(default_factory=list)

    def sql_string(self, use_view_definition=False) -> str:
        column_strings = [column.sql_string() for column in self.columns]
        columns = ",\n".join(column_strings)

        if use_view_definition and self.type == "VIEW":
            return self.view_definition.strip()

        return f"""
CREATE TABLE {self.name} (
{pad(columns, 2)}
);""".strip()


# Based on: https://atlasgo.io/blog/2022/02/09/programmatic-inspection-in-go-with-atlas
# Adapted for DuckDB
table_query = """
SELECT c.table_name,
       t.table_type,
       c.column_name,
       UPPER(c.data_type) as column_type,
       c.is_nullable AS column_type_is_nullable,
       v.sql as view_definition
FROM information_schema.columns AS c
LEFT JOIN information_schema.tables AS t
ON c.table_name = t.table_name
LEFT JOIN duckdb_views() as v	
ON c.table_name = v.view_name
WHERE c.table_schema != 'premia'
ORDER BY t.table_type, c.table_name, c.ordinal_position;
"""


def pad(value: str, width: int, fill_string=" ") -> str:
    filler = fill_string * width
    new_line = "\n"
    return f"{filler}{value.replace(new_line, new_line + filler)}"


def tables() -> list[str]:
    con = migration.connect()
    con.execute(
        """
SELECT table_name
FROM information_schema.tables
WHERE table_schema != 'premia'
ORDER BY table_name;
"""
    )
    result = cast(list[tuple[str]], con.fetchall())
    return [table for table, in result]


def inspect() -> str:
    con = migration.connect()

    parsed_tables = {}
    with con.cursor() as cursor:
        cursor.execute(table_query)

        for row in cursor.fetchall():
            (
                table_name,
                table_type,
                column_name,
                column_data_type,
                column_is_nullable,
                view_definition,
            ) = row
            column_is_nullable = column_is_nullable == "YES"
            table_type = table_type if table_type == "VIEW" else "TABLE"

            if table_name not in parsed_tables:
                parsed_tables[table_name] = Table(
                    table_name, table_type, view_definition
                )

            column = Column(column_name, column_data_type, column_is_nullable)
            parsed_tables[table_name].columns.append(column)

    db_schema = ""
    for table in parsed_tables.values():
        db_schema += table.sql_string() + "\n\n"

    return db_schema.rstrip()
