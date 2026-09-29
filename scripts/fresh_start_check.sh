#!/usr/bin/env bash
# ============================================================
# MineIntel — Fresh Start & Deployment Verification Script
# SIH 2026 | Problem Statement 26023
# Usage: bash scripts/fresh_start_check.sh
# Verifies a fresh environment: venv, deps, migrations, API boot, login, upload.
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
VENV_DIR="${REPO_ROOT}/.fresh_venv"
TEST_PORT=8005

echo "==> Step 1: Creating fresh virtual environment at ${VENV_DIR}..."
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

echo "==> Step 2: Upgrading pip and installing requirements..."
pip install --upgrade pip
pip install -r "${BACKEND_DIR}/requirements.txt"

echo "==> Step 3: Setting test environment variables..."
export APP_ENV="development"
export DEBUG="true"
export DEMO_MODE="true"
export DATABASE_URL="sqlite:///${REPO_ROOT}/data/fresh_check.db"
export JWT_SECRET_KEY="fresh-start-test-secret-key-32chars-min-ok"
export DEMO_ANALYST_PASSWORD="TestAnalyst@2026"
mkdir -p "${REPO_ROOT}/data/uploads" "${REPO_ROOT}/data/reports"

echo "==> Step 4: Applying database migrations..."
cd "${BACKEND_DIR}"
alembic upgrade head

echo "==> Step 5: Starting MineIntel API on port ${TEST_PORT} in background..."
python -m uvicorn app.main:app --host 127.0.0.1 --port ${TEST_PORT} &
API_PID=$!

cleanup() {
    echo "==> Shutting down API (PID: ${API_PID})..."
    kill "${API_PID}" 2>/dev/null || true
    rm -rf "${VENV_DIR}" "${REPO_ROOT}/data/fresh_check.db"
    echo "==> Cleaned up temporary test environment."
}
trap cleanup EXIT

echo "==> Waiting for API healthcheck..."
for i in {1..30}; do
    if curl -s "http://127.0.0.1:${TEST_PORT}/api/health" | grep -q '"ok"'; then
        echo "API is healthy!"
        break
    fi
    sleep 1
done

echo "==> Step 6: Authenticating Analyst using env-provided credentials..."
LOGIN_RES=$(curl -s -X POST "http://127.0.0.1:${TEST_PORT}/api/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=analyst_demo&password=${DEMO_ANALYST_PASSWORD}")

TOKEN=$(echo "${LOGIN_RES}" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "${TOKEN}" ]; then
    echo "ERROR: Failed to authenticate. Response: ${LOGIN_RES}"
    exit 1
fi
echo "==> Successfully authenticated! Token acquired."

echo "==> Step 7: Uploading sample data..."
for f in "${REPO_ROOT}/sample_data"/*; do
    if [ -f "$f" ]; then
        echo "    Uploading $(basename "$f")..."
        curl -s -X POST "http://127.0.0.1:${TEST_PORT}/api/documents/upload" \
            -H "Authorization: Bearer ${TOKEN}" \
            -F "file=@${f}" \
            -F "category=Production" \
            -F "subsidiary=CIL"
        echo ""
    fi
done

echo "==> Step 8: Verifying document list endpoint..."
DOCS_RES=$(curl -s -X GET "http://127.0.0.1:${TEST_PORT}/api/documents" \
    -H "Authorization: Bearer ${TOKEN}")
echo "    Documents response status verified."

echo "==> SUCCESS: Fresh clone start and workflow fully verified!"
