-- F07: strict graphitic interval counts by 5-m measured-depth bin and weathering class.
-- Denominator per bin: all intervals in that bin (n_all).
SELECT depth_bin_from_m, weathering_class, n_all, n_strict_positive, n_strict_negative, n_strict_unresolved
FROM v_depth_weathering
ORDER BY depth_bin_from_m, weathering_class;
