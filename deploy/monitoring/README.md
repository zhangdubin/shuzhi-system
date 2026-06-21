# ============================================================
# 监控使用说明
# ============================================================

## 启用监控

```bash
# 启动监控栈（Prometheus + Grafana + exporters）
docker compose --profile monitoring up -d
```

## 访问

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
  - 默认账号：`admin / admin`（首次登录会要求改密码）
- **Node Exporter**: http://localhost:9100/metrics
- **Postgres Exporter**: http://localhost:9187/metrics
- **Redis Exporter**: http://localhost:9121/metrics

## 导入 Dashboard

1. 登录 Grafana → Dashboards → Import
2. 上传 `grafana-dashboard.json`
3. 选择 Prometheus 数据源
4. 保存

## 告警规则

`alerts.yml` 已包含：
- **后端 API**：宕机、5xx 错误率、P99 延迟、慢请求
- **数据库**：连接数、锁等待、全表扫描、磁盘
- **Redis**：宕机、内存、淘汰
- **主机**：CPU、内存、磁盘
- **OCR**：服务可用性、P95 延迟

告警会推送到 Prometheus Alertmanager，需配 Slack/Email/钉钉 webhook。

## 快速配置告警（钉钉）

```yaml
# alertmanager.yml
route:
  receiver: 'dingtalk'
receivers:
  - name: 'dingtalk'
    webhook_configs:
      - url: 'https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN'
        send_resolved: true
```

## 预置 Metrics（后端）

`/metrics` 端点暴露（用 prometheus-fastapi-instrumentator）：

| 指标 | 含义 |
|------|------|
| `http_requests_total` | 请求总数（按 status/endpoint/method 分） |
| `http_request_duration_seconds` | 请求延迟直方图 |
| `sse_active_connections` | 当前 SSE 连接数 |
| `db_connections_active` | DB 连接池活跃数 |
| `app_info` | 应用版本信息（gauge = 1） |

## 容量参考

| 指标 | 健康 | 警告 | 危险 |
|------|------|------|------|
| CPU | < 60% | 60-80% | > 80% |
| 内存 | < 70% | 70-85% | > 85% |
| 磁盘 | < 60% | 60-80% | > 80% |
| P99 延迟 | < 300ms | 300-1000ms | > 1000ms |
| 5xx 错误率 | < 0.1% | 0.1-1% | > 1% |
| DB 连接 | < 100 | 100-180 | > 180 |
