"""
SSE 实时通信：基于 Redis Pub/Sub 的事件总线
"""
import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from loguru import logger
import redis.asyncio as redis

from app.config import settings
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException


sse_router = APIRouter()


# Redis 连接池（全局单例）
_redis_pool: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def publish_event(channel: str, event_type: str, data: dict):
    """发布 SSE 事件到 Redis 频道"""
    r = await get_redis()
    # data 中如果有 type 字段，避免覆盖 event_type
    safe_data = {k: v for k, v in data.items() if k != "type"}
    payload = json.dumps({"type": event_type, **safe_data}, ensure_ascii=False, default=str)
    await r.publish(channel, payload)


async def event_stream(channel: str) -> AsyncGenerator[str, None]:
    """SSE 事件流生成器"""
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)

    # 1. 用 Queue 缓冲 redis 消息（避免 listen() 在 async generator 里 yield 阻塞）
    queue: asyncio.Queue = asyncio.Queue()

    async def consume():
        """后台任务：持续 listen redis pubsub，推到 queue"""
        try:
            async for message in pubsub.listen():
                logger.info(f"[SSE] pubsub 收到: {message.get('type')} data={str(message.get('data'))[:80]}")
                if message.get("type") == "message":
                    await queue.put(message["data"])
        except Exception as e:
            logger.error(f"[SSE] consume 异常: {e}")

    consume_task = asyncio.create_task(consume())
    # 给 consume_task 一点时间进入 listen() 循环
    await asyncio.sleep(0.1)

    # 2. 连接成功
    yield f"event: connected\ndata: {json.dumps({'channel': channel}, ensure_ascii=False)}\n\n"

    try:
        # 3. 主循环：yield queue 中的消息（带超时心跳）
        while True:
            try:
                # 短超时，让出控制权给 consume_task
                raw = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # 让出控制权
                await asyncio.sleep(0.01)
                continue
            try:
                data = json.loads(raw)
                event_type = data.pop("type", "progress")
                out = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
                logger.info(f"[SSE] YIELD {event_type}: {out[:80]}")
                yield out
                logger.info(f"[SSE] AFTER YIELD {event_type}")
                # yield 后让出
                await asyncio.sleep(0)
            except json.JSONDecodeError:
                continue
    finally:
        consume_task.cancel()
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception:
            pass


# ===== 路由 =====

@sse_router.get("/{channel:path}")
async def sse_endpoint(
    channel: str,
    token: str = Query(..., description="JWT token（EventSource 不支持 header）"),
):
    """
    通用 SSE 端点
    用法：/sse/invoice/batch/BATCH-001?token=xxx
    """
    # 鉴权
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException()
    except UnauthorizedException:
        raise
    except Exception:
        raise UnauthorizedException("Token 无效")

    full_channel = f"sse:{channel}"

    return StreamingResponse(
        event_stream(full_channel),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ===== 便捷发布函数 =====

async def publish_batch_progress(batch_id: str, **data):
    """发布批量任务进度"""
    await publish_event(f"sse:invoice/batch/{batch_id}", "progress", data)


async def publish_batch_item_done(batch_id: str, file_id: str, invoice_id: int, confidence: float):
    """批量任务单条完成"""
    await publish_event(
        f"sse:invoice/batch/{batch_id}",
        "item_done",
        {"fileId": file_id, "invoiceId": invoice_id, "confidence": confidence}
    )


async def publish_batch_summary(batch_id: str, summary: dict):
    """批量任务汇总"""
    await publish_event(f"sse:invoice/batch/{batch_id}", "summary", summary)


async def publish_batch_completed(batch_id: str, finished_at: str):
    """批量任务完成"""
    await publish_event(
        f"sse:invoice/batch/{batch_id}",
        "completed",
        {"batchId": batch_id, "finishedAt": finished_at}
    )
