"""
定时任务
- 4 个手动端点：overdue-check / upcoming-due / contract-expiring / all
- 1 个 scheduler（apscheduler 异步版）：每天 9:00 跑 all，每天 18:00 跑 overdue-check

后端启动时 init_scheduler() 注册；停止时 shutdown_scheduler()。

R6.5.2 多 worker 适配：
- 4 worker 模式下，每个 worker 启动都会调 init_scheduler
- 用 Redis 分布式锁（lock:scheduler:scheduler）确保**只有 1 个 worker**真的起 scheduler
- 没抢到锁的 worker 跳过启动 scheduler，但保留 API 服务
- 锁 TTL 60s（scheduler 进程意外退出时，60s 内可被新 worker 抢到）
"""
import logging
from datetime import date, timedelta
import os
import secrets
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.sse import publish_event, get_redis
from app.config import settings
from app.modules.receivable.models import Receivable
from app.modules.contract.models import Contract

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局 scheduler
_scheduler: AsyncIOScheduler | None = None


# ============================================================
# 核心 task 函数（可被手动端点 + scheduler 共用）
# ============================================================

async def run_overdue_check(db: AsyncSession) -> dict:
    """扫描逾期回款 + SSE 提醒"""
    today = date.today()
    rows = (await db.execute(
        select(Receivable)
        .where(
            Receivable.status.in_(["pending", "partial"]),
            Receivable.plan_date < today,
        )
        .limit(100)
    )).scalars().all()

    count = 0
    for r in rows:
        overdue_days = (today - r.plan_date).days
        await publish_event("sse:dashboard", "alert", {
            "type": "回款",
            "action": "逾期",
            "level": "high" if overdue_days > 30 else "medium",
            "title": f"⚠️ 回款 #{r.id} 已逾期 {overdue_days} 天（{r.code}）",
            "operator": "系统定时",
            "receivableId": r.id,
        })
        count += 1
    return {"scanned": len(rows), "alerted": count}


async def run_upcoming_due(db: AsyncSession) -> dict:
    """扫描 3 天内即将到期回款"""
    today = date.today()
    three_days_later = today + timedelta(days=3)
    rows = (await db.execute(
        select(Receivable)
        .where(
            Receivable.status.in_(["pending", "partial"]),
            Receivable.plan_date >= today,
            Receivable.plan_date <= three_days_later,
        )
        .limit(100)
    )).scalars().all()

    count = 0
    for r in rows:
        days_left = (r.plan_date - today).days
        await publish_event("sse:dashboard", "alert", {
            "type": "回款",
            "action": "即将到期",
            "level": "low",
            "title": f"📅 回款 #{r.id} 将在 {days_left} 天后到期（{r.code}）",
            "operator": "系统定时",
            "receivableId": r.id,
        })
        count += 1
    return {"scanned": len(rows), "alerted": count}


async def run_contract_expiring(db: AsyncSession) -> dict:
    """扫描 30 天内即将到期合同"""
    today = date.today()
    thirty_days_later = today + timedelta(days=30)
    rows = (await db.execute(
        select(Contract)
        .where(
            Contract.status.in_(["approved", "signed"]),
            Contract.expire_date >= today,
            Contract.expire_date <= thirty_days_later,
        )
        .limit(100)
    )).scalars().all()

    count = 0
    for c in rows:
        days_left = (c.expire_date - today).days
        await publish_event("sse:dashboard", "alert", {
            "type": "合同",
            "action": "即将到期",
            "level": "medium" if days_left < 7 else "low",
            "title": f"📋 合同 #{c.id} 将在 {days_left} 天后到期（{c.code}）",
            "operator": "系统定时",
            "contractId": c.id,
        })
        count += 1
    return {"scanned": len(rows), "alerted": count}


# ============================================================
# Scheduler 启动/停止
# ============================================================

# ============================================================
# Scheduler 启动/停止（R6.5.2 分布式锁 + 单 worker 化）
# ============================================================

# 锁 key + TTL
SCHEDULER_LOCK_KEY = "lock:scheduler:scheduler"
SCHEDULER_LOCK_TTL = 60  # 60s（如果持锁 worker 意外退出，60s 内可被新 worker 抢到）
SCHEDULER_LOCK_REFRESH = 30  # 持锁 worker 每 30s 续期一次

_scheduler_lock_value: str | None = None  # 当前 worker 持锁的 token
_scheduler_lock_renew_task: asyncio.Task | None = None  # 续期任务


async def _try_acquire_scheduler_lock() -> bool:
    """尝试抢锁（SET NX EX）。返回 True=抢到，False=没抢到"""
    global _scheduler_lock_value
    r = await get_redis()
    token = secrets.token_hex(16)  # 唯一 token，防止误删别人的锁
    ok = await r.set(SCHEDULER_LOCK_KEY, token, nx=True, ex=SCHEDULER_LOCK_TTL)
    if ok:
        _scheduler_lock_value = token
        return True
    return False


async def _renew_scheduler_lock_loop():
    """持锁 worker 定期续期（避免 TTL 过期被别的 worker 抢到）"""
    while True:
        try:
            await asyncio.sleep(SCHEDULER_LOCK_REFRESH)
            r = await get_redis()
            # 用 Lua 脚本：仅当 value 等于自己 token 时才续期
            lua = """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('expire', KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            await r.eval(lua, 1, SCHEDULER_LOCK_KEY, _scheduler_lock_value, SCHEDULER_LOCK_TTL)
            logger.debug(f"[cron] scheduler lock renewed (ttl={SCHEDULER_LOCK_TTL}s)")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"[cron] lock renew 失败: {e}")


async def _release_scheduler_lock():
    """释放锁（仅当 value 等于自己 token 时）"""
    global _scheduler_lock_value
    if not _scheduler_lock_value:
        return
    try:
        r = await get_redis()
        lua = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        await r.eval(lua, 1, SCHEDULER_LOCK_KEY, _scheduler_lock_value)
        # 清 jobs 元数据
        await r.delete("scheduler:jobs:list")
        logger.info("[cron] scheduler lock released + jobs 元数据已清")
    except Exception as e:
        logger.warning(f"[cron] lock release 失败: {e}")
    finally:
        _scheduler_lock_value = None


def init_scheduler():
    """注册定时任务（启动时调一次）
    R6.5.2: 4 worker 模式下用 Redis 锁保证只有 1 个 worker 真起 scheduler
    """
    global _scheduler, _scheduler_lock_renew_task
    if _scheduler is not None:
        logger.warning("[cron] scheduler 已初始化，跳过")
        return

    # 异步抢锁（不阻塞 lifespan）
    asyncio.create_task(_async_init_scheduler())


async def _async_init_scheduler():
    """异步启动 scheduler：抢锁 → 抢到则 start → 起续期任务"""
    global _scheduler, _scheduler_lock_renew_task

    # 1. 抢锁
    pid = os.getpid()
    acquired = await _try_acquire_scheduler_lock()
    if not acquired:
        logger.info(f"[cron] worker pid={pid} 未抢到 scheduler 锁，跳过启动（其他 worker 已持有）")
        return

    logger.info(f"[cron] worker pid={pid} 抢到 scheduler 锁，开始注册定时任务")

    # 2. 注册 3 个 job
    _scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    _scheduler.add_job(
        _scheduled_all_checks,
        CronTrigger(hour=9, minute=0),
        id="daily_all_checks",
        name="每日 9 点全量业务检查",
        replace_existing=True,
    )
    _scheduler.add_job(
        _scheduled_overdue_check,
        CronTrigger(hour=18, minute=0),
        id="evening_overdue_check",
        name="每日 18 点逾期扫描",
        replace_existing=True,
    )
    _scheduler.add_job(
        _scheduled_contract_expiring,
        CronTrigger(day_of_week="mon", hour=10, minute=0),
        id="weekly_contract_expiring",
        name="每周一 10 点合同到期扫描",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(f"[cron] scheduler 启动（pid={pid}），3 个定时任务已注册")
    for job in _scheduler.get_jobs():
        logger.info(f"  - {job.id} | next: {job.next_run_time}")

    # 3. 把 jobs 列表写到 Redis（让其他 worker 的 /cron/jobs 端点能查到）
    try:
        import json as _json
        r = await get_redis()
        jobs_meta = []
        for job in _scheduler.get_jobs():
            jobs_meta.append({
                "id": job.id,
                "name": job.name,
                "nextRun": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        # 写到 redis（不带 TTL，跟着锁走；锁释放时清掉）
        await r.set("scheduler:jobs:list", _json.dumps(jobs_meta, ensure_ascii=False))
        logger.info(f"[cron] jobs 元数据已写入 redis: scheduler:jobs:list ({len(jobs_meta)} jobs)")
    except Exception as e:
        logger.warning(f"[cron] jobs 元数据写 redis 失败: {e}")

    # 4. 起续期任务
    _scheduler_lock_renew_task = asyncio.create_task(_renew_scheduler_lock_loop())


async def shutdown_scheduler():
    """关闭 scheduler + 释放锁"""
    global _scheduler, _scheduler_lock_renew_task

    # 1. 取消续期任务
    if _scheduler_lock_renew_task and not _scheduler_lock_renew_task.done():
        _scheduler_lock_renew_task.cancel()
        try:
            await _scheduler_lock_renew_task
        except asyncio.CancelledError:
            pass
        _scheduler_lock_renew_task = None

    # 2. 停 scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("[cron] scheduler 已停止")

    # 3. 释放锁
    await _release_scheduler_lock()


async def _scheduled_all_checks():
    """scheduler 包装：跑全量"""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        r1 = await run_overdue_check(db)
        r2 = await run_upcoming_due(db)
        r3 = await run_contract_expiring(db)
        total = r1["alerted"] + r2["alerted"] + r3["alerted"]
        logger.info(f"[cron] scheduled all_checks: {r1['alerted']}+{r2['alerted']}+{r3['alerted']}={total} 条提醒")


async def _scheduled_overdue_check():
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        r = await run_overdue_check(db)
        logger.info(f"[cron] scheduled overdue_check: {r['alerted']} 条提醒")


async def _scheduled_contract_expiring():
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        r = await run_contract_expiring(db)
        logger.info(f"[cron] scheduled contract_expiring: {r['alerted']} 条提醒")


# ============================================================
# 手动端点（保持向后兼容）
# ============================================================

@router.post("/overdue-check", summary="扫描逾期回款")
async def overdue_check(db: AsyncSession = Depends(get_db)):
    r = await run_overdue_check(db)
    return {"code": 0, "data": r, "message": f"扫描完成：{r['scanned']} 笔逾期，{r['alerted']} 条提醒"}


@router.post("/upcoming-due", summary="扫描 3 天内即将到期回款")
async def upcoming_due(db: AsyncSession = Depends(get_db)):
    r = await run_upcoming_due(db)
    return {"code": 0, "data": r, "message": f"扫描完成：{r['scanned']} 笔即将到期，{r['alerted']} 条提醒"}


@router.post("/contract-expiring", summary="扫描 30 天内即将到期合同")
async def contract_expiring(db: AsyncSession = Depends(get_db)):
    r = await run_contract_expiring(db)
    return {"code": 0, "data": r, "message": f"扫描完成：{r['scanned']} 份合同即将到期，{r['alerted']} 条提醒"}


@router.post("/all", summary="一键跑全部检查")
async def all_checks(db: AsyncSession = Depends(get_db)):
    r1 = await run_overdue_check(db)
    r2 = await run_upcoming_due(db)
    r3 = await run_contract_expiring(db)
    total = r1["alerted"] + r2["alerted"] + r3["alerted"]
    return {
        "code": 0,
        "data": {
            "overdue": r1,
            "upcoming": r2,
            "expiring": r3,
            "total": total,
        },
        "message": f"一键检查完成：{total} 条提醒",
    }


@router.get("/jobs", summary="查看定时任务列表")
async def list_jobs():
    """前端 Dashboard 顶部"定时任务"小卡片可调
    R6.5.2 修复：4 worker 模式下，从 Redis 锁判断 running（不是查本地 _scheduler）
    抢到锁的 worker 持有锁，其他 worker 查不到自己的 _scheduler → 报 running: false
    修法：查 Redis 锁存在 = running，jobs 列表从抢到锁的 worker 写到 Redis
    """
    # 1. 查 Redis 锁
    try:
        r = await get_redis()
        lock_owner = await r.get(SCHEDULER_LOCK_KEY)
    except Exception as e:
        logger.warning(f"[cron] jobs 端点查锁失败: {e}")
        lock_owner = None

    if not lock_owner:
        return {"code": 0, "data": {"running": False, "jobs": []}}

    # 2. 锁存在 = running，从 Redis 读 jobs 元数据
    # 抢到锁的 worker 把 job 信息写到 key "scheduler:jobs:list"
    jobs_raw = await r.get("scheduler:jobs:list")
    if jobs_raw:
        import json
        try:
            jobs = json.loads(jobs_raw)
            return {"code": 0, "data": {"running": True, "jobs": jobs, "lockOwner": lock_owner[:8]}}
        except Exception:
            pass

    # 3. 兜底：本地 _scheduler（如果当前 worker 抢到锁）
    if _scheduler is not None:
        jobs = []
        for job in _scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "nextRun": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return {"code": 0, "data": {"running": True, "jobs": jobs}}

    # 4. 锁存在但没 jobs 元数据（启动中）—— 返回 running: true + 空 jobs
    return {"code": 0, "data": {"running": True, "jobs": [], "lockOwner": lock_owner[:8]}}
