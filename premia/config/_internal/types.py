import re
from typing import TypeAlias, TypedDict, NotRequired, Literal
from premia._shared import InstrumentType, Timespan, ModelType

FormatOption: TypeAlias = Literal["yaml", "json"]


class ProvidersConfig(TypedDict):
    twelvedata: NotRequired[str]
    polygon: NotRequired[str]


class InstrumentConfig(TypedDict):
    base_table: str
    metadata_table: str
    timespan: Timespan
    feature_names: NotRequired[list[str]]
    aggregate_timespans: NotRequired[list[Timespan]]


class DbConfig(TypedDict):
    type: Literal["DuckDB"]
    path: str
    instruments: NotRequired[dict[InstrumentType, InstrumentConfig]]


class RemoteAiConfig(TypedDict):
    api_key: str
    model: str


class LocalAiConfig(TypedDict):
    user: str
    repo: str
    filename: str
    model_path: str


class AiConfig(TypedDict):
    preference: ModelType
    local: NotRequired[LocalAiConfig]
    remote: NotRequired[RemoteAiConfig]


class ConfigFileData(TypedDict):
    version: str
    db: NotRequired[DbConfig]
    ai: NotRequired[AiConfig]
    providers: NotRequired[ProvidersConfig]


class HuggingfaceModelLink(TypedDict):
    user: str
    repo: str
    filename: str


def parse_huggingface_model_link(link: str) -> HuggingfaceModelLink:
    # Example: https://huggingface.co/TheBloke/Mistral-7B-v0.1-GGUF/blob/main/mistral-7b-v0.1.Q4_K_M.gguf
    pattern = r"^https://huggingface\.co/([^/]+)/([^/]+)/blob/[^/]+/(.+)$"
    match = re.match(pattern, link)
    if match:
        return HuggingfaceModelLink(
            user=match.group(1),
            repo=match.group(2),
            filename=match.group(3),
        )
    else:
        raise ValueError(f"The model link you entered is not supported: {link}")
