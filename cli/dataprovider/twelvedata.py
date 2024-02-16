import os
import requests
import pandas as pd
from datetime import datetime
from typing import Any
from dataclasses import asdict
from urllib.parse import urlencode
from cli.utils import types, errors
from cli.db import migration


accepted_timespans = [
    types.Timespan.MINUTE,
    types.Timespan.HOUR,
    types.Timespan.DAY,
    types.Timespan.WEEK,
    types.Timespan.MONTH,
]


def import_market_data(api_params: types.ApiParams):
    # TODO: Move the connect function to another module
    con = migration.connect()

    market_data_rows = get_aggregates(api_params)
    rows_df = pd.DataFrame([asdict(row) for row in market_data_rows])
    con = migration.connect()

    try:
        rows_df.to_sql(
            api_params.table, con=con, if_exists="append", index=False
        )
    except Exception as e:
        raise errors.DataImportError(
            f"Failed to copy twelvedata.com data to table '{api_params.table}': {e}"
        )


def get_aggregates(api_params: types.ApiParams):
    api_key = os.getenv("TWELVEDATA_API_KEY")
    if not api_key:
        raise errors.DataImportError(
            "Please set TWELVEDATA_API_KEY environment variable"
        )

    if api_params.timespan not in accepted_timespans:
        raise ValueError(
            f"Timespan '{api_params.timespan.value}' is not supported by twelvedata"
        )

    timespan = types.timespan_info[api_params.timespan].twelvedata_code
    interval = f"{api_params.quantity}{timespan}"

    query = {
        "apikey": api_key,
        "interval": interval,
        "symbol": api_params.symbol,
        "start_date": api_params.start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_date": api_params.end.strftime("%Y-%m-%d %H:%M:%S"),
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
        raise errors.DataImportError(
            f"Error fetching data from TwelveData: {e}"
        )


def convert_to_market_data_rows(data: Any) -> list[types.MarketDataRow]:
    candles: list[types.MarketDataRow] = []
    for time_series_value in data["values"]:
        t = datetime.strptime(
            time_series_value["datetime"], "%Y-%m-%d %H:%M:%S"
        )
        candles.append(
            types.MarketDataRow(
                time=t,
                symbol=data["meta"]["symbol"],
                open=time_series_value["open"],
                close=time_series_value["close"],
                high=time_series_value["high"],
                low=time_series_value["low"],
                volume=time_series_value["volume"],
                currency=data["meta"]["currency"],
                data_provider=types.DataProvider.TWELVE_DATA.value,
            )
        )
    return candles
