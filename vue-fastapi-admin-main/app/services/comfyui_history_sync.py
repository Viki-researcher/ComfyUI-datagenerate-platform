from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx

from app.log import logger
from app.models.platform import ComfyUIService, GenerationLog


async def _fetch_history(comfy_url: str, *, max_items: int = 50) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{comfy_url}/history", params={"max_items": max_items})
        r.raise_for_status()
        return r.json()


def _map_status(history_item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    status = history_item.get("status") or {}
    status_str = status.get("status_str") or ""
    if status_str == "success":
        return "成功", {"status": status}
    if status_str == "error":
        return "失败", {"status": status}
    return "未知", {"status": status}


async def sync_once(*, max_items: int = 50) -> int:
    """
    从所有在线服务拉取最新 history，并将新 prompt_id 写入 generation_logs。
    返回本次新增的日志条数。
    """
    services = await ComfyUIService.filter(status="online").all()
    created = 0
    for s in services:
        if not s.comfy_url:
            continue
        try:
            history = await _fetch_history(s.comfy_url, max_items=max_items)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[ComfyUI] history fetch failed: {s.comfy_url} ({e})")
            continue

        for prompt_id, item in history.items():
            if not prompt_id:
                continue
            exists = await GenerationLog.filter(project_id=s.project_id, prompt_id=str(prompt_id)).exists()
            if exists:
                continue

            status_str, extra = _map_status(item if isinstance(item, dict) else {})
            details = {
                "prompt_id": str(prompt_id),
                "comfy_url": s.comfy_url,
                "history": item,
                **extra,
            }
            await GenerationLog.create(
                user_id=s.user_id,
                project_id=s.project_id,
                timestamp=datetime.now(),
                status=status_str,
                prompt_id=str(prompt_id),
                concurrent_id=None,
                details=details,
            )
            created += 1
    return created


async def sync_loop(stop_event: asyncio.Event, *, interval_seconds: int = 10) -> None:
    """
    后台轮询 ComfyUI history 并自动写入 generation_logs。
    """
    if interval_seconds <= 0:
        logger.warning("[ComfyUI] history sync disabled (interval<=0)")
        return

    while not stop_event.is_set():
        try:
            n = await sync_once()
            if n:
                logger.info(f"[ComfyUI] history synced: +{n}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[ComfyUI] history sync error: {e}")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except TimeoutError:
            pass

