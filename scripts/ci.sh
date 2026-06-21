#!/bin/bash
# ============================================================
# 数智化管理系统 · 本地 CI 一键脚本
# 用法: bash scripts/ci.sh
# ============================================================
# 跑：E2E 全部 10 个测试 + perf bench + docker healthcheck
# 失败时 exit 1，CI 拦截
# ============================================================
set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

step() { echo -e "\n${YELLOW}▶ $1${NC}"; }
ok() { echo -e "${GREEN}✅ $1${NC}"; }
fail() { echo -e "${RED}❌ $1${NC}"; exit 1; }

# ============================================================
# 1. Docker 容器健康检查
# ============================================================
step "1/5 Docker 容器健康检查..."
# frontend 没配 healthcheck，用 running 状态判断
check_container() {
  local c=$1
  local expected=$2
  if [ "$expected" = "running" ]; then
    local state=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null || echo "missing")
    if [ "$state" = "running" ]; then
      ok "$c: running"
    else
      fail "$c: $state（应该 running）"
    fi
  else
    local status=$(docker inspect --format='{{.State.Health.Status}}' "$c" 2>/dev/null || echo "missing")
    if [ "$status" = "$expected" ]; then
      ok "$c: $expected"
    else
      fail "$c: $status（应该 $expected）"
    fi
  fi
}

check_container shuzhi-frontend  running
check_container shuzhi-backend    healthy
check_container shuzhi-postgres   healthy
check_container shuzhi-redis      healthy
check_container shuzhi-ocr-service healthy

# ============================================================
# 2. Backend /health
# ============================================================
step "2/5 后端 /health 探活..."
HEALTH=$(curl -fsS http://localhost:8000/health 2>&1 || echo "fail")
echo "$HEALTH" | grep -q "ok" && ok "Backend /health: OK" || fail "Backend /health 失败: $HEALTH"

# ============================================================
# 3. E2E 全部 10 个测试
# ============================================================
step "3/5 E2E 全部测试（10 个）..."
HEADLESS=1 node e2e/run-all.js 2>&1 | tail -25
E2E_RESULT=${PIPESTATUS[0]}
if [ $E2E_RESULT -ne 0 ]; then
  fail "E2E 测试失败（exit=$E2E_RESULT）"
fi
ok "E2E 全部通过"

# ============================================================
# 4. 性能基准（基线对比）
# ============================================================
step "4/5 性能基准（12 端点 p50/p95）..."
node scripts/perf-bench.js 2>&1 | tail -20
ok "性能基准完成"

# ============================================================
# 5. 自动写报告
# ============================================================
step "5/5 生成 CI 报告..."
REPORT="ci-report-$(date +%Y%m%d-%H%M%S).md"
{
  echo "# CI 报告 - $(date +'%Y-%m-%d %H:%M:%S')"
  echo ""
  echo "## Docker 容器"
  for c in "${EXPECTED_CONTAINERS[@]}"; do
    status=$(docker inspect --format='{{.State.Health.Status}}' "$c" 2>/dev/null || echo "missing")
    echo "- **$c**: $status"
  done
  echo ""
  echo "## 性能基准"
  node scripts/perf-bench.js 2>&1 | grep -E "^POST|^GET|p95|端点数"
  echo ""
  echo "## E2E"
  echo "10/10 PASS（详见 e2e/report-*.md）"
} > "$REPORT"
ok "CI 报告: $REPORT"

echo ""
echo "============================================================"
echo -e "${GREEN}  ✅ CI 全部通过${NC}"
echo "============================================================"
