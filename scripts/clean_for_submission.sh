#!/usr/bin/env bash
# ============================================================
# MineIntel — Clean-for-Submission Script
# SIH 2026 | Problem Statement 26023
# Usage: bash scripts/clean_for_submission.sh
# Creates a ZIP under 20 MB with all sensitive/generated files removed.
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_ZIP="${REPO_ROOT}/../mineintel_submission_${TIMESTAMP}.zip"

echo "==> Cleaning repository for SIH submission..."
echo "    Repo root: ${REPO_ROOT}"

# ── 1. Remove generated / sensitive files from working tree (do NOT git rm) ──
rm -rf \
    "${REPO_ROOT}/frontend/node_modules" \
    "${REPO_ROOT}/frontend/dist" \
    "${REPO_ROOT}/.pytest_cache" \
    "${REPO_ROOT}/backend/.pytest_cache" \
    "${REPO_ROOT}/_backups" \
    "${REPO_ROOT}/backups"

# Databases — never submit live data
find "${REPO_ROOT}" -name "*.db"     -delete 2>/dev/null || true
find "${REPO_ROOT}" -name "*.db-shm" -delete 2>/dev/null || true
find "${REPO_ROOT}" -name "*.db-wal" -delete 2>/dev/null || true

# Uploads and generated reports (user data / PII)
rm -rf \
    "${REPO_ROOT}/backend/data/uploads" \
    "${REPO_ROOT}/backend/data/reports" \
    "${REPO_ROOT}/data/uploads" \
    "${REPO_ROOT}/data/reports"

# Real .env (never expose secrets)
rm -f "${REPO_ROOT}/.env"

# Python caches
find "${REPO_ROOT}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "${REPO_ROOT}" -name "*.pyc"       -delete 2>/dev/null || true

# ── 2. Create ZIP ─────────────────────────────────────────────────────────────
echo "==> Creating ZIP: ${OUTPUT_ZIP}"
cd "${REPO_ROOT}/.."
zip -r "${OUTPUT_ZIP}" "$(basename "${REPO_ROOT}")" \
    --exclude "*.git*" \
    --exclude "*node_modules*" \
    --exclude "*__pycache__*" \
    --exclude "*.pyc" \
    --exclude "*.db" \
    --exclude "*.db-shm" \
    --exclude "*.db-wal" \
    --exclude "*.env" \
    --exclude "*_backups*" \
    --exclude "*backups*"

# ── 3. Check size ─────────────────────────────────────────────────────────────
ZIP_SIZE_MB=$(du -m "${OUTPUT_ZIP}" | cut -f1)
echo "==> ZIP size: ${ZIP_SIZE_MB} MB"
if [ "${ZIP_SIZE_MB}" -gt 20 ]; then
    echo "WARNING: ZIP exceeds 20 MB (${ZIP_SIZE_MB} MB). Review large files."
else
    echo "==> OK — ZIP is within 20 MB limit."
fi

echo "==> Submission package created: ${OUTPUT_ZIP}"
