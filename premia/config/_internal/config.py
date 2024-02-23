import os
import json
import glob
import yaml
from typing import Literal
import shutil
from huggingface_hub import hf_hub_download
from .types import (
    ConfigFileData,
    FormatOption,
    ProvidersConfig,
    InstrumentConfig,
    DbConfig,
    AiConfig,
    LocalAiConfig,
    RemoteAiConfig,
    HuggingfaceModelLink,
    parse_huggingface_model_link,
)
from premia._shared import errors, types

CONFIG_DIR_NAME = ".premia"
CONFIG_DIR_PATH = os.path.expanduser(f"~/{CONFIG_DIR_NAME}")
MIGRATIONS_DIR_NAME = "migrations"
MIGRATIONS_DIR_PATH = f"{CONFIG_DIR_PATH}/{MIGRATIONS_DIR_NAME}"
CACHE_DIR_NAME = "cache"
CACHE_DIR_PATH = f"{CONFIG_DIR_PATH}/{CACHE_DIR_NAME}"
CONFIG_FILE_NAME = "config.json"
CONFIG_FILE_PATH = f"{CONFIG_DIR_PATH}/{CONFIG_FILE_NAME}"
DEFAULT_DATABASE_FILE_NAME = "securities.db"
DEFAULT_DATABASE_PATH = f"{CONFIG_DIR_PATH}/{DEFAULT_DATABASE_FILE_NAME}"


def get_dir(dir_path: str, create_if_missing=False) -> str:
    if not os.path.exists(dir_path):
        if not create_if_missing:
            raise errors.ConfigError(f"'{dir_path}' directory doesn't exist.")
        os.makedirs(dir_path, mode=0o777)

    return dir_path


def config_dir(create_if_missing=False) -> str:
    return get_dir(CONFIG_DIR_NAME, create_if_missing)


def migrations_dir(create_if_missing=False) -> str:
    return get_dir(MIGRATIONS_DIR_PATH, create_if_missing)


def cache_dir(create_if_missing=False) -> str:
    return get_dir(CACHE_DIR_PATH, create_if_missing)


def remove_migration_files():
    files = glob.glob(os.path.join(migrations_dir(), "*.sql"))
    for file in files:
        os.remove(file)


def save_config_file(config_file_data: ConfigFileData, create_if_missing=False):
    config_file_path = get_config_file_path(create_if_missing)
    with open(config_file_path, "w") as file:
        json.dump(config_file_data, file, indent=4)


def remove_all_instrument_configs():
    config_file_data = get_config()
    db_config = config_file_data.get("db")
    if db_config is None:
        raise errors.MissingDbError()

    del db_config["instruments"]
    save_config_file(config_file_data)


def remove_instrument_config(instrument: types.InstrumentType):
    config_file_data = get_config()
    db_config = config_file_data.get("db")
    if db_config is None:
        raise errors.MissingDbError()

    instruments_config = db_config.get("instruments")
    if instruments_config is None:
        raise errors.MissingInstrumentError(instrument)

    instrument_config = instruments_config.get(instrument)
    if instrument_config is None:
        raise errors.MissingInstrumentError(instrument)

    instruments_config.pop(instrument)
    save_config_file(config_file_data)


def remove_db_or_raise():
    db_config = get_db_config_or_raise()
    os.remove(db_config["path"])
    remove_migration_files()
    remove_db_config_or_raise()


def remove_db_config_or_raise():
    config_file_data = get_config()
    if config_file_data.get("db") is None:
        raise errors.MissingDbError()

    config_file_data.pop("db")
    save_config_file(config_file_data)


def set_instrument_config(
    instrument: types.InstrumentType,
    timespan: types.Timespan | None = None,
    base_table: str | None = None,
    metadata_table: str | None = None,
    aggregate_timespans: set[types.Timespan] | None = None,
    feature_names: set[str] | None = None,
) -> InstrumentConfig:
    config_file_data = get_config()
    db_config = config_file_data.get("db")
    if db_config is None:
        raise errors.MissingDbError()

    instruments_config = db_config.get("instruments")
    if instruments_config is None:
        raise errors.MissingInstrumentError(instrument)

    instrument_config = instruments_config.get(instrument)
    if instrument_config is None:
        if timespan is None or base_table is None or metadata_table is None:
            raise errors.MissingInstrumentError(instrument)

        instruments_config[instrument] = InstrumentConfig(
            timespan=timespan,
            base_table=base_table,
            metadata_table=metadata_table,
        )

        if aggregate_timespans:
            instruments_config[instrument]["aggregate_timespans"] = list(
                aggregate_timespans
            )

        if feature_names:
            instruments_config[instrument]["feature_names"] = list(
                feature_names
            )

        save_config_file(config_file_data)
        return instruments_config[instrument]
    else:
        if base_table:
            instrument_config["base_table"] = base_table
        if metadata_table:
            instrument_config["metadata_table"] = metadata_table
        if timespan:
            instrument_config["timespan"] = timespan
        if aggregate_timespans is not None:
            instrument_config["aggregate_timespans"] = list(aggregate_timespans)
        if feature_names is not None:
            instrument_config["feature_names"] = list(feature_names)

        save_config_file(config_file_data)
        return instrument_config


def create_db_config(path: str | None = None) -> DbConfig:
    config_file_data = get_config()
    db_config = config_file_data.get("db")
    if db_config:
        raise errors.ConfigError(
            "Database has already been connected to Premia."
        )

    config_file_data["db"] = DbConfig(
        type="DuckDB", path=(path or DEFAULT_DATABASE_PATH)
    )

    save_config_file(config_file_data, create_if_missing=True)
    return config_file_data["db"]


def set_db_config(path: str) -> DbConfig:
    config_file_data = get_config()
    db_config = config_file_data.get("db")
    if db_config is None:
        raise errors.MissingDbError()

    db_config["path"] = path
    save_config_file(config_file_data, create_if_missing=True)
    return db_config


def set_remote_ai_config(api_key: str, model_name: str) -> AiConfig:
    config_file_data = get_config()

    ai_config = config_file_data.get("ai")
    if ai_config is None:
        ai_config = AiConfig(preference="remote")

    ai_config["remote"] = RemoteAiConfig(api_key=api_key, model=model_name)

    config_file_data["ai"] = ai_config
    save_config_file(config_file_data)
    return ai_config


def remove_cached_local_ai_model() -> None:
    local_ai_config = get_local_ai_config_or_raise()

    try:
        shutil.rmtree(local_ai_config["model_path"])
    except OSError as e:
        errors.PremiaError(
            f"""\
Could not delete model cached in: {local_ai_config['model_path']}.
The following error was raised:
{e}"""
        )


def set_local_ai_config(
    model_path: str, model_link: HuggingfaceModelLink
) -> AiConfig:
    config_file_data = get_config()

    ai_config = config_file_data.get("ai")
    if ai_config and ai_config.get("local"):
        remove_cached_local_ai_model()

    if ai_config is None:
        ai_config = AiConfig(preference="local")

    ai_config["local"] = LocalAiConfig(
        model_path=model_path,
        user=model_link["user"],
        repo=model_link["repo"],
        filename=model_link["filename"],
    )

    config_file_data["ai"] = ai_config
    save_config_file(config_file_data)

    return ai_config


def set_ai_config(model_type: types.ModelType) -> AiConfig:
    config_file_data = get_config()
    ai_config = config_file_data.get("ai")
    if ai_config is None:
        raise errors.MissingAiError()

    if ai_config.get(model_type) is None:
        raise errors.ConfigError(
            f"Cannot change the preference to '{model_type}'. No {model_type} AI model has been set up."
        )

    ai_config["preference"] = model_type
    save_config_file(config_file_data)
    return ai_config


def remove_ai_model_config(model_type: types.ModelType) -> AiConfig | None:
    config_file_data = get_config()
    ai_config = config_file_data.get("ai")
    if ai_config is None:
        raise errors.MissingAiError()

    if ai_config.get(model_type) is None:
        return ai_config

    if model_type == "local":
        remove_cached_local_ai_model()

    if model_type == "remote" and ai_config.get("local") is None:
        config_file_data.pop("ai")
        save_config_file(config_file_data)
        return None
    elif model_type == "local" and ai_config.get("remote") is None:
        config_file_data.pop("ai")
        save_config_file(config_file_data)
        return None
    else:
        ai_config.pop(model_type)
        ai_config["preference"] = "remote" if model_type == "local" else "local"
        save_config_file(config_file_data)
        return ai_config


def set_polygon_config(api_key: str) -> ProvidersConfig:
    config_file_data = get_config()
    providers_config = config_file_data.get("providers", {})

    providers_config["polygon"] = api_key
    config_file_data["providers"] = providers_config
    save_config_file(config_file_data)

    return providers_config


def get_polygon_config_or_raise() -> str:
    twelvedata_api_key = get_polygon_config()
    if twelvedata_api_key is None:
        raise errors.MissingApiKeyError("polygon")

    return twelvedata_api_key


def get_polygon_config() -> str | None:
    providers_config = get_providers_config_or_raise()
    return providers_config.get("polygon")


def set_twelvedata_config(api_key: str) -> ProvidersConfig:
    config_file_data = get_config()
    providers_config = config_file_data.get("providers", {})

    providers_config["twelvedata"] = api_key
    config_file_data["providers"] = providers_config
    save_config_file(config_file_data)

    return providers_config


def get_twelvedata_config_or_raise() -> str:
    twelvedata_api_key = get_twelvedata_config()
    if twelvedata_api_key is None:
        raise errors.MissingApiKeyError("twelvedata")

    return twelvedata_api_key


def get_twelvedata_config() -> str | None:
    providers_config = get_providers_config_or_raise()
    return providers_config.get("twelvedata")


def get_providers_config_str(fmt: FormatOption = "yaml") -> str:
    providers_config = get_providers_config()
    if providers_config is None:
        return ""

    if fmt == "json":
        return json.dumps(providers_config, indent=4)
    else:
        return yaml.dump(providers_config).strip()


def get_providers_config_or_raise() -> ProvidersConfig:
    providers_config = get_providers_config()
    if providers_config is None:
        raise errors.MissingProvidersError()

    return providers_config


def get_providers_config() -> ProvidersConfig | None:
    return get_config().get("providers")


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

    instruments_config = db_config.get("instruments")
    if instruments_config is None:
        return None

    return instruments_config.get(instrument)


def get_db_config_or_raise() -> DbConfig:
    db_config = get_db_config()
    if db_config is None:
        raise errors.MissingDbError()

    return db_config


def get_db_config() -> DbConfig | None:
    return get_config().get("db")


def get_db_config_str(fmt: Literal["yaml", "json"] = "yaml") -> str:
    db_config = get_db_config()
    if db_config is None:
        return ""

    if fmt == "json":
        return json.dumps(db_config, indent=4)
    else:
        return yaml.dump(db_config).strip()


def get_remote_ai_config_or_raise() -> RemoteAiConfig:
    remote_ai_config = get_remote_ai_config()
    if remote_ai_config is None:
        raise errors.MissingRemoteAiError()

    return remote_ai_config


def get_remote_ai_config() -> RemoteAiConfig | None:
    ai_config = get_ai_config()
    if ai_config is None:
        return None

    return ai_config.get("remote")


def get_local_ai_config_or_raise() -> LocalAiConfig:
    local_ai_config = get_local_ai_config()
    if local_ai_config is None:
        raise errors.MissingLocalAiError()

    return local_ai_config


def get_local_ai_config() -> LocalAiConfig | None:
    ai_config = get_ai_config()
    if ai_config is None:
        return None

    return ai_config.get("local")


def get_ai_config_or_raise() -> AiConfig:
    ai_config = get_ai_config()
    if ai_config is None:
        raise errors.MissingAiError()

    return ai_config


def get_ai_config() -> AiConfig | None:
    return get_config().get("ai")


def get_ai_config_str(fmt: Literal["yaml", "json"] = "yaml") -> str:
    ai_config = get_ai_config()
    if ai_config is None:
        return ""

    if fmt == "json":
        return json.dumps(ai_config, indent=4)
    else:
        return yaml.dump(ai_config).strip()


def get_config_str(fmt: Literal["yaml", "json"] = "yaml") -> str:
    config_data = get_config()
    if fmt == "json":
        return json.dumps(config_data, indent=4)
    else:
        return yaml.dump(config_data).strip()


def get_config(create_if_missing=False) -> ConfigFileData:
    config_file_path = get_config_file_path(create_if_missing)

    with open(config_file_path, "r") as file:
        config_data: ConfigFileData = json.load(file)
        return config_data


def get_config_file_path(create_if_missing=False) -> str:
    config_dir(create_if_missing)

    if not os.path.exists(CONFIG_FILE_PATH):
        if not create_if_missing:
            raise errors.ConfigError("Premia has not been set up yet.")

        config_file_data = ConfigFileData(version="1")
        with open(CONFIG_FILE_PATH, "w") as file:
            json.dump(config_file_data, file, indent=2)

    return CONFIG_FILE_PATH


def setup() -> str:
    config_dir_path = config_dir(create_if_missing=True)
    get_config_file_path(create_if_missing=True)
    migrations_dir(create_if_missing=True)
    cache_dir(create_if_missing=True)

    return config_dir_path


def get_local_model_path() -> str:
    local_ai_config = get_local_ai_config_or_raise()
    model_path = hf_hub_download(
        repo_id=f"{local_ai_config['user']}/{local_ai_config['repo']}",
        filename=local_ai_config["filename"],
        cache_dir=cache_dir(),
    )

    return model_path


def set_local_model(link: str, force: bool) -> str:
    model_link = parse_huggingface_model_link(link)

    model_path = hf_hub_download(
        repo_id=f"{model_link['user']}/{model_link['repo']}",
        filename=model_link["filename"],
        force_download=force,
        cache_dir=cache_dir(create_if_missing=True),
    )

    set_ai_config(model_type="local")
    set_local_ai_config(model_path, model_link)
    return model_path


def set_remote_model(api_key: str, model_name: str):
    set_remote_ai_config(api_key=api_key, model_name=model_name)
    set_ai_config(model_type="remote")
