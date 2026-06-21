"""
应用配置（pydantic-settings）
从环境变量自动加载，前缀 SHUZHI_
"""
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== 应用 =====
    APP_NAME: str = "数智化管理系统"
    ENV: str = Field(default="development", description="development/staging/production")
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True

    # ===== 数据库 =====
    DATABASE_URL: str = "postgresql+asyncpg://shuzhi:shuzhi@localhost:5432/shuzhi"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600

    # ===== Redis =====
    REDIS_URL: str = "redis://localhost:6379/0"

    # ===== JWT =====
    JWT_SECRET_KEY: str = "dev-secret-please-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ===== 公网 / 静态资源基础 URL =====
    # 拼出 file_url / previewUrl 时使用：
    # - 容器内默认 http://shuzhi-backend:8000（其他容器 OCR service 等能拉图）
    # - 前端浏览器访问用 http://localhost:8000（用户/前端代理）
    # 通过环境变量 SHUZHI_PUBLIC_BASE_URL 注入，覆盖默认值
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # ===== CORS =====
    CORS_ORIGINS: str = "http://localhost:8080,http://localhost:3000"

    # ===== OCR 服务（PaddleOCR 自建微服务）=====
    OCR_SERVICE_URL: str = "http://localhost:8001"
    OCR_CONFIDENCE_THRESHOLD: float = 0.90
    OCR_MODE: str = "real"  # real | mock —— 无 OCR 服务时设 "mock" 自动回退
    OCR_TIMEOUT: int = 30  # 秒
    OCR_RETRY_TIMES: int = 2  # 失败重试次数

    # ===== 诺诺发票云（合规查验）=====
    NUONUO_API_KEY: str = ""  # appKey（空 = mock 模式）
    NUONUO_API_SECRET: str = ""  # appSecret
    NUONUO_API_TOKEN: str = ""  # accessToken（向诺诺 open.nuonuo.com 申请）
    NUONUO_API_URL: str = "https://sandbox.nuonuocs.cn/open/v1/services"  # 沙箱环境
    # 生产环境：https://sdk.nuonuo.com/open/v1/services
    NUONUO_USE_SANDBOX: bool = True
    NUONUO_MODE: str = "real"  # real | mock —— 没配 key 时自动 mock

    # ===== 企业微信 SSO（R6.4 架构预留）=====
    WECHAT_WORK_CORP_ID: str = ""  # 企业 ID（corpid）
    WECHAT_WORK_CORP_SECRET: str = ""  # 应用 secret
    WECHAT_WORK_AGENT_ID: str = ""  # 自建应用 agentid
    WECHAT_WORK_REDIRECT_URI: str = ""  # OAuth 回调地址
    WECHAT_WORK_MODE: str = "real"  # real | mock —— 没配 corp_id 时自动 mock

    # ===== AI 平台（AI-API.md §9）=====
    AI_ENABLED: bool = True
    AI_DEFAULT_TIMEOUT: int = 30  # 秒
    AI_MAX_FILE_SIZE_MB: int = 20
    AI_MAX_DOC_LENGTH_CHARS: int = 50000
    AI_OCR_MODEL: str = "paddleocr-v3"
    AI_LLM_MODEL: str = "qwen2.5-7b-instruct"
    AI_RISK_MODEL: str = "risk-v2.3"
    AI_OCR_ENDPOINT: str = "http://localhost:8001"
    AI_LLM_ENDPOINT: str = "http://localhost:8002"
    AI_LLM_API_KEY: str = ""
    AI_RATE_LIMIT_PER_USER_PER_MIN: int = 30
    AI_RATE_LIMIT_PER_TENANT_PER_HOUR: int = 5000
    AI_COST_LIMIT_PER_TENANT_PER_DAY_CENTS: int = 50000  # 500 元
    AI_ALERT_SCAN_CRON: str = "0 9 * * *"
    AI_ALERT_MAX_PER_USER_PER_DAY: int = 10

    # ===== 对象存储（MinIO S3 兼容）=====
    # 触点 #26：专门管理非结构化数据（发票 PDF/图片/合同/凭证）
    # 切到 MinIO/S3/OSS 时只改这几个字段
    STORAGE_BACKEND: str = "local"  # local | minio（未来可扩展 oss/cos/s3）
    MINIO_ENDPOINT: str = "minio:9000"  # host:port（容器内用 minio:9000，host 用 localhost:9000）
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "shuzhi-files"
    MINIO_SECURE: bool = False  # True = https, False = http
    MINIO_REGION: str = "us-east-1"  # MinIO 默认 region
    # 文件访问 URL 模板（前端用）
    MINIO_PUBLIC_URL: str = ""  # 留空 = 用 MINIO_ENDPOINT；填 CDN 域名可加速

    # ===== Sentry =====
    SENTRY_DSN: str = ""

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @field_validator("LOG_LEVEL")
    @classmethod
    def uppercase_log_level(cls, v: str) -> str:
        return v.upper()


# 全局单例
settings = Settings()
