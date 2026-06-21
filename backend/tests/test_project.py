"""
项目模块测试

测试矩阵：
- 健康检查
- 未授权访问（401）
- 列表查询（带权限）
- 详情查询
- 创建（权限校验：管理员通 / 普通员工拒）
- 更新
- 删除
- 里程碑
- 统计
"""
import pytest


# ============== 健康检查 ==============

@pytest.mark.asyncio
async def test_health(client):
    """健康检查端点"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


# ============== 鉴权 ==============

@pytest.mark.asyncio
async def test_projects_list_unauthorized(client):
    """未登录访问项目列表 → 401"""
    resp = await client.post(
        "/api/v1/projects/list",
        json={"page": 1, "pageSize": 20},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == 1001  # UnauthorizedException


# ============== 列表 ==============

@pytest.mark.asyncio
async def test_projects_list_empty(client, auth_headers):
    """空列表"""
    resp = await client.post(
        "/api/v1/projects/list",
        json={"page": 1, "pageSize": 20},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["list"] == []
    assert data["data"]["total"] == 0


@pytest.mark.asyncio
async def test_projects_list_with_data(client, auth_headers, sample_project):
    """有数据时返回项目"""
    resp = await client.post(
        "/api/v1/projects/list",
        json={"page": 1, "pageSize": 20},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 1
    assert data["data"]["list"][0]["name"] == "示例项目"
    assert data["data"]["list"][0]["code"] == "PRJ-2026-0001"


@pytest.mark.asyncio
async def test_projects_list_keyword_search(client, auth_headers, sample_project):
    """关键词搜索"""
    resp = await client.post(
        "/api/v1/projects/list",
        json={"page": 1, "pageSize": 20, "keyword": "示例"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["total"] == 1


@pytest.mark.asyncio
async def test_projects_list_keyword_miss(client, auth_headers, sample_project):
    """关键词不匹配"""
    resp = await client.post(
        "/api/v1/projects/list",
        json={"page": 1, "pageSize": 20, "keyword": "不存在的关键词"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0


# ============== 详情 ==============

@pytest.mark.asyncio
async def test_project_detail(client, auth_headers, sample_project):
    """项目详情"""
    resp = await client.post(
        f"/api/v1/projects/detail?projectId={sample_project.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["id"] == sample_project.id
    assert data["data"]["name"] == "示例项目"


@pytest.mark.asyncio
async def test_project_detail_not_found(client, auth_headers):
    """项目不存在 → 404"""
    resp = await client.post(
        "/api/v1/projects/detail?projectId=99999",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == 2004


# ============== 创建（权限校验） ==============

@pytest.mark.asyncio
async def test_create_project_unauthorized_user(
    client, user_token, sample_client, normal_user
):
    """普通员工无 project:write 权限 → 403"""
    resp = await client.post(
        "/api/v1/projects/create",
        json={
            "name": "无权创建",
            "managerId": normal_user.id,
            "clientId": sample_client.id,
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == 1003


@pytest.mark.asyncio
async def test_create_project_success(
    client, auth_headers, sample_client, admin_user
):
    """管理员创建项目"""
    resp = await client.post(
        "/api/v1/projects/create",
        json={
            "name": "新项目",
            "type": "系统集成",
            "clientId": sample_client.id,
            "managerId": admin_user.id,
            "startDate": "2026-07-01",
            "endDate": "2026-12-31",
            "budget": 1000000,  # 1 万（分）
            "description": "新建项目测试",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "新项目"
    assert data["data"]["code"].startswith("PRJ-")
    assert data["data"]["status"] == "draft"  # 默认状态


@pytest.mark.asyncio
async def test_create_project_invalid_dates(client, auth_headers, admin_user):
    """截止日期早于开始日期 → 422"""
    resp = await client.post(
        "/api/v1/projects/create",
        json={
            "name": "日期错误",
            "managerId": admin_user.id,
            "startDate": "2026-12-31",
            "endDate": "2026-01-01",  # 早于开始
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ============== 更新 ==============

@pytest.mark.asyncio
async def test_update_project(client, auth_headers, sample_project):
    """更新项目名称"""
    resp = await client.post(
        f"/api/v1/projects/update?projectId={sample_project.id}",
        json={"name": "已重命名的项目"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "已重命名的项目"


# ============== 删除 ==============

@pytest.mark.asyncio
async def test_delete_project(client, auth_headers, sample_project):
    """删除项目"""
    resp = await client.post(
        f"/api/v1/projects/delete?projectId={sample_project.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    # 再次查询应该 404
    detail = await client.post(
        f"/api/v1/projects/detail?projectId={sample_project.id}",
        headers=auth_headers,
    )
    assert detail.status_code == 404


# ============== 统计 ==============

@pytest.mark.asyncio
async def test_project_stats(client, auth_headers, sample_project):
    """项目统计"""
    resp = await client.post(
        "/api/v1/projects/stats",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "active" in data["data"]
    assert "totalContractAmount" in data["data"]
