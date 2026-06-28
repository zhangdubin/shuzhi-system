"""
数智化管理系统 · 后端入口
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import settings
from app.core.exceptions import AppException, app_exception_handler
from app.core.sse import sse_router
from app.core.audit import AuditLogMiddleware
from app.modules.auth.router import router as auth_router
from app.modules.project.router import router as project_router
from app.modules.common.router import router as common_router
from app.modules.contract.router import router as contract_router
from app.modules.expense.router import router as expense_router
from app.modules.receivable.router import router as receivable_router
from app.modules.invoice_template.router import router as invoice_template_router
from app.modules.invoice_ocr.router import router as invoice_ocr_router
from app.modules.invoice_verify.router import router as invoice_verify_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.admin.router import router as admin_router
from app.modules.print_runtime.router import (
    admin_router as print_admin_router,
    runtime_router as print_runtime_router,
)
from app.modules.system_settings.router import router as system_settings_router
from app.modules.cron.router import router as cron_router
from app.modules.ai.router import router as ai_router
from app.modules.reimbursement.router import router as reimbursement_router


def _register_udpe() -> None:
    """UDPE 引擎注册：M1 阶段 3。

    把 2 个 Renderer、4 个业务 Resolver、1 个 VariableProvider 注册到 core.print 注册中心。
    业务模块以后想加 Resolver 只需在自己 router 启动时调 ResolverRegistry.register。
    """
    from app.core.print import (
        ProviderRegistry, RendererRegistry, ResolverRegistry,
    )
    from app.modules.print_runtime.renderers import HtmlRenderer, PdfRenderer
    from app.modules.print_runtime.resolvers import (
        ContractResolver, ExpenseResolver, InvoiceResolver, ReimbursementResolver,
    )
    from app.modules.print_runtime.variables import SystemVarsProvider

    RendererRegistry.register(PdfRenderer())
    RendererRegistry.register(HtmlRenderer())

    ResolverRegistry.register(ContractResolver())
    ResolverRegistry.register(ReimbursementResolver())
    ResolverRegistry.register(ExpenseResolver())
    ResolverRegistry.register(InvoiceResolver())

    ProviderRegistry.register(SystemVarsProvider())

    logger.info(
        f"[UDPE] 已注册 renderers={list(RendererRegistry.all().keys())} "
        f"resolvers={list(ResolverRegistry.all().keys())} "
        f"providers={list(ProviderRegistry.all().keys())}"
    )


# 静态文件目录（uploads）
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info(f"🚀 启动 {settings.APP_NAME} - {settings.ENV}")
    logger.info(f"📊 数据库：{settings.DATABASE_URL.split('@')[-1]}")
    # 启动定时任务调度器
    from app.modules.cron.router import init_scheduler, shutdown_scheduler
    init_scheduler()
    # UDPE 引擎注册（M1 阶段 3 D6）
    _register_udpe()
    yield
    # 关闭（await 异步 shutdown）
    await shutdown_scheduler()
    logger.info("👋 应用关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="数智化管理系统 API",
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url="/redoc" if settings.ENV != "production" else None,
    openapi_url="/openapi.json" if settings.ENV != "production" else None,
    lifespan=lifespan,
)

# ===== 中间件（顺序敏感）=====
# 1. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],  # 开发期放宽
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id", "X-Total-Count"],
)

# 2. 审计日志（写接口自动记录）
app.add_middleware(AuditLogMiddleware)

# 3. Prometheus 指标（R7.2）
from app.core.metrics import prometheus_middleware
app.middleware("http")(prometheus_middleware)

# ===== 全局异常处理 =====
app.add_exception_handler(AppException, app_exception_handler)


# ===== 路由 =====
app.include_router(auth_router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(project_router, prefix="/api/v1/projects", tags=["项目"])
app.include_router(common_router, prefix="/api/v1/common", tags=["公共"])
app.include_router(contract_router, prefix="/api/v1/contracts", tags=["合同"])
app.include_router(expense_router, prefix="/api/v1/expenses", tags=["销售费用"])
app.include_router(receivable_router, prefix="/api/v1/receivables", tags=["回款"])
app.include_router(invoice_template_router, prefix="/api/v1/invoice/templates", tags=["发票模板"])
app.include_router(invoice_ocr_router, prefix="/api/v1/invoice/ocr", tags=["发票识别"])
app.include_router(invoice_verify_router, prefix="/api/v1/invoice/verify", tags=["发票查验"])
app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(cron_router, prefix="/api/v1/cron", tags=["定时任务"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["管理后台"])
# UDPE 统一单据打印引擎（design §五）
app.include_router(print_admin_router, prefix="/api/v1/admin", tags=["打印模板"])
app.include_router(print_runtime_router, prefix="/api/v1", tags=["打印引擎"])
app.include_router(system_settings_router, prefix="/api/v1/admin/settings", tags=["系统设置"])
app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI 平台"])
app.include_router(reimbursement_router, prefix="/api/v1/reimbursements", tags=["报销中心"])
app.include_router(sse_router, prefix="/sse", tags=["SSE"])


# ===== 静态文件（uploads 目录）=====
app.mount("/static/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# 查验凭证 PDF 目录：与 cert_generator 保持一致
# cert_generator.py 位置：app/modules/invoice_verify/cert_generator.py
# 它的 CERT_DIR = app/certificates/ (容器内)
# main.py 位置：app/main.py
# 用相同相对路径：app/certificates/
CERT_DIR = Path(__file__).resolve().parent / "certificates"
CERT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/certificates", StaticFiles(directory=str(CERT_DIR)), name="certificates")
