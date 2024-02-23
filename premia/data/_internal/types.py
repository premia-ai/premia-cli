from datetime import datetime
from typing import Literal, TypeAlias, TypedDict


ProviderType: TypeAlias = Literal[
    "polygon.io",
    "twelvedata.com",
    "csv",
    "yfinance",
]


class MarketDataRow(TypedDict):
    time: datetime
    symbol: str
    open: str
    close: str
    high: str
    low: str
    volume: str
    currency: str
    data_provider: ProviderType
