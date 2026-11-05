-- T02 part B: graphitic-evidence patterns and review status (disagreement summary).
SELECT evidence_pattern, label_review_status, n_intervals, logged_m
FROM v_label_disagreement
ORDER BY n_intervals DESC, evidence_pattern;
