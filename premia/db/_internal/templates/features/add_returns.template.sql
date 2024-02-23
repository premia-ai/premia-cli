CREATE OR REPLACE VIEW {{ instrument }}_{{ quantity }}_{{ timespan }}_returns AS
SELECT 
    "time", 
    symbol, 
    ((close - previous_close) / previous_close) * 100 AS return  
FROM (
    SELECT 
        *, 
        LAG(close) OVER(PARTITION BY symbol ORDER BY "time") AS previous_close 
    FROM {{ reference_table }}
) 
WHERE previous_close IS NOT NULL;
