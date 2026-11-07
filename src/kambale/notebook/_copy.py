"""Copying the repository for a rerun, and running a command inside the copy.

A copy is what gates and reproduce run in, so the real databases and outputs are never written. The copy is run with
PYTHONPATH pointing at its own src folder; kambale.config derives PROJECT_ROOT from its own location, so every path
then resolves inside the copy.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

from kambale.config import PROJECT_ROOT

EXCLUDED_NAMES = {".git", "__pycache__", ".pytest_cache", "graphify-out"}


def is_excluded(rel_path: str) -> bool:
    """True when a path relative to the repository root must not be copied.

    Excluded: any .git, __pycache__, .pytest_cache or graphify-out entry at any depth; everything under
    notebooks/output; and PDF or ZIP files at the repository root (reference papers and the supplementary archive).
    """
    parts = PurePosixPath(str(rel_path).replace("\\", "/")).parts
    if not parts:
        return False
    if any(part in EXCLUDED_NAMES for part in parts):
        return True
    if len(parts) >= 2 and parts[0] == "notebooks" and parts[1] == "output":
        return True
    if len(parts) == 1 and parts[0].lower().endswith((".pdf", ".zip")):
        return True
    return False


def copy_repo(dest: Path) -> Path:
    """Copy the repository into dest, which is created when missing and must be empty when present."""
    dest = Path(dest).resolve()
    if dest == PROJECT_ROOT or PROJECT_ROOT in dest.parents:
        raise ValueError(f"copy destination {dest} must not be inside the repository {PROJECT_ROOT}")
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"copy destination {dest} is not empty")
    dest.mkdir(parents=True, exist_ok=True)

    def _ignore(directory, names):
        rel = Path(directory).resolve().relative_to(PROJECT_ROOT)
        return {n for n in names if is_excluded((rel / n).as_posix())}

    shutil.copytree(PROJECT_ROOT, dest, ignore=_ignore, dirs_exist_ok=True)
    return dest


def in_copy(copy_root: Path, real_path: Path) -> Path:
    """Map a path inside the real repository to the same path inside a copy."""
    return Path(copy_root) / Path(real_path).resolve().relative_to(PROJECT_ROOT)


def copy_env(copy_root: Path) -> dict:
    """Environment for a command run in a copy: PYTHONPATH on the copy's src, UTF-8 output, no tier override."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(copy_root) / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.pop("KAMBALE_O4_TIER", None)
    return env


def run_command(args: list[str], cwd: Path, env: dict) -> dict:
    """Run sys.executable with args in cwd. Returns exit_code, seconds, stdout and stderr. Does not raise on exit code."""
    start = time.time()
    proc = subprocess.run([sys.executable, *args], cwd=str(cwd), env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return {"exit_code": proc.returncode, "seconds": round(time.time() - start, 1),
            "stdout": proc.stdout, "stderr": proc.stderr}
