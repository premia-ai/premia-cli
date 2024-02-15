DROP INDEX IF EXISTS {{ instrument }}_{{ quantity }}_{{ time_unit }}_candles_symbol_time_idx;
DROP TABLE IF EXISTS {{ instrument }}_{{ quantity }}_{{ time_unit }}_candles;
