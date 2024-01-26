import os
import requests
from datetime import datetime
from typing import Any
import psycopg2
from psycopg2.extras import execute_values
from urllib.parse import urlencode
from utils import types
from db import migration


accepted_timespans = [
    types.Timespan.MINUTE.value,
    types.Timespan.HOUR.value,
    types.Timespan.DAY.value,
    types.Timespan.WEEK.value,
    types.Timespan.MONTH.value,
]


def import_market_data(api_params: types.ApiParams):
    # TODO: Move the Postgres connect function to another module
    conn = migration.connect()

    candles = get_aggregates(api_params)
    columns = list(candles[0].__dict__.keys())
    rows = [tuple(candle.__dict__.values()) for candle in candles]

    try:
        with conn.cursor() as cursor:
            execute_values(
                cursor,
                f"INSERT INTO {api_params.table} ({','.join(columns)}) VALUES %s",
                rows,
            )
        conn.commit()
    except psycopg2.Error as e:
        raise types.DataImportError(e)
    finally:
        conn.close()


def get_aggregates(api_params: types.ApiParams):
    api_key = os.getenv("TWELVEDATA_API_KEY")
    if not api_key:
        raise types.DataImportError(
            "Please set TWELVEDATA_API_KEY environment variable"
        )

    if api_params.timespan_unit not in accepted_timespans:
        raise ValueError(
            f"Timespan '{api_params.timespan_unit}' is not supported by twelvedata"
        )

    timespan = types.timespan_info[api_params.timespan_unit].twelvedata
    interval = f"{api_params.quantity}{timespan}"

    query = {
        "apikey": api_key,
        "interval": interval,
        "symbol": api_params.ticker,
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
        raise types.DataImportError(f"Error fetching data from TwelveData: {e}")


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
                data_provider=types.DataProvider.TwelveData.value,
            )
        )
    return candles
