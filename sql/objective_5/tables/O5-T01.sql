-- O5-T01 cell counts and relative grid volume by class, zone and depth band (relative depth below collar).
-- name: class_by_zone_band
WITH meta AS (
    SELECT (SELECT CAST(meta_value AS REAL) FROM grid_meta WHERE meta_key = 'cell_volume_m3') AS cell_m3,
           (SELECT CAST(meta_value AS REAL) FROM grid_meta WHERE meta_key = 'depth_band_m') AS band_m
)
SELECT g.zone AS zone,
       g.class_label AS class_label,
       printf('%d-%d m', g.depth_band_top_m, CAST(g.depth_band_top_m + m.band_m AS INTEGER)) AS depth_band_below_collar,
       COUNT(*) AS cells,
       ROUND(COUNT(*) * m.cell_m3, 1) AS relative_volume_m3,
       SUM(g.above_weathering_front) AS cells_above_weathering_front,
       SUM(CASE WHEN g.depth_support = 'DEPTH_EXTRAPOLATED' THEN 1 ELSE 0 END) AS cells_depth_extrapolated
FROM grid_cells g CROSS JOIN meta m
GROUP BY g.zone, g.class_label, g.depth_band_top_m
ORDER BY CASE g.zone WHEN 'INTERPOLATION' THEN 0 WHEN 'EXTRAPOLATION' THEN 1 ELSE 2 END,
         g.depth_band_top_m,
         CASE g.class_label WHEN 'CONFIDENT_PRESENT' THEN 0 WHEN 'CONFIDENT_ABSENT' THEN 1 WHEN 'UNCERTAIN' THEN 2 ELSE 3 END;
