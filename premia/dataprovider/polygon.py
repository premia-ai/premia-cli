import os
from typing import cast
from polygon import RESTClient
from polygon.rest import models
from psycopg2.extras import execute_values
from datetime import datetime
from utils import types
from db import migration

accepted_timespans = [
    types.Timespan.SECOND.value,
    types.Timespan.MINUTE.value,
    types.Timespan.HOUR.value,
    types.Timespan.DAY.value,
    types.Timespan.WEEK.value,
    types.Timespan.MONTH.value,
    types.Timespan.QUARTER.value,
    types.Timespan.YEAR.value,
]


def map_agg_to_market_data_row(
    ticker: str, agg: models.Agg
) -> types.MarketDataRow:
    if agg.timestamp is None:
        raise ValueError(f"Entry needs to have a timestamp: {agg}")

    return types.MarketDataRow(
        time=datetime.fromtimestamp(float(agg.timestamp / 1000)),
        symbol=ticker,
        open=str(agg.open),
        close=str(agg.close),
        high=str(agg.high),
        low=str(agg.low),
        volume=str(int(agg.volume)) if agg.volume else "",
        currency="USD",
        data_provider=types.DataProvider.Polygon.value,
    )


def import_market_data(api_params: types.ApiParams) -> None:
    if api_params.timespan_unit not in accepted_timespans:
        raise ValueError(
            f"Timespan '{api_params.timespan_unit}' is not supported by polygon.io"
        )

    client = RESTClient(api_key=os.getenv("POLYGON_API_KEY"))

    try:
        aggs = cast(
            list[models.Agg],
            client.get_aggs(
                ticker=api_params.ticker,
                multiplier=api_params.quantity,
                timespan=api_params.timespan_unit,
                from_=api_params.start,
                to=api_params.end,
            ),
        )
    except Exception as e:
        raise types.DataImportError(e)

    market_data_rows = [
        map_agg_to_market_data_row(api_params.ticker[0], agg) for agg in aggs
    ]
    columns = list(market_data_rows[0].__dict__.keys())
    rows = [tuple(mdr.__dict__.values()) for mdr in market_data_rows]

    conn = migration.connect()
    try:
        with conn.cursor() as cursor:
            execute_values(
                cursor,
                f"INSERT INTO {api_params.table} ({', '.join(columns)}) VALUES %s",
                rows,
            )
        conn.commit()
    except Exception as e:
        raise types.DataImportError(
            f"Failed to copy polygon.io data to database: {e}"
        )

    conn.close()
