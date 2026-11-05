-- O2-T03 variogram fitting report for one receipt: every base and sensitivity fit, with nugget, structured sill, range,
-- objective, identifiability and stability. Leave-one-line-out refits are summarised by the envelope columns, not listed.
-- role: HANDOFF_BASIS (lateral between-hole family), REPORTED_3D, REPORTED_WITHIN_HOLE, EXPLORATORY_DIRECTIONAL, SENSITIVITY.
-- name: fit_report
SELECT
    CASE WHEN e.variant = 'BASE' AND e.direction_id = 'LATERAL_BETWEEN' THEN 'HANDOFF_BASIS'
         WHEN e.variant = 'BASE' AND e.direction_id = 'OMNI_3D_BETWEEN' THEN 'REPORTED_3D'
         WHEN e.variant = 'BASE' AND e.direction_id = 'DOWNHOLE_WITHIN' THEN 'REPORTED_WITHIN_HOLE'
         WHEN e.variant = 'BASE' THEN 'EXPLORATORY_DIRECTIONAL'
         ELSE 'SENSITIVITY' END AS role,
    e.direction_id,
    e.variant,
    f.model,
    f.fit_status,
    f.stability_status,
    f.n_bins_used,
    ROUND(f.objective_value, 3) AS objective,
    f.admissible,
    ROUND(f.marginal_departure, 3) AS marginal_departure,
    ROUND(MAX(CASE WHEN p.parameter = 'nugget' THEN p.estimate END), 4) AS nugget,
    ROUND(MAX(CASE WHEN p.parameter = 'structured_sill' THEN p.estimate END), 4) AS structured_sill,
    ROUND(MAX(CASE WHEN p.parameter = 'range_m' THEN p.estimate END), 2) AS range_m,
    ROUND(MAX(CASE WHEN p.parameter = 'range_m' THEN p.leave_one_line_min END), 2) AS range_loo_min_m,
    ROUND(MAX(CASE WHEN p.parameter = 'range_m' THEN p.leave_one_line_max END), 2) AS range_loo_max_m,
    CASE WHEN e.variant = 'BASE' AND e.direction_id = 'LATERAL_BETWEEN'
         THEN (SELECT h.decision_status FROM continuity_handoff_decisions h
               WHERE h.receipt_id = e.receipt_id ORDER BY h.handoff_id DESC LIMIT 1)
         ELSE 'not a handoff basis' END AS handoff_status,
    f.reason
FROM variogram_fits f
JOIN variogram_experiments e ON e.experiment_id = f.experiment_id
LEFT JOIN variogram_fit_parameters p ON p.fit_id = f.fit_id
WHERE e.receipt_id = :receipt_id
  AND NOT EXISTS (SELECT 1 FROM sensitivity_runs s
                  WHERE s.experiment_id = e.experiment_id AND s.changed_factor = 'excluded_line')
GROUP BY f.fit_id
ORDER BY role, e.direction_id, e.variant, f.model;
