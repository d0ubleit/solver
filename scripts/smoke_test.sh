#!/usr/bin/env bash
# smoke_test.sh — полный цикл проверки Solver бота
# Запуск: ./scripts/smoke_test.sh
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0

check() {
    local name="$1"
    local result="$2"
    if [ "$result" -eq 0 ]; then
        echo -e "  ${GREEN}✅${NC} $name"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}❌${NC} $name"
        FAIL=$((FAIL + 1))
    fi
}

echo "══════════════════════════════════════════════"
echo "  Solver Smoke Test Suite"
echo "══════════════════════════════════════════════"
echo ""

# ── 1. Python unit + integration tests ──
echo "📦 Unit & Integration Tests"
python -m pytest tests/unit/ tests/integration/ -q 2>&1
check "Unit + Integration (70 tests)" $?
echo ""

# ── 2. E2E tests (FakeBot) ──
echo "📡 E2E Tests (FakeBot)"
python -m pytest tests/e2e/ -q 2>&1
check "E2E (28 tests)" $?
echo ""

# ── 3. Docker build ──
echo "🐳 Docker Build"
docker compose build 2>&1 | tail -3
check "Docker image build" $?
echo ""

# ── 4. Docker up + health check ──
echo "🚀 Starting bot..."
docker compose down 2>/dev/null || true
docker compose up -d 2>&1
sleep 3

if docker compose ps | grep -q "Up"; then
    check "Container is running" 0
else
    check "Container is running" 1
fi

# ── 5. Check logs for errors ──
echo "📋 Log check"
LOGS=$(docker compose logs --tail=20 2>&1)
if echo "$LOGS" | grep -qi "error\|exception\|traceback"; then
    echo "  ⚠️  Errors found in logs:"
    echo "$LOGS" | grep -i "error\|exception\|traceback" | head -5
    check "No errors in logs" 1
else
    check "No errors in logs" 0
fi

# ── 6. Bot is polling ──
if echo "$LOGS" | grep -q "polling"; then
    check "Bot is polling Telegram" 0
else
    check "Bot is polling Telegram" 1
fi

echo ""
echo "══════════════════════════════════════════════"
echo -e "  Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}"
echo "══════════════════════════════════════════════"

# Exit with failure if any test failed
[ "$FAIL" -eq 0 ] || exit 1
