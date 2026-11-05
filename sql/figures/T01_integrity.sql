-- T01 part D: latest SQL integrity and reconciliation results stored by `kambale verify`.
SELECT t.test_group, t.test_name, t.expected, t.observed, t.outcome, t.run_utc
FROM validation_test_results t
WHERE t.test_result_id IN (
    SELECT MAX(test_result_id) FROM validation_test_results
    WHERE test_group IN ('SQL_INTEGRITY', 'RECONCILIATION') GROUP BY test_name)
ORDER BY t.test_group, t.test_name;
