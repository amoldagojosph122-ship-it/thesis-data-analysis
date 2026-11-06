"""Environment summary, configuration receipts and the database manifest check. All read-only."""

from __future__ import annotations

import hashlib
import platform
import re
import subprocess
import sys
import tomllib
from importlib import metadata
from pathlib import Path

import pandas as pd
import yaml

from kambale.config import PROJECT_ROOT
from kambale.notebook.paths import CONFIG_FILES, OBJECTIVE_LABELS

NOTEBOOK_EXTRAS = ("jupyter", "nbformat", "nbconvert", "nbclient", "papermill", "ipykernel")
MANIFEST_PATH = PROJECT_ROOT / "database" / "MANIFEST.md"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def _dependency_names() -> list[str]:
    data = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    names = []
    for dep in data["project"]["dependencies"]:
        names.append(re.split(r"[<>=!~\[; ]", dep, maxsplit=1)[0])
    return names


def _installed_version(dist: str) -> str:
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return "not installed"


def environment_summary() -> pd.DataFrame:
    """Item and value rows: interpreter, platform, dependency versions, git state and package version."""
    rows: list[tuple[str, str]] = [
        ("python version", sys.version.split()[0]),
        ("python executable", sys.executable),
        ("platform", platform.platform()),
    ]
    for dep in _dependency_names():
        rows.append((f"package {dep}", _installed_version(dep)))
    for dep in NOTEBOOK_EXTRAS:
        rows.append((f"package {dep} (notebook extra)", _installed_version(dep)))
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    commit = _git("rev-parse", "--short", "HEAD")
    tracked_changes = _git("status", "--porcelain", "--untracked-files=no")
    rows.append(("git branch", branch or "unavailable"))
    rows.append(("git commit", commit or "unavailable"))
    if tracked_changes is None:
        rows.append(("working tree dirty (tracked files)", "unknown"))
    else:
        n = len([ln for ln in tracked_changes.splitlines() if ln.strip()])
        rows.append(("working tree dirty (tracked files)", "yes" if n else "no"))
        rows.append(("tracked files with changes", str(n)))
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    rows.append(("kambale package version (pyproject.toml)", pyproject["project"]["version"]))
    from kambale.config import ETL_VERSION
    rows.append(("kambale ETL_VERSION (kambale.config)", ETL_VERSION))
    return pd.DataFrame(rows, columns=["item", "value"])


def _config_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and data.get("config_version"):
            return str(data["config_version"]).strip()
    except yaml.YAMLError:
        pass
    # The O2 structural configuration has prose lines that PyYAML rejects; the version line is still plain text.
    match = re.search(r"^config_version:\s*(\S+)", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _first_commit(relpath: str) -> tuple[str, str]:
    out = _git("log", "--diff-filter=A", "--format=%h|%cI", "--", relpath)
    if not out:
        return "NOT_COMMITTED", ""
    first = out.splitlines()[-1]  # git log lists newest first; the last line is the commit that first added the file
    commit, date = first.split("|", 1)
    return commit, date


def config_receipts() -> pd.DataFrame:
    """One row per live configuration file: version, current SHA-256 and the commit that first added it."""
    rows = []
    for key, files in CONFIG_FILES.items():
        for path in files:
            relpath = path.relative_to(PROJECT_ROOT).as_posix()
            commit, date = _first_commit(relpath)
            rows.append({
                "objective": OBJECTIVE_LABELS[key],
                "file": relpath,
                "config_version": _config_version(path),
                "sha256": sha256_file(path),
                "first_commit": commit,
                "first_commit_date": date,
            })
    return pd.DataFrame(rows, columns=["objective", "file", "config_version", "sha256", "first_commit",
                                       "first_commit_date"])


def _parse_manifest(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # Manifest rows: | File | Role | Bytes | SHA-256 |
        if len(cells) != 4 or not cells[0].endswith(".sqlite") and ".sqlite." not in cells[0]:
            continue
        try:
            size = int(cells[2])
        except ValueError:
            continue
        rows.append({"file": cells[0], "role": cells[1], "bytes": size, "sha256": cells[3]})
    return rows


def database_manifest_check() -> pd.DataFrame:
    """Compare database/MANIFEST.md with the current database files.

    CHANGED_SINCE_MANIFEST is expected for databases that a later run rewrote: the manifest was written at one point in
    time and records what the files were then. It is informational, not an error.
    """
    manifest = _parse_manifest(MANIFEST_PATH.read_text(encoding="utf-8"))
    db_dir = MANIFEST_PATH.parent
    rows = []
    for item in manifest:
        path = db_dir / item["file"]
        if not path.exists():
            status, current_sha, current_bytes = "MISSING", "", None
        else:
            current_sha = sha256_file(path)
            current_bytes = path.stat().st_size
            status = "MATCH" if current_sha == item["sha256"] else "CHANGED_SINCE_MANIFEST"
        note = ""
        if status == "CHANGED_SINCE_MANIFEST":
            note = ("Expected: the manifest was recorded earlier (2026-11-06); later verify or import runs rewrote "
                    "this database. Informational only.")
        elif status == "MISSING":
            note = "Listed in the manifest but not present on disk."
        rows.append({"file": item["file"], "role": item["role"], "manifest_bytes": item["bytes"],
                     "current_bytes": current_bytes, "manifest_sha256": item["sha256"],
                     "current_sha256": current_sha, "status": status, "note": note})
    return pd.DataFrame(rows, columns=["file", "role", "manifest_bytes", "current_bytes", "manifest_sha256",
                                       "current_sha256", "status", "note"])
