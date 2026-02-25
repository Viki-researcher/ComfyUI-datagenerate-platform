from __future__ import annotations

import time
from collections import deque
from typing import Optional

import psutil
from fastapi import APIRouter

from app.core.dependency import DependPermission
from app.schemas.base import Success

router = APIRouter(prefix="/server", tags=["监控模块"])

# 历史数据缓存（保留最近60个数据点，约5分钟数据）
HISTORY_LENGTH = 60
_history_data = deque(maxlen=HISTORY_LENGTH)


def _get_gpu_info() -> Optional[dict]:
    """获取GPU信息（如果有nvidia-smi）"""
    try:
        import subprocess
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits"
            ],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            gpus = []
            for line in lines:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    gpus.append({
                        "utilization": float(parts[0]),
                        "memory_used": float(parts[1]),
                        "memory_total": float(parts[2])
                    })
            return {"available": True, "gpus": gpus}
    except Exception:
        pass
    return {"available": False, "gpus": []}


@router.get("/stats", summary="服务器资源监控(只读)", dependencies=[DependPermission])
async def server_stats():
    cpu = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory().percent
    swap = psutil.swap_memory().percent
    disk = psutil.disk_usage("/").percent
    gpu = _get_gpu_info()

    # 记录历史数据
    _history_data.append({
        "timestamp": int(time.time()),
        "cpu": float(cpu),
        "memory": float(memory),
        "swap": float(swap),
        "disk": float(disk),
        "gpu": gpu
    })

    return Success(
        data={
            "cpu": float(cpu),
            "memory": float(memory),
            "swap": float(swap),
            "disk": float(disk),
            "gpu": gpu,
            "history": list(_history_data)
        }
    )


@router.get("/stats/history", summary="服务器历史监控数据", dependencies=[DependPermission])
async def server_stats_history():
    """获取历史监控数据"""
    return Success(
        data={
            "history": list(_history_data),
            "max_points": HISTORY_LENGTH
        }
    )

