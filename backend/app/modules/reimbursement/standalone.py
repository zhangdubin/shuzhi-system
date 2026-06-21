"""
报销中心 - 独立运行入口
- 跑在 8002 端口，独立进程
- 不挂主后端 8000 → 主后端永远不会因为报销中心挂掉
- 由 deploy/ 下的 reimbursement.Dockerfile 启动
- 通过 nginx 反代 /api/v1/reimbursements → 127.0.0.1:8002

启动：
    uvicorn app.modules.reimbursement.standalone:app --host 0.0.0.0 --port 8002

依赖：
    - 共享主后端的 app.core.database / app.core.security
    - 注册报销中心的所有 API 路由
    - alembic 升级由 deploy entrypoint.sh 跑
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# 复用主后端的核心组件（共享同一 PG/Redis）
from app.core.database import Base, engine
from app.core.security import get_current_user, require_permission
from app.core.exceptions import AppException, app_exception_handler
from app.modules.reimbursement import service
from app.modules.reimbursement.router import router as reimburse_router

logging.basicConfig(level=logging.INFO)
logger.info("🚀 启动 报销中心独立服务（端口 8002）")

app = FastAPI(
    title="数智化系统 - 报销中心",
    version="1.0.0",
    description="独立子服务：销售费用 → 报销单 → 打印 → 回填。共享主后端数据库。",
)

# CORS（与主后端一致）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(reimburse_router, prefix="/api/v1/reimbursements", tags=["报销中心"])

# 全局异常
app.add_exception_handler(AppException, app_exception_handler)


@app.get("/health", tags=["健康检查"])
async def health():
    return {"status": "ok", "service": "reimbursement", "port": 8002}


@app.on_event("startup")
async def on_startup():
    """启动时建表（仅报销中心自己的表），不碰主后端的表"""
    try:
        # 让 Base.metadata 加载所有关联模型（这样 FK 解析不会在 query 时报 NoReferencedTable）
        # 但只物理创建 reimbursement_forms / reimbursement_details 这两张表
        from app.modules.reimbursement.models import ReimbursementForm, ReimbursementDetail, ReimbursementTemplate
        from app.modules.auth.models import User, Department  # FK target: users / departments
        from app.modules.expense.models import Expense  # FK source: expenses
        # 延迟 import，让所有表都注册到 metadata
        try:
            from app.modules.project.models import Project
        except Exception:
            pass
        try:
            from app.modules.contract.models import Contract
        except Exception:
            pass
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, tables=[ReimbursementForm.__table__, ReimbursementDetail.__table__, ReimbursementTemplate.__table__])
        logger.info("✅ 报销表已就绪")
    except Exception as e:
        logger.error(f"❌ 报销表创建失败：{e}")
        raise
