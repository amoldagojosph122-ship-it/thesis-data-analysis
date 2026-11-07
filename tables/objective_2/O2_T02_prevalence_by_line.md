# O2-T02. Indicator prevalence, ambiguity and missingness by line

Prevalence is the positive share of binary intervals. Missingness counts blank rock codes and blank weathering codes.
Source: sql/objective_2/tables/O2-T02.sql, receipt 1, 6 rows.

| line_code | n_holes | n_intervals | binary_n | positive_n | negative_n | ambiguous_n | unresolved_n | rock_code_missing | weathering_missing | prevalence_binary | excluded_share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NOM_N1111930 | 3 | 84 | 84 | 29 | 55 | 0 | 0 | 0 | 0 | 0.3452 | 0 |
| NOM_N1112140 | 13 | 440 | 429 | 217 | 212 | 11 | 0 | 0 | 0 | 0.5058 | 0.025 |
| NOM_N1112500 | 21 | 542 | 528 | 130 | 398 | 14 | 0 | 0 | 10 | 0.2462 | 0.0258 |
| NOM_N1112600 | 15 | 423 | 401 | 133 | 268 | 22 | 0 | 0 | 5 | 0.3317 | 0.052 |
| NOM_N1113000 | 19 | 421 | 387 | 16 | 371 | 34 | 0 | 0 | 6 | 0.0413 | 0.0808 |
| ALL | 71 | 1910 | 1829 | 525 | 1304 | 81 | 0 | 0 | 21 | 0.287 | 0.0424 |
