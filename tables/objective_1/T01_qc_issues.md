**T01: Workbook inventory, reconciliation and integrity checks [T01_qc_issues] (obj1_master 55dead7da64c; PROVISIONAL where labels or coordinates are used)**

| check_id | category | severity | status | result | n_records | description |
|---|---|---|---|---|---|---|
| QC-CODE-ROCK-UNSUPPORTED | Codes | ERROR | APPROVED | PASS | 0 | rock_type1 code not in logging legend |
| QC-DATE | Metadata | ERROR | APPROVED | PASS | 71 | DateDrilled parses under the explicit format %d-%m-%Y |
| QC-DEPTH-INTERVAL | Depth | ERROR | APPROVED | PASS | 0 | Non-numeric, negative or DEPTH_FROM >= DEPTH_TO intervals |
| QC-DUP-LOG | Duplicates | ERROR | APPROVED | PASS | 0 | Duplicate logging interval (hole, DEPTH_FROM) |
| QC-DUP-SURVEY | Duplicates | ERROR | APPROVED | PASS | 0 | Duplicate survey station (hole, depth) |
| QC-HOLEID-DUP | Identifiers | ERROR | APPROVED | PASS | 0 | Duplicate normalised HoleID in Collars |
| QC-ORPHAN-LOG | Referential | ERROR | APPROVED | PASS | 0 | Logging interval whose hole is not in Collars |
| QC-ORPHAN-SURVEY | Referential | ERROR | APPROVED | PASS | 0 | Survey record whose hole is not in Collars |
| QC-OVERLAP | Depth | ERROR | APPROVED | PASS | 0 | Overlapping logging intervals within a hole |
| QC-QUARANTINE | Curation | ERROR | APPROVED | PASS | 0 | Records excluded from curated tables by a hard rule |
| QC-SRC-HASH | Provenance | ERROR | APPROVED | PASS | 0 | Workbook SHA-256 equals raw copy SHA-256 |
| QC-SURVEY-RANGE | Survey | ERROR | APPROVED | PASS | 0 | Dip outside [-90, 0] or azimuth outside [0, 360) |
| QC-CODE-WEATHER-MISSING | Codes | WARNING | PROVISIONAL | FAIL | 21 | weathering blank |
| QC-COMMENT-TRACE | Labels | WARNING | PROVISIONAL | FAIL | 56 | Graphite comment qualified by 'trace' (false-positive review) |
| QC-COORD-PAIR | Coordinates | WARNING | APPROVED | FAIL | 17 | Discrepancy between UTM and Easting/Northing pairs |
| QC-GRAINSIZE | Codes | WARNING | PROVISIONAL | FAIL | 513 | grainsize values present without documented unit |
| QC-INTENSITY | Codes | WARNING | PROVISIONAL | FAIL | 16 | alt_min1int present without alt_min1 code |
| QC-INTENSITY-UNITS | Codes | WARNING | PROVISIONAL | FAIL | 0 | alt_min1int unit undocumented |
| QC-LABEL-CONFLICT | Labels | WARNING | PROVISIONAL | FAIL | 126 | Intervals with mixed graphite evidence |
| QC-PROJECT | Metadata | WARNING | PROVISIONAL | FAIL | 5 | Project code inconsistent with prospect |
| QC-RL | Vertical | WARNING | BLOCKED | FAIL | 71 | Collar RL present |
| QC-SURVEY-META | Survey | WARNING | PROVISIONAL | FAIL | 71 | SurveyedBy and Instrument blank in source |
| QC-SURVEY-STATIONS | Survey | WARNING | PROVISIONAL | FAIL | 71 | Number and type of survey stations per hole |
| QC-SURVEY-UNIFORM | Survey | WARNING | PROVISIONAL | FAIL | 71 | Dip and azimuth identical across all holes |
| QC-CODE-COLOUR-MISSING | Codes | INFO | PROVISIONAL | FAIL | 6 | colour1 blank |
| QC-CONTRACTOR | Metadata | INFO | PROVISIONAL | FAIL | 71 | Contractor blank in source |
| QC-LABEL-RECON | Labels | INFO | PROVISIONAL | FAIL | 1910 | Evidence distribution versus ThesisDesign.docx |
| QC-SGS-COUNT | Labels | INFO | PROVISIONAL | FAIL | 530 | Sgs interval count versus ThesisDesign.docx |
