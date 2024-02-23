CREATE VIEW {{ instrument }}_{{ quantity }}_{{ timespan }}_candles AS
SELECT
    DATE_TRUNC('{{ timespan }}', time) as time,
    symbol,
    FIRST(open) as open,
    LAST(close) as close,
    MAX(high) as high,
    MIN(low) as low,
    SUM(volume) as volume,
    currency,
    data_provider
FROM
    {{ reference_table }}
GROUP BY
    time,
    symbol,
    currency,
    data_provider
ORDER BY
    symbol,
    time DESC;
