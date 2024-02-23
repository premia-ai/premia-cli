from typing import cast
from datetime import datetime
from polygon import RESTClient
from polygon.rest import models
import pandas as pd
from premia._shared import types
from premia import config, db
from premia.data import DataError, MarketDataRow

accepted_timespans: list[types.Timespan] = [
    "second",
    "minute",
    "hour",
    "day",
    "week",
    "month",
]


def stocks(
    symbol: str,
    start: datetime,
    end: datetime,
    persist=False,
) -> pd.DataFrame:
    return import_market_data(
        instrument="stocks",
        symbol=symbol,
        start=start,
        end=end,
        persist=persist,
    )


def options(
    symbol: str,
    start: datetime,
    end: datetime,
    persist=False,
) -> pd.DataFrame:
    return import_market_data(
        instrument="options",
        symbol=symbol,
        start=start,
        end=end,
        persist=persist,
    )


def map_agg_to_market_data_row(symbol: str, agg: models.Agg) -> MarketDataRow:
    if agg.timestamp is None:
        raise ValueError(f"Entry needs to have a timestamp: {agg}")

    return MarketDataRow(
        time=datetime.fromtimestamp(float(agg.timestamp / 1000)),
        symbol=symbol,
        open=str(agg.open),
        close=str(agg.close),
        high=str(agg.high),
        low=str(agg.low),
        volume=str(int(agg.volume)) if agg.volume else "",
        currency="USD",
        data_provider="polygon.io",
    )


def import_market_data(
    instrument: types.InstrumentType,
    symbol: str,
    start: datetime,
    end: datetime,
    persist=False,
) -> pd.DataFrame:
    instrument_config = config.get_db_instrument(instrument)
    if instrument_config["timespan"] not in accepted_timespans:
        raise ValueError(
            f"Timespan '{instrument_config['timespan']}' is not supported by polygon.io"
        )

    polygon_api_key = config.get_provider_polygon()
    client = RESTClient(api_key=polygon_api_key)

    try:
        aggs = cast(
            list[models.Agg],
            client.get_aggs(
                ticker=symbol,
                multiplier=1,
                timespan=instrument_config["timespan"],
                from_=start,
                to=end,
            ),
        )
    except Exception as e:
        raise DataError(e)

    market_data_rows = [map_agg_to_market_data_row(symbol, agg) for agg in aggs]
    rows_df = pd.DataFrame(market_data_rows)

    if persist:
        try:
            rows_df.to_sql(
                instrument_config["base_table"],
                con=db.connect(),
                if_exists="append",
                index=False,
            )
        except Exception as e:
            raise DataError(
                f"Failed to copy polygon.io data to table '{instrument_config['base_table']}': {e}"
            )

    return rows_df
