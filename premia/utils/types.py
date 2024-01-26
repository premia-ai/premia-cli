from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class InstrumentType(Enum):
    Stocks = "stocks"
    Options = "options"


class Timespan(Enum):
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


@dataclass
class TimespanInfo:
    one_letter_code: str
    twelvedata: str | None
    unit: str
    bigger_units: list[str]


timespan_info: dict[str, TimespanInfo] = {
    Timespan.SECOND.value: TimespanInfo(
        one_letter_code="s",
        twelvedata=None,
        unit=Timespan.SECOND.value,
        bigger_units=[
            Timespan.MINUTE.value,
            Timespan.HOUR.value,
            Timespan.DAY.value,
            Timespan.WEEK.value,
        ],
    ),
    Timespan.MINUTE.value: TimespanInfo(
        one_letter_code="m",
        twelvedata="min",
        unit=Timespan.MINUTE.value,
        bigger_units=[
            Timespan.HOUR.value,
            Timespan.DAY.value,
            Timespan.WEEK.value,
        ],
    ),
    Timespan.HOUR.value: TimespanInfo(
        one_letter_code="h",
        twelvedata="h",
        unit=Timespan.HOUR.value,
        bigger_units=[
            Timespan.DAY.value,
            Timespan.WEEK.value,
        ],
    ),
    Timespan.DAY.value: TimespanInfo(
        one_letter_code="d",
        twelvedata="day",
        unit="day",
        bigger_units=[
            Timespan.WEEK.value,
        ],
    ),
    Timespan.WEEK.value: TimespanInfo(
        one_letter_code="w",
        twelvedata="week",
        unit="week",
        bigger_units=[],
    ),
}

market_data_column_names = [
    "time",
    "symbol",
    "open",
    "close",
    "high",
    "low",
    "volume",
    "currency",
    "data_provider",
]


class DataProvider(Enum):
    Polygon = "polygon.io"
    TwelveData = "twelvedata.com"
    Csv = "csv"


@dataclass
class ApiParams:
    ticker: str
    timespan_unit: str
    quantity: int
    start: datetime
    end: datetime
    table: str


@dataclass
class MarketDataRow:
    time: datetime
    symbol: str
    open: str
    close: str
    high: str
    low: str
    volume: str
    currency: str
    data_provider: str


class ConfigError(Exception):
    """Custom exception class for config directory related errors."""

    pass


class DataImportError(Exception):
    """Custom exception class for data import related errors."""

    pass


class MigrationError(Exception):
    """Custom exception class for migration errors."""

    pass


class WizardError(Exception):
    """Custom exception class for errors that occur during wizard flows."""

    pass
