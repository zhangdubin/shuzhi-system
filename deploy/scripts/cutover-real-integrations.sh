#!/bin/bash
# ============================================================
# R13 真实集成切真 SOP 脚本（一键上线全流程演练）
# 用法: ./cutover-real-integrations.sh [ocr|nuonuo|wechat-work|all] [--dry-run] [--skip-e2e] [--no-restart]
#
# 特性:
#   --dry-run    只生成 .env.real，不重启、不跑 E2E（演练用）
#   --skip-e2e   跳过 E2E 验证
#   --no-restart 不自动重启 backend（只生成 env）
#
# 流程:
#   1. 备份现有 env → .env.precutover.<ts>
#   2. 收集凭证（缺则报错并打印需要的环境变量）
#   3. 写 .env.real
#   4. pre-flight：探活目标服务 / 写可达性报告
#   5. 重启 backend
#   6. 验证 /health 集成状态
#   7. 跑对应 E2E
#   8. 打印后续 prom 告警 / 监控命令
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/deploy/docker-compose.integration.yml"
ENV_BACKEND_DIR="$PROJECT_ROOT/backend"
ENV_FILE="$ENV_BACKEND_DIR/.env.real"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$ENV_BACKEND_DIR/.env.precutover.$TIMESTAMP"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }
title() { echo -e "\n${CYAN}${BOLD}=== $1 ===${NC}"; }
ok()    { echo -e "${GREEN}✅ $1${NC}"; }
fail()  { echo -e "${RED}❌ $1${NC}"; }

# ============================================================
# 参数解析
# ============================================================
TARGET="all"
DRY_RUN=false
SKIP_E2E=false
NO_RESTART=false

for arg in "$@"; do
  case "$arg" in
    ocr|nuonuo|wechat-work|all) TARGET="$arg" ;;
    --dry-run) DRY_RUN=true ;;
    --skip-e2e) SKIP_E2E=true ;;
    --no-restart) NO_RESTART=true ;;
    -h|--help)
      cat <<USAGE
用法: $0 [TARGET] [OPTIONS]

TARGET:
  ocr           只切 PaddleOCR
  nuonuo        只切诺诺
  wechat-work   只切企业微信
  all           全切（默认）

OPTIONS:
  --dry-run     只生成 env，不重启 / 不跑 E2E（演练）
  --skip-e2e    跳过 E2E 验证
  --no-restart  不自动重启 backend

前置（环境变量）:
  OCR:               SHUZHI_OCR_SERVICE_URL_REAL（可选，默认 http://shuzhi-ocr-service:8001）
  诺诺:              SHUZHI_NUONUO_API_KEY / SHUZHI_NUONUO_API_SECRET [/ SHUZHI_NUONUO_API_TOKEN]
  企业微信:          SHUZHI_WECHAT_WORK_CORP_ID / SHUZHI_WECHAT_WORK_CORP_SECRET
                     SHUZHI_WECHAT_WORK_AGENT_ID / SHUZHI_WECHAT_WORK_REDIRECT_URI
USAGE
      exit 0 ;;
    *) err "未知参数: $arg"; exit 1 ;;
  esac
done

title "R13 真实集成切真 SOP 启动"
info "目标: $TARGET"
info "项目: $PROJECT_ROOT"
[ "$DRY_RUN" = true ] && warn "模式: DRY-RUN（只生成 env，不重启）" || info "模式: LIVE"
[ "$SKIP_E2E" = true ] && warn "跳过 E2E"
[ "$NO_RESTART" = true ] && warn "不自动重启 backend"

# ============================================================
# 前置检查
# ============================================================
title "前置检查"

if [ ! -f "$COMPOSE_FILE" ]; then
  err "docker-compose 文件不存在: $COMPOSE_FILE"
  exit 1
fi
ok "compose 文件存在"

if ! command -v docker &> /dev/null; then
  err "docker 未安装"
  exit 1
fi
ok "docker 可用"

if ! command -v curl &> /dev/null; then
  err "curl 未安装"
  exit 1
fi
ok "curl 可用"

# ============================================================
# 备份现有 env（如果有）
# ============================================================
if [ -f "$ENV_FILE" ]; then
  cp "$ENV_FILE" "$BACKUP_FILE"
  ok "已备份现有 $ENV_FILE → $BACKUP_FILE"
else
  warn "未发现现有 $ENV_FILE，首次切真"
fi

# ============================================================
# OCR 切真
# ============================================================
run_ocr() {
  title "[1/3] PaddleOCR 切真"

  OCR_URL="${SHUZHI_OCR_SERVICE_URL_REAL:-http://shuzhi-ocr-service:8001}"
  info "OCR_SERVICE_URL = $OCR_URL"

  # pre-flight 探活
  info "pre-flight: 探活 OCR 服务..."
  if curl -sf --max-time 5 "$OCR_URL/health" > /tmp/ocr_health.json 2>&1; then
    OCR_HEALTH=$(cat /tmp/ocr_health.json)
    ok "OCR 服务可达: $OCR_HEALTH"
  else
    warn "OCR 服务不可达: $OCR_URL"
    warn "  切真后会回退 mock（业务不停）"
  fi

  cat > "$ENV_FILE" <<EOF
# R13 切真 - PaddleOCR 真实模式
# 生成时间: $(date -Iseconds)
SHUZHI_OCR_MODE=real
SHUZHI_OCR_SERVICE_URL=$OCR_URL
EOF
  ok "已写入 OCR 配置"
}

# ============================================================
# 诺诺切真
# ============================================================
run_nuonuo() {
  title "[2/3] 诺诺发票云切真"

  if [ -z "$SHUZHI_NUONUO_API_KEY" ] || [ -z "$SHUZHI_NUONUO_API_SECRET" ]; then
    err "缺少诺诺凭证！需设置:"
    err "  export SHUZHI_NUONUO_API_KEY=your_app_key"
    err "  export SHUZHI_NUONUO_API_SECRET=your_app_secret"
    err "  export SHUZHI_NUONUO_API_TOKEN=your_access_token (可选)"
    exit 1
  fi
  ok "凭证已就绪 (KEY=${SHUZHI_NUONUO_API_KEY:0:6}***)"

  NUONUO_USE_SANDBOX="${SHUZHI_NUONUO_USE_SANDBOX:-true}"
  if [ "$NUONUO_USE_SANDBOX" = "true" ]; then
    NUONUO_API_URL="https://sandbox.nuonuocs.cn/open/v1/services"
    info "环境: 沙箱 (sandbox.nuonuocs.cn)"
  else
    NUONUO_API_URL="https://sdk.nuonuo.com/open/v1/services"
    warn "环境: 生产 (sdk.nuonuo.com)"
  fi

  # pre-flight 探活
  info "pre-flight: 探活诺诺 ${NUONUO_USE_SANDBOX} 环境..."
  if curl -sf --max-time 5 -o /dev/null "$NUONUO_API_URL" 2>&1; then
    ok "诺诺 API 端点可达"
  else
    warn "诺诺 API 端点不可达（DNS/网络问题）"
    warn "  切真后会回退 mock，业务不停"
  fi

  cat >> "$ENV_FILE" <<EOF

# 诺诺真实模式
SHUZHI_NUONUO_MODE=real
SHUZHI_NUONUO_API_KEY=$SHUZHI_NUONUO_API_KEY
SHUZHI_NUONUO_API_SECRET=$SHUZHI_NUONUO_API_SECRET
SHUZHI_NUONUO_API_TOKEN=${SHUZHI_NUONUO_API_TOKEN:-}
SHUZHI_NUONUO_USE_SANDBOX=$NUONUO_USE_SANDBOX
SHUZHI_NUONUO_API_URL=$NUONUO_API_URL
EOF
  ok "已写入诺诺配置"
}

# ============================================================
# 企业微信切真
# ============================================================
run_wechat_work() {
  title "[3/3] 企业微信 SSO 切真"

  if [ -z "$SHUZHI_WECHAT_WORK_CORP_ID" ] || [ -z "$SHUZHI_WECHAT_WORK_CORP_SECRET" ]; then
    err "缺少企业微信凭证！需设置:"
    err "  export SHUZHI_WECHAT_WORK_CORP_ID=ww..."
    err "  export SHUZHI_WECHAT_WORK_CORP_SECRET=..."
    err "  export SHUZHI_WECHAT_WORK_AGENT_ID=1000002"
    err "  export SHUZHI_WECHAT_WORK_REDIRECT_URI=https://yourdomain.com/..."
    exit 1
  fi
  if [ -z "$SHUZHI_WECHAT_WORK_REDIRECT_URI" ]; then
    err "必须设置 SHUZHI_WECHAT_WORK_REDIRECT_URI（公网 HTTPS 回调地址）"
    exit 1
  fi
  ok "凭证已就绪"
  ok "回调地址: $SHUZHI_WECHAT_WORK_REDIRECT_URI"

  # 警告：必须配置 OAuth 回调域
  warn "切真前必须:"
  warn "  1. 企业微信管理后台 → 自建应用 → 设置 → OAuth 授权回调域 = REDIRECT_URI 的域名"
  warn "  2. 公网域名 + SSL 证书 + DNS 解析"
  warn "  3. 后端部署到公网可访问的服务器"
  warn "  4. 前端部署到公网"

  # pre-flight 探活（access_token 接口）
  info "pre-flight: 探活企业微信 access_token 接口..."
  WW_TOKEN_URL="https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=$SHUZHI_WECHAT_WORK_CORP_ID&corpsecret=$SHUZHI_WECHAT_WORK_CORP_SECRET"
  WW_RESP=$(curl -s --max-time 5 "$WW_TOKEN_URL" 2>&1)
  if echo "$WW_RESP" | grep -q '"errcode":0'; then
    ok "企业微信 API 可达且凭证正确"
  else
    warn "企业微信 API 调用失败（凭证可能错 / 域名未配）"
    warn "  响应: $(echo $WW_RESP | head -c 200)"
    warn "  切真后用户扫码会失败，业务可切回 mock"
  fi

  cat >> "$ENV_FILE" <<EOF

# 企业微信 SSO 真实模式
SHUZHI_WECHAT_WORK_MODE=real
SHUZHI_WECHAT_WORK_CORP_ID=$SHUZHI_WECHAT_WORK_CORP_ID
SHUZHI_WECHAT_WORK_CORP_SECRET=$SHUZHI_WECHAT_WORK_CORP_SECRET
SHUZHI_WECHAT_WORK_AGENT_ID=$SHUZHI_WECHAT_WORK_AGENT_ID
SHUZHI_WECHAT_WORK_REDIRECT_URI=$SHUZHI_WECHAT_WORK_REDIRECT_URI
EOF
  ok "已写入企业微信配置"
}

# ============================================================
# 执行
# ============================================================
> "$ENV_FILE"  # 清空
case "$TARGET" in
  ocr)        run_ocr ;;
  nuonuo)     run_nuonuo ;;
  wechat-work) run_wechat_work ;;
  all)
    run_ocr
    run_nuonuo
    run_wechat_work
    ;;
esac

# ============================================================
# 打印 .env.real
# ============================================================
title "生成 $ENV_FILE"
cat "$ENV_FILE"
echo ""

# ============================================================
# DRY-RUN 提前退出
# ============================================================
if [ "$DRY_RUN" = true ]; then
  warn "DRY-RUN 模式：不重启 / 不跑 E2E"
  warn "下一步: 确认 env 内容后，移除 --dry-run 重跑"
  exit 0
fi

# ============================================================
# 重启 backend（注入 env）
# ============================================================
if [ "$NO_RESTART" = true ]; then
  warn "NO-RESTART 模式：跳过重启"
  warn "请手动执行: docker restart shuzhi-backend"
  exit 0
fi

title "重启 shuzhi-backend"
# 注入 env（从 .env.real 加载）
set -a
. "$ENV_FILE"
set +a

# 重建 backend 时把 env 注入（通过 docker run 临时注入最稳）
info "停掉旧 backend..."
docker stop shuzhi-backend 2>/dev/null || true
docker rm shuzhi-backend 2>/dev/null || true

info "启动新 backend（带 env）..."
DOCKER_ENV_ARGS=""
while IFS='=' read -r key val; do
  [[ -z "$key" || "$key" =~ ^# ]] && continue
  DOCKER_ENV_ARGS="$DOCKER_ENV_ARGS -e $key=$val"
done < "$ENV_FILE"

# 保留其他必要 env（DB / Redis / JWT）
DOCKER_RUN_CMD="docker run -d --name shuzhi-backend \
  -p 8000:8000 \
  --network deploy_shuzhi-net \
  --restart unless-stopped \
  $DOCKER_ENV_ARGS \
  -e SHUZHI_DATABASE_URL=postgresql+asyncpg://shuzhi:shuzhi@shuzhi-postgres:5432/shuzhi \
  -e SHUZHI_REDIS_URL=redis://shuzhi-redis:6379/0 \
  -e SHUZHI_JWT_SECRET_KEY=integration-test-secret-key-very-long-64-chars-aaaaaaaaaa \
  shuzhi-backend:latest"

info "执行: $DOCKER_RUN_CMD"
eval "$DOCKER_RUN_CMD" > /tmp/backend_container_id 2>&1
BACKEND_CID=$(cat /tmp/backend_container_id)
info "新 container: $BACKEND_CID"

info "等待 backend 就绪（worker 启动）..."
sleep 8

# ============================================================
# 验证 /health
# ============================================================
title "验证 /health"
HEALTH=$(curl -s --max-time 5 http://localhost:8000/health || echo "{}")
echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"

# 解析 integrations
INTEGRATIONS=$(echo "$HEALTH" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for k, v in d.get('integrations', {}).items():
        status = v.get('status', '?')
        mode = v.get('mode', '?')
        print(f'{k:20s} status={status:6s} mode={mode}')
except Exception as e:
    print(f'PARSE_ERROR: {e}')
" 2>&1)
echo ""
info "集成状态:"
echo "$INTEGRATIONS"

# ============================================================
# 跑 E2E
# ============================================================
if [ "$SKIP_E2E" = true ]; then
  warn "跳过 E2E（--skip-e2e）"
else
  title "跑 E2E 验证"

  E2E_DIR="$PROJECT_ROOT/e2e"
  if [ ! -d "$E2E_DIR" ]; then
    warn "e2e 目录不存在: $E2E_DIR"
  else
    cd "$E2E_DIR"
    if [[ "$TARGET" == "ocr" || "$TARGET" == "all" ]]; then
      info "test-08-paddleocr-real.js"
      node test-08-paddleocr-real.js 2>&1 | tail -15 || warn "test-08 失败"
    fi
    if [[ "$TARGET" == "nuonuo" || "$TARGET" == "all" ]]; then
      info "test-09-nuonuo-verify.js"
      node test-09-nuonuo-verify.js 2>&1 | tail -15 || warn "test-09 失败"
    fi
    if [[ "$TARGET" == "wechat-work" || "$TARGET" == "all" ]]; then
      info "test-10-wechat-work-sso.js"
      node test-10-wechat-work-sso.js 2>&1 | tail -15 || warn "test-10 失败"
    fi
  fi
fi

# ============================================================
# 完成 + 后续指引
# ============================================================
title "R13 切真完成 🎉"

echo ""
info "后续监控命令:"
echo "  curl -s http://localhost:8000/metrics | grep business_ocr_total"
echo "  curl -s http://localhost:8000/metrics | grep business_verify_total"
echo "  docker logs shuzhi-backend --tail 50 | grep -E 'real|mock|fallback'"
echo ""
info "回滚命令（如需）:"
echo "  cp $BACKUP_FILE $ENV_FILE && docker restart shuzhi-backend"
echo ""
info "备份保留: $BACKUP_FILE"
ok "全部完成！"
