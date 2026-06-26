# -*- coding: utf-8 -*-
"""
系统设置（运维可视化配置）服务
- GET: 返回分组后的所有配置（带元信息 + 脱敏值 + 是否敏感）
- PUT: 更新字段，写回 .env 文件（注意不是容器内 .env，而是用户的工作目录 .env）
- 不重启即时生效：仅对部分"运行时可变"字段
"""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import httpx

from app.config import settings

# ============================================================
# 配置项元数据（前端用来展示表单）
# ============================================================
SETTING_METAS: List[Dict[str, Any]] = [
    # ===== 应用 =====
    {"key": "APP_NAME", "group": "应用", "label": "应用名称", "type": "string", "sensitive": False},
    {"key": "ENV", "group": "应用", "label": "运行环境", "type": "enum", "options": ["development", "staging", "production"], "sensitive": False},
    {"key": "DEBUG", "group": "应用", "label": "调试模式", "type": "bool", "sensitive": False},
    {"key": "LOG_LEVEL", "group": "应用", "label": "日志级别", "type": "enum", "options": ["DEBUG", "INFO", "WARNING", "ERROR"], "sensitive": False},

    # ===== 数据库（敏感） =====
    {"key": "DATABASE_URL", "group": "数据库", "label": "数据库连接", "type": "string", "sensitive": True, "placeholder": "postgresql+asyncpg://user:pass@host:5432/db"},
    {"key": "DB_POOL_SIZE", "group": "数据库", "label": "连接池大小", "type": "int", "sensitive": False},
    {"key": "DB_MAX_OVERFLOW", "group": "数据库", "label": "连接池溢出", "type": "int", "sensitive": False},

    # ===== Redis =====
    {"key": "REDIS_URL", "group": "Redis", "label": "Redis 连接", "type": "string", "sensitive": True},

    # ===== JWT =====
    {"key": "JWT_SECRET_KEY", "group": "JWT 安全", "label": "JWT 签名密钥", "type": "string", "sensitive": True, "warning": "修改后所有已签发 token 失效，用户需重新登录"},
    {"key": "JWT_ALGORITHM", "group": "JWT 安全", "label": "签名算法", "type": "enum", "options": ["HS256", "HS384", "HS512"], "sensitive": False},
    {"key": "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "group": "JWT 安全", "label": "访问 Token 过期（分钟）", "type": "int", "sensitive": False},
    {"key": "JWT_REFRESH_TOKEN_EXPIRE_DAYS", "group": "JWT 安全", "label": "刷新 Token 过期（天）", "type": "int", "sensitive": False},

    # ===== CORS =====
    {"key": "CORS_ORIGINS", "group": "CORS", "label": "允许的跨域来源", "type": "string", "placeholder": "http://a.com,http://b.com", "sensitive": False},

    # ===== OCR =====
    {"key": "OCR_SERVICE_URL", "group": "OCR 识别", "label": "OCR 服务地址", "type": "string", "sensitive": False},
    {"key": "OCR_MODE", "group": "OCR 识别", "label": "运行模式", "type": "enum", "options": ["real", "mock"], "sensitive": False},
    {"key": "OCR_CONFIDENCE_THRESHOLD", "group": "OCR 识别", "label": "置信度阈值（0-1）", "type": "float", "min": 0, "max": 1, "step": 0.05, "sensitive": False},
    {"key": "OCR_TIMEOUT", "group": "OCR 识别", "label": "超时（秒）", "type": "int", "sensitive": False},

    # ===== GitHub Release（系统更新检查）=====
    {"key": "GITHUB_REPO_OWNER", "group": "系统更新", "label": "仓库 Owner（用户/组织名）", "type": "string", "sensitive": False, "placeholder": "如 zhangdubin"},
    {"key": "GITHUB_REPO_NAME", "group": "系统更新", "label": "仓库名", "type": "string", "sensitive": False, "placeholder": "如 shuzhi-system"},
    {"key": "GITHUB_API_BASE", "group": "系统更新", "label": "GitHub API 地址", "type": "string", "sensitive": False, "placeholder": "https://api.github.com"},
    {"key": "GITHUB_TOKEN", "group": "系统更新", "label": "GitHub Token（PAT）", "type": "string", "sensitive": True, "placeholder": "Private 仓库必填；公开仓库可留空（填写后限额 60/h → 5000/h）", "help": "申请：https://github.com/settings/tokens/new （无 scopes 即可）"},
    {"key": "APP_VERSION", "group": "系统更新", "label": "当前版本号", "type": "string", "sensitive": False, "help": "CI/CD 构建时注入；本地留默认 1.0.0"},

    # ===== 诺诺发票云 =====
    {"key": "NUONUO_API_KEY", "group": "诺诺发票云", "label": "AppKey", "type": "string", "sensitive": True, "placeholder": "向诺诺开放平台申请"},
    {"key": "NUONUO_API_SECRET", "group": "诺诺发票云", "label": "AppSecret", "type": "string", "sensitive": True},
    {"key": "NUONUO_API_TOKEN", "group": "诺诺发票云", "label": "AccessToken", "type": "string", "sensitive": True},
    {"key": "NUONUO_API_URL", "group": "诺诺发票云", "label": "API 地址", "type": "string", "sensitive": False,
     "options_help": {"sandbox": "https://sandbox.nuonuocs.cn/open/v1/services", "prod": "https://sdk.nuonuo.com/open/v1/services"}},
    {"key": "NUONUO_USE_SANDBOX", "group": "诺诺发票云", "label": "使用沙箱环境", "type": "bool", "sensitive": False},
    {"key": "NUONUO_MODE", "group": "诺诺发票云", "label": "运行模式", "type": "enum", "options": ["real", "mock", "auto"], "sensitive": False, "help": "auto = 按 Key 是否存在自动判断"},

    # ===== 企业微信 SSO =====
    {"key": "WECHAT_WORK_CORP_ID", "group": "企业微信 SSO", "label": "Corp ID", "type": "string", "sensitive": True},
    {"key": "WECHAT_WORK_CORP_SECRET", "group": "企业微信 SSO", "label": "Corp Secret", "type": "string", "sensitive": True},
    {"key": "WECHAT_WORK_AGENT_ID", "group": "企业微信 SSO", "label": "Agent ID", "type": "string", "sensitive": False},
    {"key": "WECHAT_WORK_REDIRECT_URI", "group": "企业微信 SSO", "label": "OAuth 回调地址", "type": "string", "sensitive": False},
    {"key": "WECHAT_WORK_MODE", "group": "企业微信 SSO", "label": "运行模式", "type": "enum", "options": ["real", "mock", "auto"], "sensitive": False},

    # ===== AI 平台 =====
    {"key": "AI_ENABLED", "group": "AI 平台", "label": "启用 AI", "type": "bool", "sensitive": False},
    {"key": "AI_LLM_MODEL", "group": "AI 平台", "label": "默认 LLM 模型", "type": "string", "sensitive": False},
    {"key": "AI_LLM_ENDPOINT", "group": "AI 平台", "label": "LLM API 地址", "type": "string", "sensitive": False},
    {"key": "AI_LLM_API_KEY", "group": "AI 平台", "label": "LLM API Key", "type": "string", "sensitive": True},
    {"key": "AI_DEFAULT_TIMEOUT", "group": "AI 平台", "label": "默认超时（秒）", "type": "int", "sensitive": False},
    {"key": "AI_MAX_FILE_SIZE_MB", "group": "AI 平台", "label": "单文件最大（MB）", "type": "int", "sensitive": False},
    {"key": "AI_RATE_LIMIT_PER_USER_PER_MIN", "group": "AI 平台", "label": "每用户每分钟限流", "type": "int", "sensitive": False},
    {"key": "AI_RATE_LIMIT_PER_TENANT_PER_HOUR", "group": "AI 平台", "label": "每租户每小时限流", "type": "int", "sensitive": False},
    {"key": "AI_COST_LIMIT_PER_TENANT_PER_DAY_CENTS", "group": "AI 平台", "label": "每租户每日费用上限（分）", "type": "int", "sensitive": False},

    # ===== 对象存储 MinIO =====
    {"key": "STORAGE_BACKEND", "group": "对象存储 MinIO", "label": "存储后端", "type": "enum", "options": ["local", "minio"], "sensitive": False, "help": "local = 本地文件；minio = S3 兼容对象存储（MinIO/OSS/COS）"},
    {"key": "MINIO_ENDPOINT", "group": "对象存储 MinIO", "label": "Endpoint（host:port）", "type": "string", "sensitive": False, "placeholder": "minio:9000（容器内） 或 localhost:9000（host）"},
    {"key": "MINIO_ACCESS_KEY", "group": "对象存储 MinIO", "label": "Access Key", "type": "string", "sensitive": True},
    {"key": "MINIO_SECRET_KEY", "group": "对象存储 MinIO", "label": "Secret Key", "type": "string", "sensitive": True, "warning": "明文存储在 .env，请妥善保管"},
    {"key": "MINIO_BUCKET", "group": "对象存储 MinIO", "label": "Bucket 名称", "type": "string", "sensitive": False, "placeholder": "shuzhi-files"},
    {"key": "MINIO_SECURE", "group": "对象存储 MinIO", "label": "HTTPS", "type": "bool", "sensitive": False, "help": "true = https（生产），false = http（开发）"},
    {"key": "MINIO_REGION", "group": "对象存储 MinIO", "label": "Region", "type": "string", "sensitive": False, "placeholder": "us-east-1"},
    {"key": "MINIO_PUBLIC_URL", "group": "对象存储 MinIO", "label": "公网访问 URL", "type": "string", "sensitive": False, "placeholder": "https://minio.example.com（留空则用 endpoint）"},

    # ===== Sentry =====
    {"key": "SENTRY_DSN", "group": "Sentry 监控", "label": "Sentry DSN", "type": "string", "sensitive": True},
]


# 运行时可立即生效的字段（不需重启）
HOT_RELOAD_KEYS = {
    "OCR_CONFIDENCE_THRESHOLD", "OCR_TIMEOUT", "OCR_MODE",
    "NUONUO_MODE", "NUONUO_API_URL", "NUONUO_USE_SANDBOX",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "AI_DEFAULT_TIMEOUT", "AI_MAX_FILE_SIZE_MB",
    "AI_RATE_LIMIT_PER_USER_PER_MIN", "AI_RATE_LIMIT_PER_TENANT_PER_HOUR",
    "AI_COST_LIMIT_PER_TENANT_PER_DAY_CENTS",
    "AI_ENABLED", "AI_LLM_MODEL", "AI_LLM_ENDPOINT",
    "CORS_ORIGINS", "LOG_LEVEL", "DEBUG",
}


def _mask_value(v: Any) -> str:
    """脱敏：保留前 2 + *** + 后 2"""
    s = str(v)
    if len(s) <= 6:
        return "***"
    return s[:2] + "***" + s[-2:]


def get_all_settings() -> Dict[str, Any]:
    """返回全量配置（按 group 分组），敏感字段脱敏"""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for meta in SETTING_METAS:
        key = meta["key"]
        raw_value = getattr(settings, key, None)
        is_set = raw_value is not None and str(raw_value) != ""
        item = {
            **meta,
            "isSet": is_set,
            "displayValue": _mask_value(raw_value) if (meta.get("sensitive") and is_set) else ("" if not is_set else str(raw_value)),
            "rawType": type(raw_value).__name__ if raw_value is not None else meta["type"],
            "hotReload": key in HOT_RELOAD_KEYS,
        }
        groups.setdefault(meta["group"], []).append(item)

    return {
        "groups": groups,
        "envFilePath": _find_env_path(),
        "runtimeEnv": settings.ENV,
        "version": settings.APP_VERSION or settings.APP_NAME,
    }


def _find_env_path() -> str:
    """找到 .env 文件路径
    优先级：
      1) SHUZHI_ENV_FILE 环境变量指定的路径（deploy 场景）
      2) /app/.env （容器内 backend 工作目录）
      3) 当前工作目录 .env
      4) backend 源码根 .env
    """
    import os
    override = os.environ.get("SHUZHI_ENV_FILE")
    candidates = []
    if override:
        candidates.append(Path(override))
    candidates += [
        Path("/app/.env"),
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    for p in candidates:
        try:
            if p.exists():
                return str(p)
        except OSError:
            continue
    return ""


def update_settings(updates: Dict[str, str], operator_id: int) -> Dict[str, Any]:
    """更新配置：内存立即生效（运行时可热加载的），同时写回 .env"""
    valid_keys = {m["key"] for m in SETTING_METAS}
    applied = []
    rejected = []

    for k, v in updates.items():
        if k not in valid_keys:
            rejected.append({"key": k, "reason": "未知配置项"})
            continue
        # 内存更新
        try:
            setattr(settings, k, v)
            applied.append({"key": k, "hotReload": k in HOT_RELOAD_KEYS})
        except Exception as e:
            rejected.append({"key": k, "reason": str(e)})

    # 写 .env（如果路径存在）
    env_path = _find_env_path()
    written = False
    if env_path:
        try:
            _write_env(env_path, updates)
            written = True
        except Exception as e:
            rejected.append({"key": "_env_write", "reason": f"写 .env 失败：{e}"})

    # 写 audit log
    from app.modules.auth.models import AuditLog
    from app.core.database import AsyncSessionLocal
    import asyncio
    try:
        async def _audit():
            async with AsyncSessionLocal() as s:
                log = AuditLog(
                    operator_id=operator_id,
                    action="system_settings_update",
                    resource_type="system_settings",
                    resource_id=None,
                    body=f"updated={len(applied)} rejected={len(rejected)} env_written={written}",
                )
                s.add(log)
                await s.commit()
        asyncio.get_event_loop().create_task(_audit())
    except Exception:
        pass

    return {
        "applied": applied,
        "rejected": rejected,
        "envWritten": written,
        "envPath": env_path,
    }


def _write_env(env_path: str, updates: Dict[str, str]) -> None:
    """原子写 .env：保留原顺序、注释、空行，更新已有 key、追加新 key"""
    p = Path(env_path)
    lines = p.read_text(encoding="utf-8").splitlines()
    out_lines = []
    touched = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            out_lines.append(line)
            continue
        if "=" not in stripped:
            out_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            v = updates[key]
            # 字符串值带引号避免 # 号被误判
            if any(c in v for c in " #\t"):
                v_escaped = '"' + v.replace('"', '\\"') + '"'
            else:
                v_escaped = v
            out_lines.append(f"{key}={v_escaped}")
            touched.add(key)
        else:
            out_lines.append(line)
    # 追加未在文件中的新 key
    for k, v in updates.items():
        if k not in touched:
            v_escaped = '"' + v.replace('"', '\\"') + '"' if any(c in v for c in " #\t") else v
            out_lines.append(f"{k}={v_escaped}")
    # 写入：mount 模式下 os.replace 跨设备会失败，先尝试原子写，失败回退直接覆盖
    content = "\n".join(out_lines) + "\n"
    try:
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        # mount 跨设备：直接覆盖（短暂不一致，但保证成功）
        p.write_text(content, encoding="utf-8")


# ============================================================
# 配置备份 / 恢复（运维迁移用）
# ============================================================

def export_settings(operator_id: int) -> Dict[str, Any]:
    """导出当前所有非敏感配置 + 敏感配置的存在性标记

    设计原则：
    - 敏感字段（密码/密钥/Token）**不导出**，只导出"已设置"标记，便于审计
    - 导出文件带版本号 + 时间戳 + 操作人，便于在多环境间迁移
    - 导入时只接受"非敏感"字段，敏感字段仍需在新环境手动配置
    """
    safe_items: List[Dict[str, Any]] = []
    sensitive_keys: List[str] = []
    for meta in SETTING_METAS:
        key = meta["key"]
        raw_value = getattr(settings, key, None)
        if meta.get("sensitive"):
            # 敏感字段：只标记"已设置"状态
            sensitive_keys.append({
                "key": key,
                "group": meta["group"],
                "label": meta["label"],
                "isSet": raw_value is not None and str(raw_value) != "",
            })
        else:
            # 非敏感字段：明文导出
            safe_items.append({
                "key": key,
                "group": meta["group"],
                "label": meta["label"],
                "type": meta["type"],
                "value": "" if raw_value is None else str(raw_value),
            })

    # 写审计
    from app.modules.auth.models import AuditLog
    from app.core.database import AsyncSessionLocal
    import asyncio
    async def _audit():
        try:
            async with AsyncSessionLocal() as s:
                s.add(AuditLog(
                    operator_id=operator_id,
                    action="system_settings_export",
                    resource_type="system_settings",
                    resource_id=0,
                    body=json.dumps({"safe_count": len(safe_items), "sensitive_count": len(sensitive_keys)}, ensure_ascii=False),
                ))
                await s.commit()
        except Exception:
            pass
    try:
        asyncio.get_event_loop().create_task(_audit())
    except RuntimeError:
        pass

    return {
        "formatVersion": 1,
        "exportedAt": datetime.utcnow().isoformat() + "Z",
        "exportedBy": operator_id,
        "runtimeEnv": settings.ENV,
        "appName": settings.APP_NAME,
        "safeItems": safe_items,
        "sensitiveKeys": sensitive_keys,
        "notice": "敏感字段（密码/Token/密钥）未导出。导入前请确认目标环境已配置对应敏感字段。",
    }


def import_settings(payload: Dict[str, Any], operator_id: int) -> Dict[str, Any]:
    """从 export_settings 生成的 JSON 恢复非敏感配置

    - 校验 formatVersion
    - 拒绝敏感字段（payload 里没有 value）
    - 走 update_settings 同样的写流程（内存 + .env）
    """
    if payload.get("formatVersion") != 1:
        raise ParamErrorException(f"配置包格式不兼容：formatVersion={payload.get('formatVersion')}")
    safe_items = payload.get("safeItems", [])
    if not isinstance(safe_items, list):
        raise ParamErrorException("safeItems 必须是数组")

    updates: Dict[str, str] = {}
    skipped: List[str] = []
    for item in safe_items:
        if not isinstance(item, dict) or "key" not in item or "value" not in item:
            skipped.append(str(item))
            continue
        key = item["key"]
        # 安全：跳过敏感字段
        meta = next((m for m in SETTING_METAS if m["key"] == key), None)
        if meta is None:
            skipped.append(key)
            continue
        if meta.get("sensitive"):
            skipped.append(key)
            continue
        updates[key] = str(item["value"])

    if not updates:
        return {"applied": [], "skipped": skipped, "rejected": []}

    # 复用 update_settings 的写流程（带审计 + 写 .env）
    result = update_settings(updates, operator_id=operator_id)
    result["skipped"] = skipped
    return result


# ============================================================
# 系统更新（检查新版本）
# ============================================================

# GitHub Release 仓库配置已移至 app.config.settings（GITHUB_REPO_OWNER / GITHUB_REPO_NAME / GITHUB_API_BASE）


async def check_update() -> Dict[str, Any]:
    """检查 GitHub release 是否有新版本

    返回:
    {
      "currentVersion": "v1.0.0",   # 当前版本
      "latestVersion": "v1.0.5",     # 最新 release
      "hasUpdate": true,
      "releaseUrl": "...",
      "releaseNotes": "...",
      "publishedAt": "...",
      "size": 1234,
    }
    """
    # 当前版本从 git tag 读
    current = _get_current_git_version()

    # 调用 GitHub API 拿最新 release
    try:
        url = f"{settings.GITHUB_API_BASE}/repos/{settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}/releases/latest"
        # GitHub PAT 头（Private 仓库或提升限流）
        _gh_headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "shuzhi-update-checker",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if settings.GITHUB_TOKEN:
            _gh_headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, headers=_gh_headers)
            if r.status_code == 404:
                # 可能是仓库不存在 / 仓库私有无 token / 仓库未发 release
                _err = "仓库未发布任何 release"
                if not settings.GITHUB_TOKEN:
                    _err += "（若仓库为 Private，请在 .env 配置 GITHUB_TOKEN）"
                return {"currentVersion": current, "latestVersion": None, "hasUpdate": False, "releaseUrl": None, "error": _err}
            if r.status_code != 200:
                return {"currentVersion": current, "latestVersion": None, "hasUpdate": False, "releaseUrl": None, "error": f"GitHub API HTTP {r.status_code}"}
            data = r.json()
        latest = data.get("tag_name") or data.get("name")
        release_url = data.get("html_url")
        notes = data.get("body", "")
        published = data.get("published_at")
        size = 0
        for asset in data.get("assets", []):
            size += asset.get("size", 0)
        has_update = _is_newer(latest, current) if latest and current else False
        return {
            "currentVersion": current,
            "latestVersion": latest,
            "hasUpdate": has_update,
            "releaseUrl": release_url,
            "releaseNotes": notes[:500] + ("..." if len(notes) > 500 else ""),
            "publishedAt": published,
            "assetSizeMB": round(size / 1024 / 1024, 2),
        }
    except httpx.ConnectError:
        return {"currentVersion": current, "latestVersion": None, "hasUpdate": False, "error": "无法连接 GitHub（请检查网络/代理）"}
    except Exception as e:
        return {"currentVersion": current, "latestVersion": None, "hasUpdate": False, "error": f"检查失败：{type(e).__name__}: {e}"}


def _get_current_git_version() -> str:
    """读当前版本：优先用 settings.APP_VERSION（CI/CD 注入），fallback 到 git"""
    # 1) 优先：环境变量/CI 注入的版本号
    # 优先用 settings.APP_VERSION（.env / CI / 构建时注入）
    _app_v = getattr(settings, "APP_VERSION", None)
    if _app_v and _app_v.strip() and _app_v.strip() != "unknown":
        return _app_v.strip()
    # 2) fallback：git tag 或 commit
    try:
        # 优先 tag
        out = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, timeout=3,
            cwd="/app" if os.path.isdir("/app/.git") else os.getcwd(),
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    try:
        # fallback: short commit
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=3,
            cwd="/app" if os.path.isdir("/app/.git") else os.getcwd(),
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _is_newer(latest: str, current: str) -> bool:
    """简单 SemVer 比较：v1.2.3 vs v1.2.0 → True"""
    import re
    def parse(v: str) -> Tuple[int, ...]:
        m = re.findall(r"\d+", v)
        return tuple(int(x) for x in m[:3]) if m else (0,)
    try:
        return parse(latest) > parse(current)
    except Exception:
        return False
