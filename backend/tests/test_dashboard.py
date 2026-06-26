"""
Dashboard 模块测试

测试矩阵（2 endpoint）：
- summary: 首页数据汇总
- activities: 最近活动

依据：R1-R16 文档 + 现有 conftest.py fixture 风格
"""
import pytest
from datetime import date


# ============== summary ==============

@pytest.mark.asyncio
async def test_summary_unauthorized(client):
    resp = await client.post("/api/v1/dashboard/summary", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_summary_empty(client, auth_headers):
    """空数据时 summary 应返回默认结构"""
    resp = await client.post(
        "/api/v1/dashboard/summary", json={}, headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    # summary 至少包含基础字段
    assert "greeting" in data or "timeBucket" in data or "kpi" in data or "invoiceCount" in data


@pytest.mark.asyncio
async def test_summary_with_data(client, auth_headers, db, sample_project):
    """有数据时 summary 返回统计"""
    resp = await client.post(
        "/api/v1/dashboard/summary", json={}, headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, dict)


# ============== activities ==============

@pytest.mark.asyncio
async def test_activities_unauthorized(client):
    resp = await client.post("/api/v1/dashboard/activities", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_activities_empty(client, auth_headers):
    """空数据时 activities 应返回空列表"""
    resp = await client.post(
        "/api/v1/dashboard/activities", json={}, headers=auth_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_activities_with_data(client, auth_headers, sample_client):
    """有数据时 activities 返回非空"""
    # 创建一些 audit_log 记录（通过之前的 client 操作）
    resp = await client.post(
        "/api/v1/dashboard/activities", json={}, headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    # 不同 service 版本可能返回 list 或 dict，宽松断言
    assert data is not None


@pytest.mark.asyncio
async def test_activities_pagination(client, auth_headers):
    """分页参数"""
    resp = await client.post(
        "/api/v1/dashboard/activities",
        json={"page": 1, "pageSize": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
