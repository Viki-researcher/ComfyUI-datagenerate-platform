from __future__ import annotations

import asyncio
import os
import signal
import socket
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Tuple

import httpx
import yaml

from app.log import logger
from app.models.platform import ComfyUIService
from app.settings.config import settings


@dataclass(frozen=True)
class ComfyUIConfig:
    repo_path: Path
    python_exec: str
    listen: str
    internal_host: str
    port_start: int
    port_end: int
    instance_base_dir: Path
    log_dir: Path
    startup_timeout_seconds: int
    heartbeat_interval_seconds: int


def _parse_port_range(s: str) -> Tuple[int, int]:
    left, right = s.split("-", 1)
    a, b = int(left.strip()), int(right.strip())
    if a <= 0 or b <= 0 or a > b:
        raise ValueError(f"invalid COMFYUI_PORT_RANGE: {s}")
    return a, b


def _derive_internal_host(listen: str) -> str:
    """
    ComfyUI 进程的监听地址可能是 0.0.0.0，但后端内部健康检查/拉取 history 需要可连接的 host。
    """
    if settings.COMFYUI_INTERNAL_HOST:
        return settings.COMFYUI_INTERNAL_HOST
    if listen in ("0.0.0.0", "::", "[::]"):
        return "127.0.0.1"
    return listen


def load_comfyui_config() -> ComfyUIConfig:
    if not settings.COMFYUI_REPO_PATH:
        raise RuntimeError("COMFYUI_REPO_PATH is empty")
    if not settings.COMFYUI_PYTHON:
        raise RuntimeError("COMFYUI_PYTHON is empty")

    repo_path = Path(settings.COMFYUI_REPO_PATH).expanduser().resolve()
    if not repo_path.exists():
        raise RuntimeError(f"COMFYUI_REPO_PATH not found: {repo_path}")
    if not (repo_path / "main.py").exists():
        raise RuntimeError(f"ComfyUI main.py not found in: {repo_path}")

    port_start, port_end = _parse_port_range(settings.COMFYUI_PORT_RANGE)

    instance_base_dir = Path(settings.COMFYUI_INSTANCE_BASE_DIR).expanduser()
    if not instance_base_dir.is_absolute():
        instance_base_dir = Path(settings.BASE_DIR) / instance_base_dir

    log_dir = Path(settings.COMFYUI_LOG_DIR).expanduser()
    if not log_dir.is_absolute():
        log_dir = Path(settings.BASE_DIR) / log_dir

    return ComfyUIConfig(
        repo_path=repo_path,
        python_exec=settings.COMFYUI_PYTHON,
        listen=settings.COMFYUI_LISTEN,
        internal_host=_derive_internal_host(settings.COMFYUI_LISTEN),
        port_start=port_start,
        port_end=port_end,
        instance_base_dir=instance_base_dir,
        log_dir=log_dir,
        startup_timeout_seconds=int(settings.COMFYUI_STARTUP_TIMEOUT_SECONDS),
        heartbeat_interval_seconds=int(settings.COMFYUI_HEARTBEAT_INTERVAL_SECONDS),
    )


def _pick_free_port(start: int, end: int) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No free port available")


def _instance_dir(cfg: ComfyUIConfig, user_id: int, project_id: int) -> Path:
    return cfg.instance_base_dir / f"u{user_id}" / f"p{project_id}"


def _ensure_instance_links(cfg: ComfyUIConfig, inst_dir: Path) -> None:
    """
    ComfyUI 使用 --base-directory 后，会在实例目录下读取 custom_nodes/models 等。
    为了复用仓库内资源，这里在实例目录建立软链接：
    - {inst_dir}/custom_nodes -> {repo_path}/custom_nodes
    - {inst_dir}/models -> {repo_path}/models
    """
    inst_dir.mkdir(parents=True, exist_ok=True)
    for d in ("output", "temp", "input", "user"):
        (inst_dir / d).mkdir(parents=True, exist_ok=True)
    for name in ("custom_nodes", "models"):
        src = cfg.repo_path / name
        dst = inst_dir / name
        if dst.exists() or dst.is_symlink():
            continue
        if not src.exists():
            raise RuntimeError(f"ComfyUI repo missing {name}: {src}")
        try:
            dst.symlink_to(src, target_is_directory=True)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"failed to create symlink: {dst} -> {src} ({e})") from e


def _write_extra_model_paths(cfg: ComfyUIConfig, inst_dir: Path) -> Path:
    data = {
        "comfyui": {
            "base_path": str(cfg.repo_path),
            "custom_nodes": "custom_nodes",
            "checkpoints": "models/checkpoints",
            "text_encoders": "models/text_encoders",
            "clip_vision": "models/clip_vision",
            "configs": "models/configs",
            "controlnet": "models/controlnet",
            "diffusion_models": "models/diffusion_models",
            "embeddings": "models/embeddings",
            "loras": "models/loras",
            "upscale_models": "models/upscale_models",
            "vae": "models/vae",
        }
    }
    path = inst_dir / "extra_model_paths.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


async def is_healthy(comfy_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            r = await client.get(f"{comfy_url}/system_stats")
            return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False


def stop_pid(pid: int, *, timeout_seconds: int = 10) -> None:
    if pid <= 0:
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.2)

    try:
        os.killpg(pid, signal.SIGKILL)
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            return


def _should_force_cpu(cfg: ComfyUIConfig) -> bool:
    if settings.COMFYUI_FORCE_CPU:
        return True
    try:
        out = subprocess.check_output(
            [cfg.python_exec, "-c", "import torch; print(int(torch.cuda.is_available()))"],
            stderr=subprocess.STDOUT,
            timeout=10,
        )
        return out.decode().strip() != "1"
    except Exception:
        return True


async def start_instance(user_id: int, project_id: int) -> dict:
    cfg = load_comfyui_config()
    port = _pick_free_port(cfg.port_start, cfg.port_end)
    # 注意：cfg.listen 可能是 0.0.0.0（用于对外监听），内部健康检查应使用可连接的 internal_host
    comfy_url = f"http://{cfg.internal_host}:{port}"

    inst_dir = _instance_dir(cfg, user_id, project_id)
    _ensure_instance_links(cfg, inst_dir)
    extra_paths = _write_extra_model_paths(cfg, inst_dir)

    cfg.log_dir.mkdir(parents=True, exist_ok=True)
    log_path = cfg.log_dir / f"comfy_u{user_id}_p{project_id}_{port}.log"

    cmd = [
        cfg.python_exec,
        str(cfg.repo_path / "main.py"),
        "--listen",
        cfg.listen,
        "--port",
        str(port),
        "--disable-auto-launch",
        "--base-directory",
        str(inst_dir),
        "--extra-model-paths-config",
        str(extra_paths),
    ]
    if _should_force_cpu(cfg):
        cmd.append("--cpu")

    logger.info(f"[ComfyUI] starting: {' '.join(cmd)}")
    with open(log_path, "ab", buffering=0) as f:
        env = os.environ.copy()
        if settings.PLATFORM_CALLBACK_URL:
            env["PLATFORM_CALLBACK_URL"] = settings.PLATFORM_CALLBACK_URL
        if settings.PLATFORM_INTERNAL_SECRET:
            env["PLATFORM_CALLBACK_SECRET"] = settings.PLATFORM_INTERNAL_SECRET
        env["PLATFORM_PROJECT_ID"] = str(project_id)
        proc = subprocess.Popen(
            cmd,
            cwd=str(cfg.repo_path),
            stdout=f,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )

    deadline = time.time() + max(5, cfg.startup_timeout_seconds)
    while time.time() < deadline:
        if await is_healthy(comfy_url):
            return {
                "port": port,
                "comfy_url": comfy_url,
                "pid": proc.pid,
                "base_dir": str(inst_dir),
                "log_path": str(log_path),
            }
        await asyncio.sleep(1)

    stop_pid(proc.pid)
    raise RuntimeError("ComfyUI start timeout")


async def ensure_comfyui_service(user_id: int, project_id: int) -> ComfyUIService:
    existing = await ComfyUIService.filter(project_id=project_id).first()
    if existing and existing.status == "online" and existing.comfy_url:
        if await is_healthy(existing.comfy_url):
            existing.last_heartbeat = datetime.now()
            await existing.save()
            return existing

    if existing and existing.pid:
        try:
            stop_pid(int(existing.pid))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[ComfyUI] stop old pid failed: {existing.pid} ({e})")

    info = await start_instance(user_id=user_id, project_id=project_id)

    if existing:
        await existing.update_from_dict(
            dict(
                port=info["port"],
                status="online",
                comfy_url=info["comfy_url"],
                last_heartbeat=datetime.now(),
                pid=info["pid"],
                base_dir=info["base_dir"],
                log_path=info["log_path"],
                start_time=datetime.now(),
            )
        ).save()
        return existing

    return await ComfyUIService.create(
        user_id=user_id,
        project_id=project_id,
        port=info["port"],
        status="online",
        comfy_url=info["comfy_url"],
        last_heartbeat=datetime.now(),
        pid=info["pid"],
        base_dir=info["base_dir"],
        log_path=info["log_path"],
        start_time=datetime.now(),
    )


async def heartbeat_once() -> None:
    rows = await ComfyUIService.all()
    for s in rows:
        if not s.comfy_url:
            continue
        ok = await is_healthy(s.comfy_url)
        if ok:
            if s.status != "online":
                s.status = "online"
            s.last_heartbeat = datetime.now()
            await s.save()
        else:
            if s.status != "offline":
                s.status = "offline"
                await s.save()


async def heartbeat_loop(stop_event: asyncio.Event) -> None:
    try:
        cfg = load_comfyui_config()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ComfyUI] heartbeat disabled (config invalid): {e}")
        return

    interval = int(cfg.heartbeat_interval_seconds)
    if interval <= 0:
        logger.warning("[ComfyUI] heartbeat disabled (interval<=0)")
        return

    while not stop_event.is_set():
        try:
            await heartbeat_once()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[ComfyUI] heartbeat error: {e}")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            pass

