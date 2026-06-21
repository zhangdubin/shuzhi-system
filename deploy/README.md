# ============================================================
# 部署快速开始
# ============================================================

## 1. 启动整套系统

```bash
# 1. 复制环境变量
cp .env.example .env
vim .env  # 修改 JWT_SECRET_KEY 等敏感信息

# 2. 一键启动
docker compose up -d

# 3. 查看状态
docker compose ps

# 4. 查看日志
docker compose logs -f backend
```

启动后访问：
- 前端：http://localhost
- 后端 API：http://localhost/api/
- Prometheus（监控）：http://localhost:9090 （profile: monitoring）
- Grafana：http://localhost:3000 （profile: monitoring）

## 2. 数据库初始化

```bash
# 进入后端容器
docker compose exec backend bash

# 手动跑迁移
alembic upgrade head

# 初始化种子数据
python scripts/seed.py
```

## 3. 启用监控（可选）

```bash
docker compose --profile monitoring up -d
```

访问：
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000（默认账号 admin / admin）

## 4. 常用命令

```bash
# 查看所有服务
docker compose ps

# 重启某个服务
docker compose restart backend

# 查看资源占用
docker stats

# 进入容器调试
docker compose exec backend bash
docker compose exec postgres psql -U shuzhi shuzhi

# 备份数据库
docker compose exec postgres pg_dump -U shuzhi shuzhi > backup_$(date +%Y%m%d).sql

# 恢复数据库
cat backup_20260612.sql | docker compose exec -T postgres psql -U shuzhi shuzhi
```

## 5. 性能调优

### PostgreSQL
```ini
# postgresql.conf
shared_buffers = 256MB          # 物理内存的 25%
effective_cache_size = 1GB      # 物理内存的 75%
work_mem = 4MB
maintenance_work_mem = 128MB
max_connections = 200
```

### Redis
```conf
maxmemory 1gb
maxmemory-policy allkeys-lru
```

### FastAPI
```bash
# 增加 worker
uvicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
# 或用 gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## 6. HTTPS 配置（生产环境必做）

使用 Let's Encrypt + Certbot：

```bash
# 1. 安装 certbot
apt install certbot python3-certbot-nginx

# 2. 申请证书
certbot --nginx -d shuzhi.example.com

# 3. 自动续期
crontab -e
0 3 * * * certbot renew --quiet
```

## 7. 日志收集

推荐方案：Promtail + Loki + Grafana

或 ELK：

```bash
docker run -d \
  --name elasticsearch \
  -e discovery.type=single-node \
  -e ES_JAVA_OPTS="-Xms512m -Xmx512m" \
  -p 9200:9200 \
  elasticsearch:8.5.0
```

## 8. 升级流程

```bash
# 1. 拉新代码
git pull

# 2. 重新构建镜像
docker compose build --no-cache

# 3. 数据库迁移（如果有 schema 变更）
docker compose exec backend alembic upgrade head

# 4. 滚动重启
docker compose up -d
```

## 9. 故障排查

```bash
# 后端无法连接数据库
docker compose logs backend | grep -i "database"
docker compose exec postgres pg_isready

# OCR 服务慢
docker compose logs ocr-service | tail -50
docker stats ocr-service

# SSE 不工作
# 1. 检查 nginx 配置
docker compose exec frontend cat /etc/nginx/conf.d/default.conf | grep -A5 sse
# 2. 直接测后端 SSE
curl -N http://localhost:8000/sse/invoice/batch/test

# 性能问题
docker stats
# 看 CPU / 内存占用最高的容器
```

## 10. 架构图

```
┌─────────────────────────────────────────┐
│  浏览器 (Chrome/Safari/Edge)             │
└────────────┬────────────────────────────┘
             │ HTTPS
             ↓
┌─────────────────────────────────────────┐
│  Nginx (port 80/443)                     │
│  - 静态文件                               │
│  - /api/* → 后端                          │
│  - /sse/* → 后端（SSE 长连接）            │
└────┬──────────┬──────────┬───────────────┘
     │          │          │
     ↓          ↓          ↓
┌─────────┐ ┌─────────┐ ┌──────────┐
│ Backend │ │  Paddle │ │ Postgres │
│ FastAPI │ │   OCR   │ │   15     │
│  port   │ │  port   │ │  port    │
│  8000   │ │  8001   │ │  5432    │
└────┬────┘ └─────────┘ └──────────┘
     │
     ↓ (异步任务)
┌─────────┐
│ Celery  │ ←──── Redis ────┐
│ Worker  │                  │
└─────────┘                  │
                             ↓
                       ┌──────────┐
                       │  Redis   │
                       │   7      │
                       │  6379    │
                       └──────────┘
```

## 11. 端口清单

| 端口 | 服务 | 用途 |
|------|------|------|
| 80 | Nginx | 前端 / API 入口 |
| 443 | Nginx (HTTPS) | 生产 |
| 5432 | PostgreSQL | 数据库（生产不对外） |
| 6379 | Redis | 缓存（生产不对外） |
| 8000 | FastAPI | 后端 API（生产不对外） |
| 8001 | PaddleOCR | OCR 服务（生产不对外） |
| 9090 | Prometheus | 监控（内网） |
| 3000 | Grafana | 监控（内网） |
