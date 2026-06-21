# 数智化管理系统

发票识别 / 销售费用 / 项目管理 / 合同 / 客户 / 回款 / AI 智能 — 一体化企业管理系统。

## 技术栈
- 后端：FastAPI + SQLAlchemy + PostgreSQL + Redis
- 前端：Vue 3 + Element Plus + Vite
- 存储：MinIO (S3 兼容)
- 部署：Docker Compose

## 模块
- 📄 发票识别（OCR + 诺诺发票云验真）
- 💰 销售费用 + 报销中心
- 👥 客户管理 + 跟进
- 📁 项目管理 + 看板
- 📑 合同管理
- 💵 回款管理
- 🤖 AI 智能中心（抽取/问答/风险扫描）

## 本地启动
\`\`\`bash
cp backend/.env.example backend/.env
# 编辑 .env 填入真实密钥
docker compose up -d
# 访问 http://localhost
\`\`\`

## 文档
- [AGENTS.md](./AGENTS.md) - AI 助手协作规范
- [DEPLOY.md](./DEPLOY.md) - 部署指南
- [PROJECT_HANDBOOK.md](./PROJECT_HANDBOOK.md) - 项目手册
- [GITHUB_UPLOAD_STEPS.md](./GITHUB_UPLOAD_STEPS.md) - GitHub 上传步骤
