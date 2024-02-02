import os
from typing import cast
from polygon import RESTClient
from polygon.rest import models
from datetime import datetime
import pandas as pd
from dataclasses import asdict
from premia.utils import types
from premia.db import migration

accepted_timespans = [
    types.Timespan.SECOND.value,
    types.Timespan.MINUTE.value,
    types.Timespan.HOUR.value,
    types.Timespan.DAY.value,
    types.Timespan.WEEK.value,
    types.Timespan.MONTH.value,
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
        data_provider=types.DataProvider.POLYGON.value,
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
    rows_df = pd.DataFrame([asdict(row) for row in market_data_rows])
    con = migration.connect()

    try:
        rows_df.to_sql(
            api_params.table, con=con, if_exists="append", index=False
        )
    except Exception as e:
        raise types.DataImportError(
            f"Failed to copy polygon.io data to table '{api_params.table}': {e}"
        )

    con.close()
