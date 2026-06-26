# -*- coding: utf-8 -*-
"""
系统设置路由
- GET  /api/v1/admin/settings/all   全量配置（分组+脱敏+元信息）
- PUT  /api/v1/admin/settings/update 批量更新（写内存+写 .env）
- POST /api/v1/admin/settings/test-connection 测试连通性（OCR/诺诺/DB/Redis）

权限：admin only
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional

from app.core.security import require_admin, CurrentUser
from app.modules.system_settings import service

router = APIRouter()


@router.get("/all", summary="全量系统配置（分组+脱敏）")
async def get_all(_admin: CurrentUser = Depends(require_admin())):
    return {"code": 0, "data": service.get_all_settings()}


class UpdateRequest(BaseModel):
    updates: Dict[str, str]


@router.put("/update", summary="更新配置（写内存 + 写 .env）")
async def update_settings(req: UpdateRequest, _admin: CurrentUser = Depends(require_admin())):
    if not req.updates:
        raise HTTPException(status_code=400, detail="updates 不能为空")
    result = service.update_settings(req.updates, operator_id=_admin.id)
    return {"code": 0, "data": result}


class TestRequest(BaseModel):
    target: str  # "ocr" | "nuonuo" | "redis" | "database" | "storage"


@router.post("/test-connection", summary="测试外部服务连通性")
async def test_connection(req: TestRequest, _admin: CurrentUser = Depends(require_admin())):
    if req.target == "ocr":
        try:
            from app.integrations.ocr_client import ocr_client
            r = await ocr_client.health_check() if hasattr(ocr_client, "health_check") else {"status": "unknown"}
            return {"code": 0, "data": {"target": "ocr", **r}}
        except Exception as e:
            return {"code": 0, "data": {"target": "ocr", "status": "down", "error": str(e)}}
    if req.target == "nuonuo":
        from app.integrations import nuonuo
        r = await nuonuo.health_check()
        return {"code": 0, "data": {"target": "nuonuo", **r}}
    if req.target == "redis":
        from app.core.redis_client import redis_client
        try:
            pong = await redis_client.ping()
            return {"code": 0, "data": {"target": "redis", "status": "reachable" if pong else "degraded"}}
        except Exception as e:
            return {"code": 0, "data": {"target": "redis", "status": "down", "error": str(e)}}
    if req.target == "database":
        from app.core.database import AsyncSessionLocal
        try:
            async with AsyncSessionLocal() as s:
                from sqlalchemy import text
                r = await s.execute(text("SELECT 1"))
                r.scalar()
            return {"code": 0, "data": {"target": "database", "status": "reachable"}}
        except Exception as e:
            return {"code": 0, "data": {"target": "database", "status": "down", "error": str(e)}}
    if req.target == "storage":
        from app.integrations import storage
        r = await storage.health_check()
        return {"code": 0, "data": {"target": "storage", **r}}
    raise HTTPException(status_code=400, detail=f"未知 target: {req.target}")


# ============================================================
# 触点 #52：配置备份 / 恢复 / 系统更新
# ============================================================

@router.get("/export", summary="导出所有非敏感配置（JSON）")
async def export_settings(admin: CurrentUser = Depends(require_admin())):
    """导出当前配置为 JSON 文件，便于跨环境迁移。敏感字段（密码/Token）不会导出。"""
    return {"code": 0, "data": service.export_settings(operator_id=admin.id)}


class ImportRequest(BaseModel):
    payload: Dict


@router.post("/import", summary="从 JSON 恢复非敏感配置")
async def import_settings(req: ImportRequest, admin: CurrentUser = Depends(require_admin())):
    """从 export_settings 导出的 JSON 恢复。敏感字段不会导入（需要在目标环境手动配置）。"""
    result = service.import_settings(req.payload, operator_id=admin.id)
    return {"code": 0, "data": result}


@router.get("/update/check", summary="检查 GitHub 是否有新版本")
async def check_update(_admin: CurrentUser = Depends(require_admin())):
    """调 GitHub API 检查最新 release，与当前 git tag/commit 对比。"""
    return {"code": 0, "data": await service.check_update()}


@router.post("/restart", summary="申请软重启后端（reload 当前 worker + 写 sentinel）")
async def restart_backend(_admin: CurrentUser = Depends(require_admin())):
    """软重启后端。

    ⚠️ backend 容器以非 root 用户（appuser）运行，CapEff=0，
    无法直接 kill uvicorn master 进程做容器级重启。
    当前方案：
    1. 写 sentinel 文件 `/tmp/shuzhi-backend-restart.trigger`
       → host 端跑 `shuzhi-restart-watcher` 检测文件就 `docker restart shuzhi-backend`
    2. 当前 worker `os._exit(0)` → uvicorn master 立即 respawn
       → 1/4 worker 加载新代码（其他 3 个仍跑旧代码）

    完整容器级软重启需要满足以下任一：
    - docker run --cap-add=KILL shuzhi-backend
    - docker run -u root shuzhi-backend
    - bind mount /var/run/docker.sock 进容器
    - host 跑 watcher 监听 sentinel 文件
    """
    import os, asyncio, time

    # 1) 写 sentinel 文件
    try:
        with open("/tmp/shuzhi-backend-restart.trigger", "w") as f:
            f.write(f"restart requested at {time.time()}\n")
    except Exception:
        pass

    async def _delayed_reload():
        await asyncio.sleep(1)
        # 当前 worker 退出 → master 立即 fork 新 worker
        os._exit(0)

    asyncio.create_task(_delayed_reload())

    return {
        "code": 0,
        "data": {
            "message": "已请求重启：1/4 worker 即将被替换，剩余 3 个需手动 docker restart shuzhi-backend",
            "delay_seconds": 1,
            "estimated_recovery_seconds": 3,
            "watcher_triggered": True,
            "note": "完整容器级重启需 host 端 watcher: while true; do [ -f /tmp/shuzhi-backend-restart.trigger ] && docker restart shuzhi-backend && rm /tmp/shuzhi-backend-restart.trigger; sleep 1; done"
        }
    }
