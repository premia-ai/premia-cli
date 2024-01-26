from dataclasses import dataclass, field
import os
from typing import Literal
import psycopg2


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
    view_definition: str | None
    columns: list[Column] = field(default_factory=list)

    def sql_string(self) -> str:
        column_strings = [column.sql_string() for column in self.columns]
        columns = ",\n".join(column_strings)
        if self.type == "TABLE":
            return f"""
CREATE TABLE {self.name} (
{pad(columns, 2)}
);
            """.strip()

        return f"""
CREATE VIEW {self.name} AS 
{self.view_definition}
            """


# Based on: https://atlasgo.io/blog/2022/02/09/programmatic-inspection-in-go-with-atlas
table_query = """
SELECT c.table_name,
       t.table_type,
       c.column_name,
       UPPER(c.udt_name) as column_type,
       c.is_nullable AS column_type_is_nullable,
       v.view_definition
FROM "information_schema"."columns" AS c
LEFT JOIN "information_schema"."tables" AS t
ON c.table_name = t.table_name
LEFT JOIN "information_schema"."views" as v	
ON c.table_name = v.table_name
WHERE c.table_schema = 'public' AND c.table_name != 'schema_migrations'
ORDER BY c.table_name, c.ordinal_position;
"""


def pad(value: str, width: int, fill_string=" ") -> str:
    filler = fill_string * width
    new_line = "\n"
    return f"{filler}{value.replace(new_line, new_line + filler)}"


def inspect() -> str:
    postgres_url = os.environ.get("POSTGRES_URL")
    if not postgres_url:
        raise ValueError("Please set POSTGRES_URL environment variable")

    conn = psycopg2.connect(postgres_url)
    cursor = conn.cursor()
    cursor.execute(table_query)

    parsed_tables = {}
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

    cursor.close()
    conn.close()

    db_schema = ""
    for table in parsed_tables.values():
        db_schema += table.sql_string() + "\n"

    return db_schema
