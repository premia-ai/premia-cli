import os
import re
import json
import glob
from dataclasses import dataclass, field
from typing import Literal
import shutil
import click
from premia.utils import types, errors

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
            raise errors.ConfigError(f"'{dir_path}' directory doesn't exist.")
        os.makedirs(dir_path, mode=0o777)

    return dir_path


def config_dir(create_if_missing=False) -> str:
    return get_dir(CONFIG_DIR, create_if_missing)


def remove_db_or_raise():
    db_config = get_db_config_or_raise()
    os.remove(db_config.path)
    remove_migration_files()
    remove_db_config_or_raise()


def migrations_dir(create_if_missing=False) -> str:
    return get_dir(MIGRATIONS_DIR, create_if_missing)


def remove_migration_files():
    files = glob.glob(os.path.join(migrations_dir(), "*.sql"))
    for file in files:
        os.remove(file)


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
    metadata_table: str
    timespan: types.Timespan
    feature_names: list[str] = field(default_factory=list)
    aggregate_timespans: list[types.Timespan] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data_dict: dict):
        return InstrumentConfig(
            base_table=data_dict["base_table"],
            metadata_table=data_dict["metadata_table"],
            timespan=types.Timespan(data_dict["timespan"]),
            aggregate_timespans=[
                types.Timespan(t)
                for t in data_dict.get("aggregate_timespans", [])
            ],
            feature_names=data_dict.get("feature_names", []),
        )

    def to_dict(self) -> dict:
        return {
            "timespan": self.timespan.value,
            "base_table": self.base_table,
            "metadata_table": self.metadata_table,
            "aggregate_timespans": [t.value for t in self.aggregate_timespans],
            "feature_names": self.feature_names.copy(),
        }


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
    preference: types.AiModel
    local: LocalAiConfig | None = None
    remote: RemoteAiConfig | None = None


@dataclass
class ConfigFileData:
    version: str = "1"
    db: DbConfig | None = None
    ai: AiConfig | None = None

    @classmethod
    def from_dict(cls, data_dict: dict):
        config_file_data = cls()
        config_file_data.version = data_dict.get("version", "1")

        db_config_dict = data_dict.get("db")
        if db_config_dict:
            instruments_config = {
                types.InstrumentType(key): InstrumentConfig.from_dict(value)
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
                    key.value: value.to_dict()
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
    config_file_path = get_config_file_path(create_if_missing)
    with open(config_file_path, "w") as file:
        json.dump(config_file_data.to_dict(), file, indent=2)


def remove_all_instrument_configs():
    config_file_data = get_config()
    if config_file_data.db is None:
        raise errors.MissingDbError()

    config_file_data.db.instruments = {}
    save_config_file(config_file_data)


def remove_instrument_config(instrument: types.InstrumentType):
    config_file_data = get_config()
    if config_file_data.db is None:
        raise errors.MissingDbError()

    instrument_config = config_file_data.db.instruments.get(instrument)
    if instrument_config is None:
        raise errors.MissingInstrumentError(instrument)

    config_file_data.db.instruments.pop(instrument)
    save_config_file(config_file_data)


def remove_db_config_or_raise():
    config_file_data = get_config()
    if config_file_data.db is None:
        raise errors.MissingDbError()

    config_file_data.db = None
    save_config_file(config_file_data)


def update_instrument_config(
    instrument: types.InstrumentType,
    timespan: types.Timespan | None = None,
    base_table: str | None = None,
    metadata_table: str | None = None,
    aggregate_timespans: list[types.Timespan] | None = None,
    feature_names: list[str] | None = None,
) -> None:
    config_file_data = get_config()
    if config_file_data.db is None:
        raise errors.MissingDbError()

    instrument_config = config_file_data.db.instruments.get(instrument)
    if instrument_config is None:
        if timespan is None or base_table is None or metadata_table is None:
            raise errors.MissingInstrumentError(instrument)

        config_file_data.db.instruments[instrument] = InstrumentConfig(
            timespan=timespan,
            base_table=base_table,
            metadata_table=metadata_table,
            aggregate_timespans=aggregate_timespans or [],
            feature_names=feature_names or [],
        )
    else:
        if base_table:
            instrument_config.base_table = base_table
        if metadata_table:
            instrument_config.metadata_table = metadata_table
        if timespan:
            instrument_config.timespan = timespan
        if aggregate_timespans is not None:
            instrument_config.aggregate_timespans = aggregate_timespans
        if feature_names is not None:
            instrument_config.feature_names = feature_names

    save_config_file(config_file_data)


def create_db_config(path: str | None = None) -> DbConfig:
    config_file_data = get_config()
    if config_file_data.db:
        raise errors.ConfigError(
            "Database has already been connected to Premia."
        )

    config_file_data.db = DbConfig(
        type="DuckDB", path=(path or DEFAULT_DATABASE_PATH)
    )

    save_config_file(config_file_data, create_if_missing=True)
    return config_file_data.db


def update_db_config(path: str) -> DbConfig:
    config_file_data = get_config()
    if not config_file_data.db:
        raise errors.MissingDbError()

    config_file_data.db.path = path
    save_config_file(config_file_data, create_if_missing=True)
    return config_file_data.db


def update_remote_ai_config(api_key: str, model_name: str) -> None:
    config_file_data = get_config()

    if not config_file_data.ai:
        config_file_data.ai = AiConfig(preference="remote")

    config_file_data.ai.remote = RemoteAiConfig(
        api_key=api_key, model=model_name
    )
    save_config_file(config_file_data)


def remove_cached_ai_model():
    local_ai_config = get_local_ai_config_or_raise()

    try:
        shutil.rmtree(local_ai_config.model_path)
    except OSError as e:
        click.secho(
            f"""\
Could not delete model cached in: {local_ai_config.model_path}.
The following error was raised:
{e}""",
            fg="red",
        )


def update_local_ai_config(
    model_path: str, model_id: HuggingfaceModelId
) -> None:
    config_file_data = get_config()

    if config_file_data.ai and config_file_data.ai.local:
        remove_cached_ai_model()

    if not config_file_data.ai:
        config_file_data.ai = AiConfig(preference="local")

    config_file_data.ai.local = LocalAiConfig(
        model_path=model_path, **model_id.__dict__
    )

    save_config_file(config_file_data)


def update_ai_config(model_type: types.AiModel) -> None:
    config_file_data = get_config()
    if not config_file_data.ai:
        raise errors.MissingAiError()

    if getattr(config_file_data.ai, model_type) is None:
        raise errors.ConfigError(
            f"Cannot change the preference to '{model_type}'. No {model_type} AI model has been set up."
        )

    config_file_data.ai.preference = model_type
    save_config_file(config_file_data)


def remove_ai_model_config(model_type: types.AiModel) -> None:
    config_file_data = get_config()
    if not config_file_data.ai:
        raise errors.MissingAiError()

    if getattr(config_file_data.ai, model_type) is None:
        return

    config_file_data.ai.preference = (
        "local" if model_type == "remote" else "remote"
    )
    setattr(config_file_data.ai, model_type, None)
    if model_type == "local":
        remove_cached_ai_model()

    save_config_file(config_file_data)


def get_instrument_config_or_raise(
    instrument: types.InstrumentType,
) -> InstrumentConfig:
    instrument_config = get_instrument_config(instrument)
    if instrument_config is None:
        raise errors.MissingInstrumentError(instrument)

    return instrument_config


def get_instrument_config(
    instrument: types.InstrumentType,
) -> InstrumentConfig | None:
    db_config = get_db_config()

    if db_config is None:
        raise errors.MissingDbError()

    return db_config.instruments.get(instrument)


def get_db_config_or_raise() -> DbConfig:
    db_config = get_db_config()
    if db_config is None:
        raise errors.MissingDbError()

    return db_config


def get_db_config() -> DbConfig | None:
    return get_config().db


def get_remote_ai_config_or_raise() -> RemoteAiConfig:
    remote_ai_config = get_remote_ai_config()
    if remote_ai_config is None:
        raise errors.MissingRemoteAiError()

    return remote_ai_config


def get_remote_ai_config() -> RemoteAiConfig | None:
    return get_ai_config_or_raise().remote


def get_local_ai_config_or_raise() -> LocalAiConfig:
    local_ai_config = get_local_ai_config()
    if local_ai_config is None:
        raise errors.MissingLocalAiError()

    return local_ai_config


def get_local_ai_config() -> LocalAiConfig | None:
    return get_ai_config_or_raise().local


def get_ai_config_or_raise() -> AiConfig:
    ai_config = get_ai_config()
    if ai_config is None:
        raise errors.MissingAiError()

    return ai_config


def get_ai_config() -> AiConfig | None:
    return get_config().ai


def get_config(create_if_missing=False) -> ConfigFileData:
    config_file_path = get_config_file_path(create_if_missing)

    with open(config_file_path, "r") as file:
        config_data = json.load(file)
        return ConfigFileData.from_dict(config_data)


def get_config_file_path(create_if_missing=False) -> str:
    config_dir(create_if_missing)
    config_file_path = os.path.expanduser(CONFIG_FILE_PATH)

    if not os.path.exists(config_file_path):
        if not create_if_missing:
            raise errors.ConfigError("Premia has not been set up yet.")

        config_file_data = ConfigFileData()
        with open(config_file_path, "w") as file:
            json.dump(config_file_data.to_dict(), file, indent=2)

    return config_file_path


def setup_config_dir() -> str:
    config_dir_path = config_dir(True)
    get_config_file_path(True)
    migrations_dir(True)

    return config_dir_path
