import os
from cli.db import migration
from cli.utils import types, config


def raw_data_from_csv(
    instrument: types.InstrumentType,
    candles_csv_path: str | None = None,
    metadata_csv_path: str | None = None,
):
    instrument_config = config.get_instrument_config_or_raise(instrument)
    if candles_csv_path:
        migration.copy_csv(
            os.path.expanduser(candles_csv_path),
            instrument_config.base_table,
        )
    if metadata_csv_path:
        migration.copy_csv(
            os.path.expanduser(metadata_csv_path),
            instrument_config.metadata_table,
        )
