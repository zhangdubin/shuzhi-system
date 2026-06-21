# ============================================================
# 前端 - 多阶段构建（Node 20 + nginx alpine）
# context: ..（项目根，即 deploy/ 的上级目录）
# ============================================================
FROM node:20-alpine AS builder
WORKDIR /build

# 依赖
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --silent || npm install --silent

# 源码
COPY frontend/ ./

# 构建
RUN npm run build

# ============================================================
# 运行 - nginx:alpine
# ============================================================
FROM nginx:alpine AS runtime
RUN rm /etc/nginx/conf.d/default.conf

# nginx 配置（context 是项目根）
COPY deploy/frontend/nginx.conf /etc/nginx/conf.d/

# 构建产物
COPY --from=builder /build/dist /usr/share/nginx/html

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:80/health || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
