-- this also drops the related continuous aggregrate policy
DROP VIEW IF EXISTS {{ instrument }}_{{ quantity }}_{{ time_unit }}_candles;
