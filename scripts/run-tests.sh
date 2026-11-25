#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE_FILE="compose.test.yaml"
TEST_URL="http://127.0.0.1:18000"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

ARTIFACT_DIR="$PROJECT_DIR/artifacts/test-runs"
TEST_LOG="$ARTIFACT_DIR/tests-$TIMESTAMP.log"
CONTAINER_LOG="$ARTIFACT_DIR/container-$TIMESTAMP.log"

mkdir -p "$ARTIFACT_DIR"

echo "=================================================="
echo " ShopSphere Automated Test Runner"
echo "=================================================="
echo "Project: $PROJECT_DIR"
echo "Started: $(date --iso-8601=seconds)"
echo

cleanup() {
    local exit_code=$?

    trap - EXIT
    set +e

    echo
    echo "========== COLLECT TEST CONTAINER LOGS =========="

    sudo docker compose -f "$COMPOSE_FILE" logs \
        --no-color > "$CONTAINER_LOG" 2>&1

    sudo docker compose -f "$COMPOSE_FILE" logs --tail 30

    echo
    echo "========== CLEAN UP TEST ENVIRONMENT =========="

    sudo docker compose -f "$COMPOSE_FILE" down --remove-orphans

    echo
    echo "========== TEST ARTIFACTS =========="
    echo "Test output:     $TEST_LOG"
    echo "Container logs:  $CONTAINER_LOG"

    echo
    if [ "$exit_code" -eq 0 ]; then
        echo "RESULT: ALL TESTS PASSED"
    else
        echo "RESULT: TEST RUN FAILED (exit code: $exit_code)"
    fi

    exit "$exit_code"
}

trap cleanup EXIT

echo "========== VALIDATE COMPOSE CONFIGURATION =========="
sudo docker compose -f "$COMPOSE_FILE" config -q

echo
echo "========== BUILD AND START ISOLATED TEST API =========="
sudo docker compose -f "$COMPOSE_FILE" up -d --build

echo
echo "========== WAIT FOR API READINESS =========="

ready=0

for attempt in $(seq 1 30); do
    if curl -fsS "$TEST_URL/health" -o /dev/null; then
        ready=1
        echo "Test API is healthy."
        break
    fi

    echo "Waiting for API startup ($attempt/30)..."
    sleep 2
done

if [ "$ready" -ne 1 ]; then
    echo "ERROR: Test API did not become healthy."
    exit 1
fi

echo
echo "========== RUN API TESTS =========="

SHOPSPHERE_TEST_URL="$TEST_URL" \
    python3 -m unittest discover \
        -s tests \
        -p 'test_*.py' \
        -v 2>&1 | tee "$TEST_LOG"

echo
echo "========== TEST EXECUTION COMPLETED =========="
