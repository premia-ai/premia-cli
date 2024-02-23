from typing import Literal, TypeAlias
from dataclasses import dataclass


ModelType: TypeAlias = Literal["remote", "local"]
InstrumentType: TypeAlias = Literal["stocks", "options"]
Timespan: TypeAlias = Literal[
    "second",
    "minute",
    "hour",
    "day",
    "week",
    "month",
]


@dataclass
class TimespanInfo:
    one_letter_code: str
    twelvedata_code: str | None
    yfinance_code: str | None
    unit: Timespan
    bigger_timespans: list[Timespan]


timespan_info: dict[Timespan, TimespanInfo] = {
    "second": TimespanInfo(
        one_letter_code="s",
        twelvedata_code=None,
        yfinance_code=None,
        unit="second",
        bigger_timespans=[
            "minute",
            "hour",
            "day",
            "week",
            "month",
        ],
    ),
    "minute": TimespanInfo(
        one_letter_code="m",
        twelvedata_code="min",
        yfinance_code="m",
        unit="minute",
        bigger_timespans=[
            "hour",
            "day",
            "week",
            "month",
        ],
    ),
    "hour": TimespanInfo(
        one_letter_code="h",
        twelvedata_code="h",
        yfinance_code="h",
        unit="hour",
        bigger_timespans=[
            "day",
            "week",
            "month",
        ],
    ),
    "day": TimespanInfo(
        one_letter_code="d",
        twelvedata_code="day",
        yfinance_code="d",
        unit="day",
        bigger_timespans=[
            "week",
            "month",
        ],
    ),
    "week": TimespanInfo(
        one_letter_code="w",
        twelvedata_code="week",
        yfinance_code="wk",
        unit="week",
        bigger_timespans=["month"],
    ),
    "month": TimespanInfo(
        one_letter_code="M",
        twelvedata_code="month",
        yfinance_code="mo",
        unit="month",
        bigger_timespans=[],
    ),
}
