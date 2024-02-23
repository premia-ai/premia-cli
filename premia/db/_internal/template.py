from typing import NotRequired, TypedDict
from jinja2 import Environment, FileSystemLoader
import time
import os
import re
from premia._shared import types, errors
from premia import config


class SqlTemplateData(TypedDict):
    instrument: types.InstrumentType
    quantity: int
    timespan: types.Timespan
    reference_table: NotRequired[str]


def parse_feature_name(file_name: str) -> str:
    template_regex = r"(?P<action>add_|remove_)(?P<feature_name>.*)(?P<extension>.template.sql)"

    match = re.search(template_regex, file_name)
    if match is None:
        raise errors.InternalError()
    return match.group("feature_name")


def features() -> set[str]:
    current_script_directory = os.path.dirname(os.path.abspath(__file__))
    template_features_path = os.path.join(
        current_script_directory, "templates", "features"
    )

    try:
        feature_file_names = os.listdir(template_features_path)
    except OSError as err:
        raise Exception(f"Error reading directory: {err}")

    feature_names = set()
    for feature_file_name in feature_file_names:
        feature_names.add(parse_feature_name(feature_file_name))

    return feature_names


def create_migration_name(template_name: str, version: int) -> str:
    # Remove ".template" from the template_name using regular expression
    sanitized_template_name = re.sub(r"\.template", "", template_name)

    migration_name = f"{version}_{sanitized_template_name}"

    return migration_name


def create_migration_file(
    template_name: str,
    instrument: types.InstrumentType | None = None,
    timespan: types.Timespan | None = None,
    quantity: int = 1,
    reference_table: str | None = None,
) -> None:
    migration_version = time.time_ns()

    template_file_name = f"{template_name}.template.sql"
    migration_name = create_migration_name(
        template_file_name, migration_version
    )

    migrations_dir = config.migrations_dir(True)
    migration_file_path = os.path.join(migrations_dir, migration_name)

    current_script_directory = os.path.dirname(os.path.abspath(__file__))
    env = Environment(
        loader=FileSystemLoader(
            [
                os.path.join(current_script_directory, "templates/features"),
                os.path.join(current_script_directory, "templates/migrations"),
            ]
        )
    )

    env.filters["sub"] = lambda a, b: a - b

    template = env.get_template(template_file_name)
    rendered_template = template.render(
        instrument=instrument,
        timespan=timespan,
        quantity=quantity,
        reference_table=reference_table,
    )

    with open(migration_file_path, "w") as f:
        f.write(rendered_template)
