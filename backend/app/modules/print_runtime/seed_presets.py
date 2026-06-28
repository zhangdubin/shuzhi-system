"""UDPE 4 套预置模板 seed 脚本。

设计文档：plans/udpe-design/design.md §三 + 评审决策 #3

用法:
  cd backend
  PYTHONPATH=. python -m app.modules.print_runtime.seed_presets

幂等：已存在同 code 的模板会被跳过。

注意：必须 import auth.models 以让 users 表进入 Base.metadata，
否则 SQLAlchemy 在 sort_tables 阶段会因为 FK 找不到 users 报错。
"""
import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# 触发 metadata 注册（必须先 import，FK 才能 sort 通过）
from app.modules.auth import models as _auth_models  # noqa: F401
from app.config import settings
from app.modules.print_runtime.models import PrintTemplate

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PRESETS_DIR = Path(__file__).resolve().parent / "presets"


def _build_schema_json(preset: dict) -> dict:
    """把 preset JSON 转成 DB 里存的标准 schema_json。

    preset 结构:
      { version, meta, paper, schemaJson: { body: [...] } }
    DB schema_json 结构（设计文档约定，renderer 直接读）:
      { body: [...], meta: {...}, paper: {...}, version: "1.0" }
    """
    meta = preset.get("meta", {})
    paper = preset.get("paper", {"size": "A4", "orientation": "portrait"})
    body = (preset.get("schemaJson") or {}).get("body", [])
    return {
        "version": preset.get("version", "1.0"),
        "meta": meta,
        "paper": paper,
        "body": body,
    }


async def seed_one(db: AsyncSession, preset_file: Path) -> PrintTemplate | None:
    raw = json.loads(preset_file.read_text(encoding="utf-8"))
    meta = raw.get("meta") or {}
    doc_type = meta.get("docType")
    if not doc_type:
        logger.warning(f"[seed] {preset_file.name} 缺少 meta.docType，跳过")
        return None

    code = preset_file.stem  # 例: contract_v1

    existing = (await db.execute(
        select(PrintTemplate).where(PrintTemplate.code == code)
    )).scalar_one_or_none()
    if existing:
        logger.info(f"[seed] 模板 {code} 已存在（id={existing.id}），跳过")
        return existing

    paper = raw.get("paper") or {}
    paper_size = paper.get("size", "A4")
    orientation = paper.get("orientation", "portrait")

    t = PrintTemplate(
        code=code,
        name=meta.get("title", code),
        doc_type=doc_type,
        paper=paper_size,
        width_mm=210.0,
        height_mm=297.0,
        orientation=orientation,
        status="active",
        is_default=True,
        description=meta.get("description", ""),
        schema_json=_build_schema_json(raw),
        version=1,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    logger.info(f"[seed] 已创建模板 {code} (id={t.id}, doc_type={doc_type}, 默认=active)")
    return t


async def main() -> None:
    eng = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(eng, expire_on_commit=False)
    async with Session() as db:
        files = sorted(PRESETS_DIR.glob("*_v1.json"))
        logger.info(f"[seed] 共发现 {len(files)} 套预置模板")
        for f in files:
            await seed_one(db, f)
    await eng.dispose()
    logger.info("[seed] 完成")


if __name__ == "__main__":
    asyncio.run(main())
