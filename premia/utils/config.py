import os
import re
import json
from dataclasses import dataclass, field
from typing import Literal
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
class DbConfig:
    type: Literal["DuckDB"]
    path: str
    instruments: dict[types.InstrumentType, InstrumentConfig] = field(
        default_factory=dict
    )


@dataclass
class RemoteAiConfig:
    api_key: str
    model: str


@dataclass
class LocalAiConfig(HuggingfaceModelId):
    model_path: str

    @property
    def model_id(self):
        return HuggingfaceModelId(
            user=self.user,
            repo=self.repo,
            filename=self.filename,
        )


@dataclass
class AiConfig:
    preference: Literal["local", "remote"]
    local: LocalAiConfig | None = None
    remote: RemoteAiConfig | None = None


@dataclass
class ConfigFileData:
    version: str = "1"
    db: DbConfig | None = None
    ai: AiConfig | None = None

    @classmethod
    def from_dict(cls, data_dict: dict) -> "ConfigFileData":
        config_file_data = cls()
        config_file_data.version = data_dict.get("version", "1")

        db_config_dict = data_dict.get("db")
        if db_config_dict:
            instruments_config = {
                types.InstrumentType(key): InstrumentConfig(**value)
                for key, value in db_config_dict.get("instruments", {}).items()
            }
            config_file_data.db = DbConfig(
                type=db_config_dict["type"],
                path=db_config_dict["path"],
                instruments=instruments_config,
            )

        ai_config_dict = data_dict.get("ai")
        if ai_config_dict:
            local_ai_config_dict = ai_config_dict.get("local")
            remote_ai_config_dict = ai_config_dict.get("remote")

            local_ai_config = (
                LocalAiConfig(**local_ai_config_dict)
                if local_ai_config_dict
                else None
            )
            remote_ai_config = (
                RemoteAiConfig(**remote_ai_config_dict)
                if remote_ai_config_dict
                else None
            )

            config_file_data.ai = AiConfig(
                preference=ai_config_dict["preference"],
                local=local_ai_config,
                remote=remote_ai_config,
            )

        return config_file_data

    def to_dict(self) -> dict:
        self_dict = self.__dict__.copy()

        if self.db:
            self_dict["db"] = self.db.__dict__.copy()
            if len(self.db.instruments):
                self_dict["db"]["instruments"] = {
                    key.value: value.__dict__.copy()
                    for key, value in self.db.instruments.items()
                }

        if self.ai:
            self_dict["ai"] = self.ai.__dict__.copy()
            if self.ai.local:
                self_dict["ai"]["local"] = self.ai.local.__dict__.copy()
            if self.ai.remote:
                self_dict["ai"]["remote"] = self.ai.remote.__dict__.copy()

        return self_dict


def save_config_file(config_file_data: ConfigFileData, create_if_missing=False):
    config_file_path = config_file(create_if_missing)
    with open(config_file_path, "w") as file:
        json.dump(config_file_data.to_dict(), file, indent=2)


def update_instrument_config(
    instrument: types.InstrumentType, data: InstrumentConfig
) -> None:
    config_file_data = config()
    if not config_file_data.db:
        raise types.ConfigError("You haven't connected a database yet.")

    config_file_data.db.instruments[instrument] = data
    save_config_file(config_file_data)


def update_db_config(path="") -> None:
    config_file_data = config()

    if config_file_data.db and not path:
        click.secho(
            "You try to update an existing db config without passing a db path. The config will not be updated.",
            fg="yellow",
        )
        return

    if not config_file_data.db:
        config_file_data.db = DbConfig(
            type="DuckDB", path=(path or DEFAULT_DATABASE_PATH)
        )
    elif config_file_data.db and path:
        config_file_data.db.path = path

    save_config_file(config_file_data, create_if_missing=True)


def update_remote_ai_config(api_key: str, model_name: str) -> None:
    config_file_data = config()

    if not config_file_data.ai:
        config_file_data.ai = AiConfig(preference="remote")

    config_file_data.ai.remote = RemoteAiConfig(
        api_key=api_key, model=model_name
    )
    save_config_file(config_file_data)


def update_local_ai_config(
    model_path: str, model_id: HuggingfaceModelId
) -> None:
    config_file_data = config()

    if config_file_data.ai and config_file_data.ai.local:
        try:
            shutil.rmtree(config_file_data.ai.local.model_path)
        except OSError as e:
            click.secho(
                f"""\
Could not delete model cached in: {config_file_data.ai.local.model_path}.
The following error was raised:
{e}""",
                fg="red",
            )

    if not config_file_data.ai:
        config_file_data.ai = AiConfig(preference="local")

    config_file_data.ai.local = LocalAiConfig(
        model_path=model_path, **model_id.__dict__
    )

    save_config_file(config_file_data)


def update_ai_config(preference: Literal["local", "remote"]) -> None:
    config_file_data = config()
    if not config_file_data.ai:
        raise types.ConfigError("You haven't set up an AI model yet.")

    config_file_data.ai.preference = preference
    save_config_file(config_file_data)


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
