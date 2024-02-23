import warnings
from datetime import datetime
import yfinance as yf
import pandas as pd
from premia._shared import types
from premia.data import DataError
from premia import config, db

# Pandas is creating a warning because we are not using SQLAlchemy
# as a connector.
warnings.simplefilter(action="ignore", category=UserWarning)


accepted_timespans: list[types.Timespan] = [
    "minute",
    "hour",
    "day",
    "week",
    "month",
]


def stocks(
    symbol: str, start: datetime, end: datetime, persist=False
) -> pd.DataFrame:
    instrument_config = config.get_db_instrument("stocks")
    if instrument_config["timespan"] not in accepted_timespans:
        raise ValueError(
            f"Timespan '{instrument_config['timespan']}' is not supported by yfinance"
        )

    timespan_code = types.timespan_info[
        instrument_config["timespan"]
    ].yfinance_code
    interval = f"1{timespan_code}"

    ticker = yf.Ticker(symbol)
    ticker_history = ticker.history(
        end=end.strftime("%Y-%m-%d"),
        start=start.strftime("%Y-%m-%d"),
        interval=interval,
    )

    ticker_history = (
        ticker_history.rename_axis("time")
        .drop(columns=["Dividends", "Stock Splits"])
        .rename(columns=str.lower)
        .reset_index()
    )

    # ticker_history = (
    #     ticker_history.stack(level=1)
    #     .rename_axis(["Time", "Ticker"])
    #     .reset_index(level=1)
    #     .drop(columns=["Dividends", "Stock Splits"])
    #     .rename(columns=str.lower)
    #     .rename(columns={"ticker": "symbol"})
    #     .rename_axis("time")
    # )

    ticker_history["symbol"] = symbol.upper()
    ticker_history["currency"] = "USD"
    ticker_history["data_provider"] = "yfinance"

    if persist:
        try:
            ticker_history.to_sql(
                instrument_config["base_table"],
                con=db.connect(),
                if_exists="append",
                index=False,
            )
        except Exception as e:
            raise DataError(
                f"Failed to copy yfinance data to table '{instrument_config['base_table']}': {e}"
            )

    return ticker_history
