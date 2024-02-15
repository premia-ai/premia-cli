CREATE OR REPLACE VIEW {{ instrument }}_{{ quantity }}_{{ time_unit }}_averages AS
SELECT time, symbol, average
FROM (
     SELECT
        time,
        symbol,
        AVG(close) OVER (
            PARTITION BY symbol 
            ORDER BY time 
            ROWS BETWEEN {{ quantity - 1 }} PRECEDING AND CURRENT ROW
        ) AS average,
        COUNT(close) OVER (
            PARTITION BY symbol 
            ORDER BY time 
            ROWS BETWEEN {{ quantity - 1 }} PRECEDING AND CURRENT ROW
        ) AS row_count
    FROM {{ reference_table }}
)
WHERE row_count = {{ quantity }};
