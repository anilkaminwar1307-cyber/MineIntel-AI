#!/usr/bin/env python3
"""
MineIntel - Clean for Submission Script
SIH 2026 | Problem Statement 26023
Cross-platform packager that creates a clean ZIP submission (< 20 MB)
excluding temporary files, node_modules, .git, .env, and caches.
"""
import os
import sys
import zipfile
import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    ".pytest_cache",
    "__pycache__",
    "dist",
    ".vite",
    "backups",
    "_backups",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".db-shm",
    ".db-wal",
}

def should_exclude(rel_path: Path) -> bool:
    parts = rel_path.parts
    # Check directory exclusions
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
        if part.endswith(".egg-info"):
            return True

    # Exclude .env but keep .env.example
    if rel_path.name == ".env":
        return True

    # Exclude uploaded documents and generated reports (PII/live user data)
    str_path = str(rel_path).replace("\\", "/")
    if "data/uploads/" in str_path and not rel_path.name.endswith(".gitkeep"):
        return True
    if "data/reports/" in str_path and not rel_path.name.endswith(".gitkeep"):
        return True

    # Check extension exclusions
    if rel_path.suffix in EXCLUDE_EXTENSIONS:
        return True

    return False

def create_submission_zip():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = REPO_ROOT.parent
    zip_path = output_dir / f"mineintel_submission_{timestamp}.zip"

    print(f"==> Packaging {REPO_ROOT.name} into {zip_path}...")
    total_files = 0

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(REPO_ROOT):
            root_path = Path(root)
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.endswith(".egg-info")]

            for file in files:
                file_path = root_path / file
                rel_path = file_path.relative_to(REPO_ROOT)

                if should_exclude(rel_path):
                    continue

                archive_name = Path(REPO_ROOT.name) / rel_path
                zf.write(file_path, archive_name)
                total_files += 1

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"==> Packed {total_files} files.")
    print(f"==> Final ZIP Size: {size_mb:.2f} MB")
    if size_mb > 20:
        print(f"WARNING: ZIP exceeds 20 MB ({size_mb:.2f} MB). Review included files.")
    else:
        print("==> SUCCESS: Submission ZIP is strictly under 20 MB!")

    return zip_path

if __name__ == "__main__":
    create_submission_zip()
