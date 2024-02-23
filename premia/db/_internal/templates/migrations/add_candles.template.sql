CREATE TABLE IF NOT EXISTS {{ instrument }}_{{ quantity }}_{{ timespan }}_candles (
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

CREATE UNIQUE INDEX IF NOT EXISTS {{ instrument }}_{{ quantity }}_{{ timespan }}_candles_symbol_time_idx
ON {{ instrument }}_{{ quantity }}_{{ timespan }}_candles (symbol, time DESC);
