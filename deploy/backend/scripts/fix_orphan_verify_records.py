"""
修复历史的 verify 记录：补全 invoice_id 关联
- 根据 invoice_no 找最近的一张 Invoice，把 verify_record.invoice_id 补上
- 仅当 invoice_no 一一对应时（避免错配）
"""
import asyncio
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.modules.invoice_ocr.models import InvoiceVerifyRecord, Invoice

async def main():
    async with AsyncSessionLocal() as db:
        # 找出所有 invoice_id IS NULL 的 verify 记录
        orphans = (await db.execute(
            select(InvoiceVerifyRecord).where(InvoiceVerifyRecord.invoice_id.is_(None))
        )).scalars().all()
        print(f"Found {len(orphans)} orphan verify records")
        # 按 invoice_no 查最近的 Invoice
        from collections import defaultdict
        by_no: dict[str, list[InvoiceVerifyRecord]] = defaultdict(list)
        for rec in orphans:
            if rec.invoice_no:
                by_no[rec.invoice_no].append(rec)
        updated = 0
        for no, recs in by_no.items():
            inv = (await db.execute(
                select(Invoice).where(Invoice.invoice_no == no).order_by(Invoice.id.desc()).limit(1)
            )).scalar_one_or_none()
            if inv:
                for rec in recs:
                    rec.invoice_id = inv.id
                    updated += 1
        await db.commit()
        print(f"Updated {updated} records")

asyncio.run(main())
