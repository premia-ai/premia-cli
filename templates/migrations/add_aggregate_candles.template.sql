CREATE MATERIALIZED VIEW {{ instrument_type }}_{{ quantity }}_{{ time_unit }}_candles
WITH (timescaledb.continuous) AS
    SELECT
        time_bucket('{{ quantity }} {{ time_unit }}', time) AS bucket,
        symbol,
        FIRST(open, time) AS "open",
        MAX(high) AS high,
        MIN(low) AS low,
        LAST(close, time) AS "close",
        SUM(volume) AS volume,
        currency
    FROM {{ reference_table }}
    GROUP BY bucket, currency, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('{{ instrument_type }}_{{ quantity }}_{{ time_unit }}_candles',
    start_offset => INTERVAL '3 day',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');
