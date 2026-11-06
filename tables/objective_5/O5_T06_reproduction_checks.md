# O5-T06. Scenario reproduction checks

Mean simulated frequency against the mean local mean over the domain (WARN above 0.05). Down-hole indicator semivariogram of realisations 1-5 against the data semivariogram on the Objective 2 lag bins; reported, not gated.
Source: sql/objective_5/tables/O5-T06.sql, receipt 1, 36 rows.

| scenario_id | check_id | simulated | reference | difference | status | basis |
|---|---|---|---|---|---|---|
| DATA | DOWNHOLE_DATA_VS_O2_MAX_ABS_DIFF | 0 |  |  | REPORTED | data semivariance recomputed here against the stored Objective 2 DOWNHOLE_WITHIN bins |
| SIS_AH015 | DOWNHOLE_GAMMA_LAG_1 | 0.023165 | 0.036411 | -0.013245 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH015 | DOWNHOLE_GAMMA_LAG_10 | 0.145856 | 0.161712 | -0.015856 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH015 | DOWNHOLE_GAMMA_LAG_20 | 0.193131 | 0.212121 | -0.01899 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH015 | DOWNHOLE_GAMMA_LAG_30 | 0.230303 | 0.280303 | -0.05 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH015 | DOWNHOLE_GAMMA_LAG_5 | 0.093728 | 0.114404 | -0.020675 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH015 | DOWNHOLE_MAX_ABS_DIFF_SUPPORTED_BINS | 0.052564 |  |  | REPORTED | maximum over supported bins of \|simulated mean - data\| |
| SIS_AH015 | MEAN_FREQUENCY_VS_MEAN_LOCAL_MEAN | 0.297238 | 0.299885 | -0.002647 | PASS | domain nodes; WARN when the absolute difference exceeds 0.05 |
| SIS_AH025 | DOWNHOLE_GAMMA_LAG_1 | 0.029759 | 0.036411 | -0.006651 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH025 | DOWNHOLE_GAMMA_LAG_10 | 0.15009 | 0.161712 | -0.011622 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH025 | DOWNHOLE_GAMMA_LAG_20 | 0.210101 | 0.212121 | -0.00202 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH025 | DOWNHOLE_GAMMA_LAG_30 | 0.249242 | 0.280303 | -0.031061 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH025 | DOWNHOLE_GAMMA_LAG_5 | 0.110613 | 0.114404 | -0.00379 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH025 | DOWNHOLE_MAX_ABS_DIFF_SUPPORTED_BINS | 0.033333 |  |  | REPORTED | maximum over supported bins of \|simulated mean - data\| |
| SIS_AH025 | MEAN_FREQUENCY_VS_MEAN_LOCAL_MEAN | 0.292319 | 0.299885 | -0.007566 | PASS | domain nodes; WARN when the absolute difference exceeds 0.05 |
| SIS_AH050 | DOWNHOLE_GAMMA_LAG_1 | 0.034002 | 0.036411 | -0.002408 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH050 | DOWNHOLE_GAMMA_LAG_10 | 0.162342 | 0.161712 | 0.000631 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH050 | DOWNHOLE_GAMMA_LAG_20 | 0.209697 | 0.212121 | -0.002424 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH050 | DOWNHOLE_GAMMA_LAG_30 | 0.274242 | 0.280303 | -0.006061 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH050 | DOWNHOLE_GAMMA_LAG_5 | 0.11785 | 0.114404 | 0.003446 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH050 | DOWNHOLE_MAX_ABS_DIFF_SUPPORTED_BINS | 0.013333 |  |  | REPORTED | maximum over supported bins of \|simulated mean - data\| |
| SIS_AH050 | MEAN_FREQUENCY_VS_MEAN_LOCAL_MEAN | 0.291311 | 0.299885 | -0.008575 | PASS | domain nodes; WARN when the absolute difference exceeds 0.05 |
| SIS_AH100 | DOWNHOLE_GAMMA_LAG_1 | 0.038475 | 0.036411 | 0.002064 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH100 | DOWNHOLE_GAMMA_LAG_10 | 0.161441 | 0.161712 | -0.00027 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH100 | DOWNHOLE_GAMMA_LAG_20 | 0.208081 | 0.212121 | -0.00404 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH100 | DOWNHOLE_GAMMA_LAG_30 | 0.269697 | 0.280303 | -0.010606 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH100 | DOWNHOLE_GAMMA_LAG_5 | 0.122329 | 0.114404 | 0.007926 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH100 | DOWNHOLE_MAX_ABS_DIFF_SUPPORTED_BINS | 0.01859 |  |  | REPORTED | maximum over supported bins of \|simulated mean - data\| |
| SIS_AH100 | MEAN_FREQUENCY_VS_MEAN_LOCAL_MEAN | 0.293633 | 0.299885 | -0.006252 | PASS | domain nodes; WARN when the absolute difference exceeds 0.05 |
| SIS_AH200 | DOWNHOLE_GAMMA_LAG_1 | 0.040539 | 0.036411 | 0.004128 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH200 | DOWNHOLE_GAMMA_LAG_10 | 0.164775 | 0.161712 | 0.003063 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH200 | DOWNHOLE_GAMMA_LAG_20 | 0.209697 | 0.212121 | -0.002424 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH200 | DOWNHOLE_GAMMA_LAG_30 | 0.265909 | 0.280303 | -0.014394 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH200 | DOWNHOLE_GAMMA_LAG_5 | 0.126327 | 0.114404 | 0.011923 | REPORTED | mean over realisations 1-5; data semivariance of binary intervals |
| SIS_AH200 | DOWNHOLE_MAX_ABS_DIFF_SUPPORTED_BINS | 0.017949 |  |  | REPORTED | maximum over supported bins of \|simulated mean - data\| |
| SIS_AH200 | MEAN_FREQUENCY_VS_MEAN_LOCAL_MEAN | 0.299825 | 0.299885 | -0.00006 | PASS | domain nodes; WARN when the absolute difference exceeds 0.05 |
