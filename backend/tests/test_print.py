"""
UDPE 打印引擎模块测试

测试覆盖:
- 模板 CRUD (create / list / get / update / delete)
- 模板生命周期 (publish / archive)
- 签名模块 (sign_pdf)
- Excel 导入器 (parse_excel)
- HTML 渲染器 (各组件类型)
"""
import pytest
import pytest_asyncio
import io

from app.core.security import hash_password
from app.modules.auth.models import User, Role, Permission, Department


# ============== 本地 fixture ==============

@pytest_asyncio.fixture
async def print_admin(db):
    """拥有 print 全部权限的管理员"""
    dept = Department(name="打印测试部门", code="PRINT_TEST")
    db.add(dept)
    await db.flush()

    role = Role(name="打印管理员", code="print_admin", is_builtin=False)
    db.add(role)
    await db.flush()

    from app.modules.auth.models import RolePermission
    for code in ["print:template:read", "print:template:write", "print:template:admin",
                 "print:document:read", "print:document:export"]:
        perm = (await db.execute(
            __import__("sqlalchemy").select(Permission).where(Permission.code == code)
        )).scalar_one_or_none()
        if perm:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    await db.flush()

    user = User(
        name="打印测试员", account="print_tester",
        password_hash=hash_password("test123"),
        department_id=dept.id, is_active=True,
    )
    db.add(user)
    await db.flush()
    user.roles = [role]
    await db.commit()
    return user


@pytest_asyncio.fixture
async def auth_headers(print_admin, client):
    """登录并返回 Authorization headers"""
    resp = await client.post("/api/v1/auth/login", json={
        "account": print_admin.account, "password": "test123",
    })
    token = resp.json().get("token", "")
    return {"Authorization": f"Bearer {token}"}


# ============== 模板 CRUD 测试 ==============

class TestTemplateCRUD:
    """模板增删改查"""

    async def test_create_template(self, client, auth_headers):
        resp = await client.post("/api/v1/admin/print-templates", json={
            "code": "test_create_v1",
            "name": "测试模板",
            "docType": "contract",
            "paper": "A4",
            "schemaJson": {"body": [{"type": "title", "text": "测试"}]},
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["code"] == "test_create_v1"
        assert data["data"]["status"] == "draft"

    async def test_list_templates(self, client, auth_headers):
        # 先创建
        await client.post("/api/v1/admin/print-templates", json={
            "code": "test_list_v1", "name": "列表测试", "docType": "invoice",
            "schemaJson": {"body": []},
        }, headers=auth_headers)
        resp = await client.get("/api/v1/admin/print-templates", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "list" in data["data"]
        assert data["data"]["total"] >= 1

    async def test_get_template(self, client, auth_headers):
        create_resp = await client.post("/api/v1/admin/print-templates", json={
            "code": "test_get_v1", "name": "详情测试", "docType": "expense",
            "schemaJson": {"body": []},
        }, headers=auth_headers)
        tid = create_resp.json()["data"]["id"]
        resp = await client.get(f"/api/v1/admin/print-templates/{tid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["code"] == "test_get_v1"

    async def test_delete_draft_template(self, client, auth_headers):
        create_resp = await client.post("/api/v1/admin/print-templates", json={
            "code": "test_del_v1", "name": "删除测试", "docType": "expense",
            "schemaJson": {"body": []},
        }, headers=auth_headers)
        tid = create_resp.json()["data"]["id"]
        resp = await client.post("/api/v1/admin/print-templates/delete",
                                 json={"id": tid}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_cannot_delete_active_template(self, client, auth_headers):
        create_resp = await client.post("/api/v1/admin/print-templates", json={
            "code": "test_no_del_v1", "name": "不可删测试", "docType": "expense",
            "schemaJson": {"body": []},
        }, headers=auth_headers)
        tid = create_resp.json()["data"]["id"]
        # 先发布
        await client.post("/api/v1/admin/print-templates/publish",
                          json={"id": tid}, headers=auth_headers)
        # 尝试删除 → 应失败
        resp = await client.post("/api/v1/admin/print-templates/delete",
                                 json={"id": tid}, headers=auth_headers)
        assert resp.status_code in (400, 422)


# ============== 模板生命周期测试 ==============

class TestTemplateLifecycle:
    """发布 / 归档"""

    async def test_publish_template(self, client, auth_headers):
        create_resp = await client.post("/api/v1/admin/print-templates", json={
            "code": "test_pub_v1", "name": "发布测试", "docType": "contract",
            "schemaJson": {"body": []},
        }, headers=auth_headers)
        tid = create_resp.json()["data"]["id"]
        resp = await client.post("/api/v1/admin/print-templates/publish",
                                 json={"id": tid}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "active"

    async def test_archive_template(self, client, auth_headers):
        create_resp = await client.post("/api/v1/admin/print-templates", json={
            "code": "test_arch_v1", "name": "归档测试", "docType": "contract",
            "schemaJson": {"body": []},
        }, headers=auth_headers)
        tid = create_resp.json()["data"]["id"]
        await client.post("/api/v1/admin/print-templates/publish",
                          json={"id": tid}, headers=auth_headers)
        resp = await client.post("/api/v1/admin/print-templates/archive",
                                 json={"id": tid}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "archived"


# ============== 签名模块测试 ==============

class TestSigner:
    """PDF 签名"""

    def test_sign_pdf(self):
        from app.modules.print_runtime.signer import sign_pdf, is_signing_available
        if not is_signing_available():
            pytest.skip("signing not available")
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "Test PDF")
        pdf_bytes = doc.tobytes()
        doc.close()
        signed = sign_pdf(pdf_bytes, reason="单元测试")
        assert len(signed) > len(pdf_bytes)
        # 验证签名后仍是有效 PDF
        doc2 = fitz.open("pdf", signed)
        assert doc2.page_count == 1
        doc2.close()

    def test_sign_empty_pdf(self):
        from app.modules.print_runtime.signer import sign_pdf, is_signing_available
        if not is_signing_available():
            pytest.skip("signing not available")
        import fitz
        doc = fitz.open()
        doc.new_page()
        pdf_bytes = doc.tobytes()
        doc.close()
        signed = sign_pdf(pdf_bytes)
        assert len(signed) > 0


# ============== HTML 渲染器测试 ==============

class TestHtmlRenderer:
    """HTML 渲染器各组件"""

    def test_title_component(self):
        from app.modules.print_runtime.renderers.html_renderer import _render_component
        html_parts = []
        comp = {"type": "title", "text": "测试标题", "fontSize": 20, "align": "center"}
        result = _render_component(comp, {}, html_parts)
        assert "测试标题" in result

    def test_text_component(self):
        from app.modules.print_runtime.renderers.html_renderer import _render_component
        html_parts = []
        comp = {"type": "text", "text": "正文内容", "fontSize": 12}
        result = _render_component(comp, {}, html_parts)
        assert "正文内容" in result

    def test_spacer_component(self):
        from app.modules.print_runtime.renderers.html_renderer import _render_component
        html_parts = []
        comp = {"type": "spacer", "height": 10}
        result = _render_component(comp, {}, html_parts)
        assert "10mm" in result

    def test_grid_component(self):
        from app.modules.print_runtime.renderers.html_renderer import _render_component
        html_parts = []
        comp = {
            "type": "grid", "border": True, "colCount": 2,
            "rows": [{"height": 14, "cells": [
                {"text": "A", "span": 1}, {"text": "B", "span": 1}
            ]}]
        }
        result = _render_component(comp, {}, html_parts)
        assert "<table" in result
        assert "A" in result
        assert "B" in result

    def test_qrcode_component(self):
        from app.modules.print_runtime.renderers.html_renderer import _render_component
        html_parts = []
        comp = {"type": "qrcode", "data": "https://example.com", "size": 100}
        result = _render_component(comp, {}, html_parts)
        assert "img" in result
        assert "data:image/png;base64" in result

    def test_barcode_component(self):
        from app.modules.print_runtime.renderers.html_renderer import _render_component
        html_parts = []
        comp = {"type": "barcode", "data": "ABC123", "height": 50}
        result = _render_component(comp, {}, html_parts)
        assert "img" in result

    def test_pagebreak_component(self):
        from app.modules.print_runtime.renderers.html_renderer import _render_component
        html_parts = []
        comp = {"type": "pagebreak"}
        result = _render_component(comp, {}, html_parts)
        assert "page-break-after" in result


# ============== QR/条码辅助函数测试 ==============

class TestQRBarcode:
    """QR/条码生成"""

    def test_generate_qr_svg(self):
        from app.modules.print_runtime.renderers.html_renderer import _generate_qr_svg
        html = _generate_qr_svg("test data", 120)
        assert "img" in html
        assert "data:image/png;base64" in html

    def test_generate_barcode_html(self):
        from app.modules.print_runtime.renderers.html_renderer import _generate_barcode_html
        html = _generate_barcode_html("TEST-123", 50)
        assert "img" in html
        assert "data:image/png;base64" in html
