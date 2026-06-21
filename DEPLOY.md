# 数智化管理系统 · 生产部署指南

> 适用：自用企业系统，6 容器（postgres / redis / backend / frontend / fake-ocr / fake-nuonuo）
> 当前状态：v1.0.0-RC4，可演示 / 可内部试用

## 0. 环境要求

| 组件 | 最低 | 推荐 |
|---|---|---|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 硬盘 | 20 GB SSD | 50 GB SSD |
| OS | Linux (Ubuntu 22.04 / macOS) | Linux |
| Docker | 24+ | 26+ |
| 域名 | — | shuzhi.your-domain.com |
| SSL | — | Let's Encrypt / 公司 CA |

## 1. 快速启动（开发 / 演示）

```bash
# 1. 拉 / 拷贝代码
cd /path/to/shuzhi-system

# 2. 启动 6 容器
cd deploy
docker compose up -d

# 3. 初始化数据库（首次）
docker exec shuzhi-postgres psql -U shuzhi -d shuzhi -f /docker-entrypoint-initdb.d/01_init.sql
docker exec shuzhi-backend python -m app.scripts.seed_admin

# 4. 打开浏览器
open http://localhost
# 默认账号：admin / admin123
```

## 2. 生产部署

### 2.1 域名 + HTTPS

```bash
# 1. 申请域名（example.com / your-domain.com）

# 2. 安装 certbot
apt install certbot python3-certbot-nginx

# 3. 申请证书
certbot certonly --standalone -d shuzhi.your-domain.com

# 4. 在 deploy/frontend/ 加一层 nginx（替换容器 nginx）
# 或者直接挂证书到 frontend 容器

# 5. 改 docker-compose.yml：
#    ports: ["443:80"] + volumes 挂证书
```

**生产 nginx 配置**（示例）：

```nginx
server {
    listen 443 ssl;
    server_name shuzhi.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/shuzhi.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/shuzhi.your-domain.com/privkey.pem;

    # 强制 HTTPS
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;

    # 后端 API
    location /api/ {
        proxy_pass http://shuzhi-backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90s;
        proxy_buffering off;
    }

    # SSE 实时通道
    location /sse/ {
        proxy_pass http://shuzhi-backend:8000;
        proxy_set_header Host $host;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;  # 长连接
    }

    # 前端 SPA
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
}
```

### 2.2 环境变量

**生产** `.env` 模板（**不要提交 git**）：

```bash
# 必改
JWT_SECRET_KEY=$(openssl rand -hex 32)        # 强随机
POSTGRES_PASSWORD=$(openssl rand -hex 16)
SHUZHI_ENV=production
SHUZHI_LOG_LEVEL=INFO

# OCR（生产用真实）
SHUZHI_OCR_MODE=nuonuo                            # mock / nuonuo / paddle
NUONUO_API_KEY=<your-nuonuo-key>
NUONUO_API_SECRET=<your-nuonuo-secret>

# SSE / Redis（生产集群）
REDIS_URL=redis://redis:6379/0

# SSO（可选）
WECOM_CORP_ID=<your-corp-id>
WECOM_AGENT_ID=<your-agent-id>
WECOM_SECRET=<your-secret>
DINGTALK_APP_KEY=<your-app-key>
DINGTALK_APP_SECRET=<your-app-secret>

# Sentry 监控
SENTRY_DSN=<your-sentry-dsn>

# 日志
LOG_PATH=/var/log/shuzhi/
```

### 2.3 Docker Compose 优化

**生产 compose 关键差异**：

```yaml
services:
  backend:
    # 4 worker 改成生产配置
    command: gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 90
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./backups:/backups  # 备份目录
    # 改 16GB shared_buffers / 4GB work_mem
    command: postgres -c shared_buffers=256MB -c max_connections=100

  redis:
    # 加密码 + appendonly 持久化
    command: redis-server --appendonly yes --requirepass $REDIS_PASSWORD
```

### 2.4 数据备份

**Postgres 每日自动备份**：

```bash
# /etc/cron.daily/shuzhi-backup
docker exec shuzhi-postgres pg_dump -U shuzhi shuzhi | gzip > /backups/shuzhi-$(date +%Y%m%d).sql.gz
find /backups -name "shuzhi-*.sql.gz" -mtime +30 -delete  # 保留 30 天
```

**Redis AOF 持久化**（默认开）+ 每小时 BGSAVE。

### 2.5 监控告警

**推荐接入**：
- **Sentry**（错误监控）—— `SENTRY_DSN` 已留 env
- **Prometheus + Grafana**（指标监控）—— 加 `/metrics` 端点
- **UptimeRobot**（HTTP 健康检查）—— 监控 `/health` 端点
- **企业微信机器人**（告警）—— 异常时推送

**最小监控指标**：
- backend 4 worker 都在线
- postgres 连接数 < 80
- redis 内存 < 500MB
- API p95 < 500ms
- SSE 长连接数

### 2.6 扩容

**水平扩展**：
- backend 4 → 8 worker（加 `deploy.replicas`）
- postgres 读多写少时，加只读副本
- redis 集群（≥3 节点）

**垂直扩展**：
- 单机 8GB → 16GB 内存
- 4 worker → 8 worker

## 3. 日常运维

### 3.1 查看日志

```bash
# 实时所有容器
cd /path/to/shuzhi/deploy
docker compose logs -f

# 只看 backend
docker logs -f shuzhi-backend --tail 100

# 错误日志
docker logs shuzhi-backend 2>&1 | grep -i error

# 慢请求
docker logs shuzhi-backend 2>&1 | grep "SLOW"
```

### 3.2 重启服务

```bash
# 单个容器
docker restart shuzhi-backend

# 全部
docker compose restart
```

### 3.3 数据库迁移

```bash
# 1. 进入 backend 容器
docker exec -it shuzhi-backend bash

# 2. 跑 alembic
alembic upgrade head
alembic revision --autogenerate -m "新增字段 xxx"
```

### 3.4 清理磁盘

```bash
# Docker 无用镜像
docker image prune -af

# 日志清理（容器内）
docker exec shuzhi-backend sh -c "find /tmp -name '*.log' -mtime +7 -delete"

# 旧备份
find /backups -mtime +30 -delete
```

## 4. 升级流程

```bash
# 1. 备份
./scripts/backup.sh

# 2. 拉新代码
git pull

# 3. 重新构建 + 重启
cd deploy
docker compose build
docker compose up -d

# 4. 跑迁移
docker exec shuzhi-backend alembic upgrade head

# 5. 验证
curl http://localhost/health
./e2e/run-all.js
```

## 5. 故障排查

### 5.1 后端 502 Bad Gateway
- 看 nginx 配置 / `docker logs shuzhi-frontend`
- 看 backend 是否 healthy：`docker ps`

### 5.2 登录 401 / Token 失效
- 清除浏览器 localStorage
- 检查 `JWT_SECRET_KEY` 是否一致

### 5.3 SSE 收不到推送
- 看后端 `/api/v1/cron/jobs` 确认 scheduler 运行
- 看 redis pub/sub: `docker exec shuzhi-redis redis-cli SUBSCRIBE sse:dashboard`
- 看浏览器 network: `GET /sse/dashboard?token=...` 应为 200

### 5.4 dashboard 加载慢
- 看慢请求日志: `docker logs shuzhi-backend | grep SLOW`
- 看 postgres 慢查询: `SELECT * FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10`
- 看 redis 缓存命中率: `docker exec shuzhi-redis redis-cli INFO stats`

## 6. 安全 checklist

- [ ] `JWT_SECRET_KEY` 改强随机（32+ 字符）
- [ ] `POSTGRES_PASSWORD` 改强随机
- [ ] Redis 启用 `requirepass`
- [ ] 启用 HTTPS（certbot + 301 redirect）
- [ ] CORS 限制具体域名（不要 `*`）
- [ ] audit log 保留 ≥ 180 天
- [ ] 定期备份 + 异地存储
- [ ] 防火墙只开 80/443 + SSH
- [ ] 敏感字段脱敏（已完成）
- [ ] 权限拦截（已完成）

---

**Generated by Mavis | 2026-06-14**
