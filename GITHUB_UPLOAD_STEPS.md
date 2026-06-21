# 上传项目到 GitHub 步骤

> 本项目仓库建议名：`shuzhi-system`（私有）或 `数智化管理系统`（公开）
> ⚠ 务必先确认 `.gitignore` 已就位（.env / dist / __pycache__ / uploads 都不能上传）

## 1. 在 GitHub 网页端建仓库

- 打开 https://github.com/new
- Repository name: `shuzhi-system`
- Description: 数智化管理系统 - 发票识别/销售费用/项目管理/合同管理
- 选择 Public（公开，开源）或 Private（私有，商业）
- ⚠ 不要勾选 "Add a README file" / "Add .gitignore" / "Choose a license"（本地已有）
- 点 Create repository

## 2. 本地首次提交

```bash
cd "/Users/trisome/Desktop/开发/数智化系统new"

# 1) 初始化 git
git init
git config user.name "你的名字"
git config user.email "你的邮箱"

# 2) 检查 .gitignore 是否覆盖关键文件
git status --ignored
# 确认 .env / dist / __pycache__ / node_modules 都列在 "Ignored files"

# 3) 添加 + 首次提交
git add .
git status   # 仔细看！确认没有 .env / dist
git commit -m "feat: 初始版本

- 后端 FastAPI + SQLAlchemy + PostgreSQL
- 前端 Vue 3 + Element Plus + Vite
- 模块：发票识别/销售费用/项目管理/合同/客户/回款/AI
- Docker 部署：backend / frontend / postgres / minio / ocr-service / reimbursement"

# 4) 关联远程仓库（替换 <你的用户名>）
git remote add origin https://github.com/<你的用户名>/shuzhi-system.git

# 5) 推送到 main
git branch -M main
git push -u origin main
```

## 3. 后续日常推送

```bash
git add .
git commit -m "feat: 新增 XXX 功能"
git push
```

## 4. 发布版本（用于「检查更新」接口）

```bash
# 打 tag
git tag -a v1.0.0 -m "v1.0.0 首个正式版本"
git push origin v1.0.0

# 在 GitHub 网页：Releases → Draft a new release
# - Choose tag: v1.0.0
# - Release title: v1.0.0
# - Describe: 写 release notes（用户能在「检查更新」弹窗看到）
# - Publish release
```

## 5. 验证

- 打开 https://github.com/<你的用户名>/shuzhi-system
- ✅ 应该看到 backend/ frontend/ AGENTS.md 等
- ❌ **不应该**看到 .env、dist、__pycache__、uploads/
- 进入「系统设置」→「🔄 检查更新」，应能看到刚发布的 v1.0.0

## 6. 团队成员 onboarding

```bash
git clone https://github.com/<你的用户名>/shuzhi-system.git
cd shuzhi-system
cp backend/.env.example backend/.env
# 编辑 .env 填入真实密钥
docker compose up -d
```

## 7. 重大注意事项

⚠ **永远不要把以下内容上传：**
- `backend/.env`（真实密钥）
- `frontend/dist/`（构建产物，几十 MB）
- `__pycache__/` / `node_modules/`（依赖）
- `uploads/`（用户上传的发票/凭证，含隐私）
- 任何 `*.pem` / `*.key` / 私钥文件

✅ **应该上传：**
- 源代码（backend/app/、frontend/src/）
- 配置模板（.env.example、.env.docker.example）
- 文档（README.md、AGENTS.md、DEPLOY.md）
- 静态资源（icons/、images/，**不是用户上传的**）
- CI/CD 配置（.github/workflows/）
- License（LICENSE 文件）
