-- F01 background: regional 1:1,000,000 polygons intersecting the collar buffer (context only).
SELECT feature_index, geo_symbol, stratigraphy, legend_text, geom_wkt, centroid_e_m, centroid_n_m
FROM v_regional_context
ORDER BY feature_index;
