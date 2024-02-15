from typing import Literal, TypeAlias
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

AiModel: TypeAlias = Literal["remote", "local"]


class InstrumentType(Enum):
    STOCKS = "stocks"
    OPTIONS = "options"


class Timespan(Enum):
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class TimespanInfo:
    one_letter_code: str
    twelvedata_code: str | None
    yfinance_code: str | None
    unit: str
    bigger_timespans: list[Timespan]


timespan_info: dict[Timespan, TimespanInfo] = {
    Timespan.SECOND: TimespanInfo(
        one_letter_code="s",
        twelvedata_code=None,
        yfinance_code=None,
        unit=Timespan.SECOND.value,
        bigger_timespans=[
            Timespan.MINUTE,
            Timespan.HOUR,
            Timespan.DAY,
            Timespan.WEEK,
            Timespan.MONTH,
        ],
    ),
    Timespan.MINUTE: TimespanInfo(
        one_letter_code="m",
        twelvedata_code="min",
        yfinance_code="m",
        unit=Timespan.MINUTE.value,
        bigger_timespans=[
            Timespan.HOUR,
            Timespan.DAY,
            Timespan.WEEK,
            Timespan.MONTH,
        ],
    ),
    Timespan.HOUR: TimespanInfo(
        one_letter_code="h",
        twelvedata_code="h",
        yfinance_code="h",
        unit=Timespan.HOUR.value,
        bigger_timespans=[
            Timespan.DAY,
            Timespan.WEEK,
            Timespan.MONTH,
        ],
    ),
    Timespan.DAY: TimespanInfo(
        one_letter_code="d",
        twelvedata_code="day",
        yfinance_code="d",
        unit=Timespan.DAY.value,
        bigger_timespans=[Timespan.WEEK, Timespan.MONTH],
    ),
    Timespan.WEEK: TimespanInfo(
        one_letter_code="w",
        twelvedata_code="week",
        yfinance_code="wk",
        unit=Timespan.WEEK.value,
        bigger_timespans=[Timespan.MONTH],
    ),
    Timespan.MONTH: TimespanInfo(
        one_letter_code="M",
        twelvedata_code="month",
        yfinance_code="mo",
        unit=Timespan.MONTH.value,
        bigger_timespans=[],
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
    POLYGON = "polygon.io"
    TWELVE_DATA = "twelvedata.com"
    CSV = "csv"
    YFINANCE = "yfinance"


@dataclass
class ApiParams:
    symbol: str
    timespan: Timespan
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


@dataclass
class OptionSymbol:
    symbol: str
    expiration_date: datetime
    contract_type: str
    company_symbol: str
    strike_price: float

    @classmethod
    def parse(cls, symbol: str):
        # Length of the expiration date and strike price parts are fixed
        # Symbol can be flexible in size
        expiration_date_length = 6  # YYMMDD
        contract_length = 1  # C/P
        strike_price_length = 8  # 00000.000

        expiration_date_part = symbol[
            -(
                expiration_date_length + contract_length + strike_price_length
            ) : -(contract_length + strike_price_length)
        ]
        contract_type_part = symbol[
            -(contract_length + strike_price_length) : -strike_price_length
        ]
        strike_price_part = symbol[-strike_price_length:]

        # The remaining part of the symbol is the company symbol
        company_symbol = symbol[
            : -(expiration_date_length + contract_length + strike_price_length)
        ]

        expiration_date = datetime.fromisoformat(
            f"20{expiration_date_part[:2]}-{expiration_date_part[2:4]}-{expiration_date_part[4:6]}"
        )
        contract_type = "call" if contract_type_part == "C" else "put"
        strike_price = float(strike_price_part) / 1000

        return cls(
            symbol=symbol,
            company_symbol=company_symbol,
            expiration_date=expiration_date,
            contract_type=contract_type,
            strike_price=strike_price,
        )
