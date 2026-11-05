**T01: Workbook inventory, reconciliation and integrity checks [T01_inventory] (obj1_master eefc5858c1ef; PROVISIONAL where labels or coordinates are used)**

| sheet_name | sheet_state | n_rows | n_cols | header_json | blank_columns_json |
|---|---|---|---|---|---|
| Collars | visible | 72 | 14 | ["HoleID", "Grid", "HoleType", "Northing", "Easting", "RL", "UTMNorthing", "UTMEasting", "max_depth", "Project", "Prospect", "Contractor", "LoggedBy", "DateDrilled"] | ["RL", "Contractor"] |
| Logging | visible | 1911 | 19 | ["HOLEID", "DEPTH_FROM", "DEPTH_TO", "rock_type1", "colour1", "colour2", "weathering", "grainsize", "structure", "alt_min1", "alt_min1int", "alt_min2", "alt_min2int", "sul_min1", "sul_min1pc", "vn_type", "vn_pc", "Comment", "sample_quality"] | ["structure", "sul_min1", "sul_min1pc", "vn_type", "vn_pc", "sample_quality"] |
| Logging Legend | visible | 205 | 4 | ["", "Legend Reference", "Legend Value", "Description"] | [] |
| Surveys | visible | 72 | 6 | ["HoleID", "depth", "dip", "azimuth", "SurveyedBy", "Instrument"] | ["SurveyedBy", "Instrument"] |
| ___CollarReferences | hidden | 54 | 5 | ["Collars_Grid", "Collars_HoleType", "Collars_ProjectCode", "Collars_ProspectCode", "Collars_DrillContractorID"] | [] |
| ___LoggingReferences | hidden | 74 | 8 | ["RockType", "Colour", "Weathering", "Structure", "RTMineral", "SulMineral", "Veining", "SampleQual"] | [] |
| ___SheetInfo | hidden | 3 | 2 | ["LoggerTemplate:", "CDT_Logging"] | [] |
| ___SurveyReferences | hidden | 14 | 2 | ["Surveys_DHSurveyorID", "Surveys_SurveyInstrumentID"] | [] |
