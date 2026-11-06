"""Objective 3: indicator geostatistics, machine learning and hybrid occurrence models.

Reads Objective 1 (authoritative geology, labels, geometry) and Objective 2 (support diagnostics and the continuity
handoff) read-only. Writes fold-specific models, hyperparameters, out-of-fold predictions, failure masks, diagnostics,
gate results and the Objective 4 handoff to database/kambale_obj3_models.sqlite.
"""

O3_CODE_VERSION = "3.0.0"
O3_SCHEMA_VERSION = "O3-SCHEMA-2026.11.05-1"
