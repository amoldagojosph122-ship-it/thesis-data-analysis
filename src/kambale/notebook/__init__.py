"""Helpers for the results notebook: read-only database access, environment and receipt checks, and two
reproducibility modes (gates and reproduce). Nothing here writes to a real database or to a real output folder.

Modules
  paths        database, output and configuration locations for every objective
  readonly     read-only SQLite access and query helpers
  env          environment summary, config receipts and the database manifest check
  receipts     upstream input hashes recorded in each downstream database
  gates        Mode A: runs every objective's verify step on a copy of the repository
  reproduce    Mode B: regenerates every output on a copy of the repository and compares it with the original
"""
