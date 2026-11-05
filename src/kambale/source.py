"""Source workbook access: hashing, immutable raw copy, and cell-level sheet reads.

Cell values are read with openpyxl exactly as stored (no pandas type coercion), so raw spellings and
trailing spaces are preserved. The original workbook is opened read-only and never written.
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

from kambale.config import RAW_COPY_PATH, SOURCE_PATH


class SourceIntegrityError(RuntimeError):
    """The workbook or its raw copy is missing or does not match the recorded SHA-256 (STOP condition)."""


@dataclass
class SheetGrid:
    name: str
    state: str
    max_row: int
    max_col: int
    formula_cells: int
    rows: dict[int, tuple] = field(default_factory=dict)  # Excel row number -> tuple of raw cell values

    def header(self, row_number: int) -> list[str]:
        return [str(v) if v is not None else "" for v in self.rows.get(row_number, ())]

    def data_rows(self, header_row: int) -> list[tuple[int, tuple]]:
        """Return (excel_row, values) for every non-blank row below the header row."""
        out = []
        for row_number in sorted(self.rows):
            if row_number <= header_row:
                continue
            values = self.rows[row_number]
            if all(v is None or (isinstance(v, str) and v.strip() == "") for v in values):
                continue
            out.append((row_number, values))
        return out


def sha256_file(path: Path | str, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_raw_copy(source: Path = SOURCE_PATH, raw_copy: Path = RAW_COPY_PATH) -> str:
    """Create or verify the immutable raw copy. Returns the SHA-256 of the workbook.

    A raw copy that differs from the source is a STOP condition: the copy is never silently replaced.
    """
    if not source.exists():
        raise SourceIntegrityError(f"source workbook not found: {source}")
    source_hash = sha256_file(source)
    if not raw_copy.exists():
        raw_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, raw_copy)
        try:
            raw_copy.chmod(0o444)
        except OSError:
            pass  # Windows honours only the read-only flag; the hash check below is the real control
    copy_hash = sha256_file(raw_copy)
    if copy_hash != source_hash:
        raise SourceIntegrityError(
            f"raw copy hash {copy_hash} differs from source hash {source_hash}; refusing to continue"
        )
    return source_hash


def read_workbook(path: Path = RAW_COPY_PATH) -> dict[str, SheetGrid]:
    """Read every sheet cell-by-cell. Hidden sheets are included and flagged by state."""
    workbook = openpyxl.load_workbook(str(path), data_only=False, read_only=False)
    try:
        sheets: dict[str, SheetGrid] = {}
        for ws in workbook.worksheets:
            formula_cells = 0
            rows: dict[int, tuple] = {}
            max_col = ws.max_column or 0
            for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=max_col):
                values = tuple(cell.value for cell in row)
                for value in values:
                    if isinstance(value, str) and value.startswith("="):
                        formula_cells += 1
                rows[row[0].row] = values
            sheets[ws.title] = SheetGrid(
                name=ws.title,
                state=ws.sheet_state,
                max_row=ws.max_row or 0,
                max_col=max_col,
                formula_cells=formula_cells,
                rows=rows,
            )
        return sheets
    finally:
        workbook.close()


def blank_columns(sheet: SheetGrid, header_row: int) -> list[str]:
    """Header names whose data cells are blank in every data row."""
    header = sheet.header(header_row)
    data = [values for _, values in sheet.data_rows(header_row)]
    blanks = []
    for index, name in enumerate(header):
        if not name:
            continue
        if all(index >= len(v) or v[index] is None or (isinstance(v[index], str) and v[index].strip() == "")
               for v in data):
            blanks.append(name)
    return blanks
