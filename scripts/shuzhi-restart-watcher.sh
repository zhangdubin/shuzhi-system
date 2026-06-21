#!/bin/bash
CONTAINER="shuzhi-backend"
TRIGGER="/tmp/shuzhi-backend-restart.trigger"
COOLDOWN=10
last_restart=0
hb=0

log() { echo "[$(date '+%F %T')] $*"; }

# PATH 兜底（launchd 启动时 PATH 很短）
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

log "watcher 启动 PID=$$, PATH=$PATH"

while true; do
  hb=$((hb + 1))
  if [ $((hb % 5)) -eq 0 ]; then
    log "heartbeat (still alive, seen $hb cycles)"
  fi
  if docker exec "$CONTAINER" test -f "$TRIGGER" 2>/dev/null; then
    now=$(date +%s)
    if [ $((now - last_restart)) -lt $COOLDOWN ]; then
      log "冷却中，跳过"
    else
      log "检测到 ${TRIGGER}，重启 ${CONTAINER}"
      docker exec "$CONTAINER" rm -f "$TRIGGER" 2>/dev/null
      if docker restart "$CONTAINER" 2>&1; then
        log "重启完成"
      else
        log "重启失败（rc=$?）"
      fi
      last_restart=$now
    fi
  fi
  sleep 1
done
