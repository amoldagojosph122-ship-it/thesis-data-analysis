"""Objective 4: independent spatial validation and probability-based performance evaluation.

Reads Objective 1, 2 and 3 read-only, freezes the Objective 3 out-of-fold prediction snapshot, and writes evaluation
metrics, calibration diagnostics, paired comparisons, a locked model-selection decision and the Objective 5 handoff to
database/kambale_obj4_validation.sqlite.
"""

O4_CODE_VERSION = "4.0.0"
O4_SCHEMA_VERSION = "O4-SCHEMA-2026.11.05-1"
