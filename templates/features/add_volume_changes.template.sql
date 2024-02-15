CREATE OR REPLACE VIEW {{ instrument }}_{{ quantity }}_{{ time_unit }}_volume_changes AS
SELECT 
    "time", 
    symbol, 
    ((volume - previous_volume) / previous_volume) * 100 AS volume_change
FROM (
    SELECT 
        *, 
        LAG(volume) OVER(PARTITION BY symbol ORDER BY "time") AS previous_volume 
    FROM {{ reference_table }}
) 
WHERE previous_volume IS NOT NULL;
