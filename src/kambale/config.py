"""Project paths, versions and fixed vocabularies for obj1_master (Stage A)."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_NAME = "Kambale RAB_Collar_Sampling_Geology_2012a.xlsx"
SOURCE_PATH = PROJECT_ROOT / "Kambale RAB_Collar_Sampling_Geology_2012a.xlsx"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
# Verified, read-only copy of the corrected workbook (six comments and 13 rock codes corrected on 2026-11-05).
# The original copy, Kambale RAB_Collar_Sampling_Geology_2012a.xlsx, is kept unchanged as an archive.
RAW_COPY_PATH = RAW_DIR / "Kambale RAB_Collar_Sampling_Geology_2012a_corrected_2026-11-05_rock_codes.xlsx"
DERIVED_DIR = PROJECT_ROOT / "data" / "derived"
DB_PATH = PROJECT_ROOT / "database" / "kambale_thesis.sqlite"
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"
SQL_FIGURES_DIR = PROJECT_ROOT / "sql" / "figures"
CONFIG_DIR = PROJECT_ROOT / "config"
FIGURES_DIR = PROJECT_ROOT / "figures"
TABLES_DIR = PROJECT_ROOT / "tables"
REPORTS_DIR = PROJECT_ROOT / "reports"

REGIONAL_SHP = (
    Path(r"C:/Users/ThinkPad P1 G4/Documents/ArcGIS/GEOLOGY OF GHANA shapefile_New/"
         r"GEOLOGY OF GHANA shapefile/GE0_KOA/GEOMAP1000_shp/Shapefiles/Geology/geology_polygon.shp")
)

# 1.2.0: provisional DEM collar elevations (migration 0014) and the QA wording that reports them.
ETL_VERSION = "1.2.0"
CODE_VERSION = ETL_VERSION

STAGE_STATUS = ("VERIFIED", "PROVISIONAL", "BLOCKED", "DEFERRED", "FAILED")
QC_SEVERITY = ("ERROR", "WARNING", "INFO")
QC_STATUS = ("BLOCKED", "PROVISIONAL", "APPROVED")

LEGEND_DOMAINS = ("RockType", "Colour", "Weathering", "Structure", "RTMineral", "SulMineral", "Veining", "SampleQual")

# Verbatim synopsis objectives (immutable). Used in reports and the figure registry footers.
SYNOPSIS_OBJECTIVES = (
    "To construct and quality-control a three-dimensional drill-hole database and define graphitic domains at the Kambale Graphite Deposit.",
    "To characterize the spatial distribution, geological controls, and continuity of graphitic domains using exploratory spatial analysis and indicator variography.",
    "To develop and spatially validate indicator-geostatistical, machine-learning, and hybrid models for predicting graphitic-domain occurrence.",
    "To evaluate the predictive performance of the developed models using independent spatial validation and probability-based metrics.",
    "To quantify and visualize three-dimensional uncertainty in graphitic-domain occurrence and identify areas of high confidence and high uncertainty.",
)

THESIS_TITLE = (
    "Hybrid Machine Learning–Indicator Geostatistical Modelling for Spatially Validated Three-Dimensional "
    "Prediction and Uncertainty Characterization of Graphitic Domains at the Kambale Graphite Deposit, Ghana"
)
