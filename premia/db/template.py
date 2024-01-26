from jinja2 import Environment, FileSystemLoader
from dataclasses import dataclass
import time
import os
import re
from utils import config, types


@dataclass
class SqlTemplateData:
    instrument_type: types.InstrumentType
    quantity: int
    time_unit: str
    reference_table: str = ""

    def as_dict(self):
        return {
            "instrument_type": self.instrument_type.value,
            "quantity": self.quantity,
            "time_unit": self.time_unit,
            "reference_table": self.reference_table,
        }


def get_feature_names() -> list[str]:
    template_extension = ".template.sql"
    current_script_directory = os.path.dirname(os.path.abspath(__file__))
    template_features_path = os.path.join(
        current_script_directory, "..", "..", "templates", "features"
    )

    try:
        entries = os.listdir(template_features_path)
    except OSError as err:
        raise Exception(f"Error reading directory: {err}")

    names = []
    for entry in entries:
        names.append(entry.replace(template_extension, "", 1))

    return names


def create_migration_name(template_name: str, version: int) -> str:
    # Remove ".template" from the template_name using regular expression
    sanitized_template_name = re.sub(r"\.template", "", template_name)

    migration_name = f"{version}_{sanitized_template_name}"

    return migration_name


def create_migration_file(
    template_name: str, data: SqlTemplateData | None = None
) -> None:
    migration_version = time.time_ns()

    template_file_name = f"{template_name}.template.sql"
    migration_name = create_migration_name(
        template_file_name, migration_version
    )

    migrations_dir = config.migrations_dir(True)
    migration_file_path = os.path.join(migrations_dir, migration_name)

    env = Environment(
        loader=FileSystemLoader(["templates/features", "templates/migrations"])
    )

    env.filters["sub"] = lambda a, b: a - b

    template = env.get_template(template_file_name)
    if data is None:
        rendered_template = template.render()
    else:
        rendered_template = template.render(**data.as_dict())

    with open(migration_file_path, "w") as f:
        f.write(rendered_template)
