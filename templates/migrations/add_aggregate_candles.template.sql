CREATE VIEW {{ instrument }}_{{ quantity }}_{{ time_unit }}_candles AS
SELECT
    DATE_TRUNC('{{ time_unit }}', time) as time,
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
