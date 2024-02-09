import os
import re
import json
from dataclasses import dataclass, field
import shutil
import click
from premia.utils import types

CONFIG_DIR = ".premia"
MIGRATIONS_DIR = f"{CONFIG_DIR}/migrations"
CACHE_DIR = f"{CONFIG_DIR}/cache"
CONFIG_FILE_NAME = "config.json"
CONFIG_FILE_PATH = f"~/{CONFIG_DIR}/{CONFIG_FILE_NAME}"
DEFAULT_DATABASE_FILE_NAME = "securities.db"
DEFAULT_DATABASE_PATH = f"~/{CONFIG_DIR}/{DEFAULT_DATABASE_FILE_NAME}"


def get_dir(dir_path: str, create_if_missing=False) -> str:
    home_dir = os.path.expanduser("~")
    dir_path = os.path.join(home_dir, dir_path)

    if not os.path.exists(dir_path):
        if not create_if_missing:
            raise types.ConfigError(f"'{dir_path}' directory doesn't exist.")
        os.makedirs(dir_path, mode=0o777)

    return dir_path


def config_dir(create_if_missing=False) -> str:
    return get_dir(CONFIG_DIR, create_if_missing)


def migrations_dir(create_if_missing=False) -> str:
    return get_dir(MIGRATIONS_DIR, create_if_missing)


def cache_dir(create_if_missing=False) -> str:
    return get_dir(CACHE_DIR, create_if_missing)


def db_path() -> str:
    return os.path.expanduser(
        os.getenv("DATABASE_PATH") or DEFAULT_DATABASE_PATH
    )


@dataclass
class HuggingfaceModelId:
    user: str
    repo: str
    filename: str

    @property
    def repo_id(self) -> str:
        return f"{self.user}/{self.repo}"

    @classmethod
    def parse(cls, link: str):
        # Example: https://huggingface.co/TheBloke/Mistral-7B-v0.1-GGUF/blob/main/mistral-7b-v0.1.Q4_K_M.gguf
        pattern = r"^https://huggingface\.co/([^/]+)/([^/]+)/blob/[^/]+/(.+)$"
        match = re.match(pattern, link)
        if match:
            return cls(
                user=match.group(1),
                repo=match.group(2),
                filename=match.group(3),
            )
        else:
            raise ValueError(
                f"The model link you entered is not supported: {link}"
            )


@dataclass
class InstrumentConfig:
    base_table: str
    timespan_unit: str


@dataclass
class AiConfig(HuggingfaceModelId):
    model_path: str

    @property
    def model_id(self):
        return HuggingfaceModelId(
            user=self.user, repo=self.repo, filename=self.filename
        )


@dataclass
class ConfigFileData:
    version: str = "1"
    database: str = "DuckDB"
    ai: AiConfig | None = None
    instruments: dict[types.InstrumentType, InstrumentConfig] = field(
        default_factory=dict
    )

    @classmethod
    def from_dict(cls, data_dict: dict) -> "ConfigFileData":
        config_file_data = cls()
        config_file_data.version = data_dict.get("version", "1")

        ai_config_dict = data_dict.get("ai")
        config_file_data.ai = (
            AiConfig(**ai_config_dict) if ai_config_dict else None
        )

        config_file_data.instruments = data_dict.get("instruments", {})
        config_file_data.instruments = {
            types.InstrumentType(key): InstrumentConfig(**value)
            for key, value in data_dict.get("instruments", {}).items()
        }

        return config_file_data

    def to_dict(self) -> dict:
        self_dict = self.__dict__.copy()

        if self.ai:
            self_dict["ai"] = self.ai.__dict__.copy()

        self_dict["instruments"] = {
            key.value: value.__dict__.copy()
            for key, value in self.instruments.items()
        }

        return self_dict


def update_instrument_config(
    instrument: types.InstrumentType, data: InstrumentConfig
) -> None:
    config_file_path = config_file()
    config_file_data = config()

    config_file_data.instruments[instrument] = data

    with open(config_file_path, "w") as file:
        json.dump(config_file_data.to_dict(), file, indent=2)


# TODO: You should delete the old model when setting a new one
def update_ai_config(model_path: str, model_id: HuggingfaceModelId) -> None:
    config_file_path = config_file()
    config_file_data = config()

    if config_file_data.ai:
        try:
            shutil.rmtree(config_file_data.ai.model_path)
        except OSError as e:
            click.secho(
                f"""\
Could not delete model cached in: {config_file_data.ai.model_path}.
The following error was raised:
{e}""",
                fg="red",
            )

    config_file_data.ai = AiConfig(model_path=model_path, **model_id.__dict__)
    with open(config_file_path, "w") as file:
        json.dump(config_file_data.to_dict(), file, indent=2)


def config(create_if_missing=False) -> "ConfigFileData":
    config_file_path = config_file(create_if_missing)

    with open(config_file_path, "r") as file:
        config_data = json.load(file)
        return ConfigFileData.from_dict(config_data)


def config_file(create_if_missing=False) -> str:
    config_dir(create_if_missing)
    config_file_path = os.path.expanduser(CONFIG_FILE_PATH)

    if not os.path.exists(config_file_path):
        if not create_if_missing:
            raise types.ConfigError("'config.json' doesn't exist.")

        config_file_data = ConfigFileData()
        with open(config_file_path, "w") as file:
            json.dump(config_file_data.to_dict(), file, indent=2)

    return config_file_path


def setup_config_dir() -> str:
    config_dir_path = config_dir(True)
    config_file(True)
    migrations_dir(True)

    return config_dir_path
