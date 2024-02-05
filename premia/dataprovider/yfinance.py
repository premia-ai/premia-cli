import yfinance as yf
from dataclasses import dataclass
from premia.utils import types
from premia.db import migration


@dataclass
class OptionContract(types.OptionSymbol):
    shares_per_contract: int  # 100
    currency: str


accepted_timespans = [
    types.Timespan.MINUTE.value,
    types.Timespan.HOUR.value,
    types.Timespan.DAY.value,
    types.Timespan.WEEK.value,
    types.Timespan.MONTH.value,
]


def import_market_data(api_params: types.ApiParams):
    if api_params.timespan_unit not in accepted_timespans:
        raise ValueError(
            f"Timespan '{api_params.timespan_unit}' is not supported by yfinance"
        )

    timespan = types.timespan_info[api_params.timespan_unit].yfinance_code
    interval = f"{api_params.quantity}{timespan}"

    ticker = yf.Ticker([api_params.ticker])
    ticker_history = ticker.history(
        end=api_params.end.strftime("%Y-%m-%d"),
        start=api_params.start.strftime("%Y-%m-%d"),
        interval=interval,
    )

    ticker_history = (
        ticker_history.stack(level=1)
        .rename_axis(["Time", "Ticker"])
        .reset_index(level=1)
        .drop(columns=["Dividends", "Stock Splits"])
        .rename(columns=str.lower)
        .rename_axis("time")
    )

    con = migration.connect()
    try:
        ticker_history.to_sql(
            api_params.table, con=con, if_exists="append", index=False
        )
    except Exception as e:
        raise types.DataImportError(
            f"Failed to copy yfinance data to table '{api_params.table}': {e}"
        )