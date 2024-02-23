import requests
import pandas as pd
from datetime import datetime
from typing import Any
from urllib.parse import urlencode
from premia.data import DataError, MarketDataRow
from premia._shared import types
from premia import config, db


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
    stocks_config = config.get_db_instrument("stocks")
    market_data_rows = get_aggregates(
        symbol, start, end, stocks_config["timespan"]
    )
    rows_df = pd.DataFrame(market_data_rows)

    if persist:
        try:
            rows_df.to_sql(
                stocks_config["base_table"],
                con=db.connect(),
                if_exists="append",
                index=False,
            )
        except Exception as e:
            raise DataError(
                f"Failed to copy twelvedata.com data to table '{stocks_config['base_table']}': {e}"
            )

    return rows_df


def get_aggregates(
    symbol: str, start: datetime, end: datetime, timespan: types.Timespan
):
    api_key = config.get_provider_twelvedata()

    if timespan not in accepted_timespans:
        raise ValueError(
            f"Timespan '{timespan}' is not supported by twelvedata"
        )

    timespan_code = types.timespan_info[timespan].twelvedata_code
    interval = f"1{timespan_code}"

    query = {
        "apikey": api_key,
        "interval": interval,
        "symbol": symbol,
        "start_date": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_date": end.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "UTC",
        "format": "JSON",
    }

    url = f"https://api.twelvedata.com/time_series?{urlencode(query)}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return convert_to_market_data_rows(data)

    except requests.RequestException as e:
        raise DataError(f"Error fetching data from TwelveData: {e}")


def convert_to_market_data_rows(data: Any) -> list[MarketDataRow]:
    candles: list[MarketDataRow] = []
    for time_series_value in data["values"]:
        t = datetime.strptime(
            time_series_value["datetime"], "%Y-%m-%d %H:%M:%S"
        )
        candles.append(
            MarketDataRow(
                time=t,
                symbol=data["meta"]["symbol"],
                open=time_series_value["open"],
                close=time_series_value["close"],
                high=time_series_value["high"],
                low=time_series_value["low"],
                volume=time_series_value["volume"],
                currency=data["meta"]["currency"],
                data_provider="twelvedata.com",
            )
        )
    return candles
