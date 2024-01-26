CREATE TABLE IF NOT EXISTS {{ instrument_type }}_{{ quantity }}_{{ time_unit }}_candles (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    open NUMERIC NULL,
    close NUMERIC NULL,
    high NUMERIC NULL,
    low NUMERIC NULL,
    volume INT NULL,
    currency TEXT NOT NULL,
    data_provider TEXT NOT NULL
);

SELECT create_hypertable('{{ instrument_type }}_{{ quantity }}_{{ time_unit }}_candles', by_range('time'));

CREATE UNIQUE INDEX IF NOT EXISTS {{ instrument_type }}_{{ quantity }}_{{ time_unit }}_candles_symbol_time_idx
ON {{ instrument_type }}_{{ quantity }}_{{ time_unit }}_candles (symbol, time DESC);
