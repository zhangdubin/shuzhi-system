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
    target: str  # "ocr" | "nuonuo" | "redis" | "database"


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
    raise HTTPException(status_code=400, detail=f"未知 target: {req.target}")
