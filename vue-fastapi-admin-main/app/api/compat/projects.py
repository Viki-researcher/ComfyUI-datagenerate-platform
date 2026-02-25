from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Request
from tortoise.expressions import Q

from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependPermission
from app.models import User
from app.models.platform import ComfyUIService, Project
from app.services.comfyui_manager import ensure_comfyui_service, stop_pid
from app.schemas.base import Fail, Success
from app.schemas.platform import OpenComfyOut, ProjectCreate, ProjectUpdate
from app.settings.config import settings

router = APIRouter(prefix="/projects", tags=["项目模块"])


def _now_str(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _get_public_comfy_url(*, port: int, request: Request) -> str:
    """
    返回给前端打开的 ComfyUI 地址。
    - 优先使用 COMFYUI_PUBLIC_BASE_URL
    - 否则从请求头推导（X-Forwarded-Host / Host / request.url）
    """
    base = (settings.COMFYUI_PUBLIC_BASE_URL or "").strip().rstrip("/")
    if base:
        # 支持两种写法：
        # 1) http://10.10.1.199
        # 2) 10.10.1.199
        if "://" not in base:
            base = f"http://{base}"
        from urllib.parse import urlparse

        u = urlparse(base)
        if not u.hostname:
            return f"http://127.0.0.1:{port}"
        scheme = u.scheme or "http"
        return f"{scheme}://{u.hostname}:{port}"

    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",", 1)[0].strip()
    host = forwarded_host or (request.headers.get("host") or "").strip() or (request.url.hostname or "")
    proto = (request.headers.get("x-forwarded-proto") or "").split(",", 1)[0].strip() or request.url.scheme or "http"

    # host 可能包含端口（如 10.10.1.199:3006），这里只取 hostname 部分
    hostname = ""
    if host.startswith("[") and "]" in host:
        hostname = host[1 : host.find("]")]
    else:
        hostname = host.split(":", 1)[0]
    hostname = hostname or "127.0.0.1"

    return f"{proto}://{hostname}:{port}"


@router.post("", summary="新建项目", dependencies=[DependPermission])
async def create_project(req_in: ProjectCreate):
    user_id = CTX_USER_ID.get()

    exists = await Project.filter(code=req_in.code).exists()
    if exists:
        return Fail(code=400, msg="项目号已存在")

    obj = await Project.create(
        name=req_in.name,
        code=req_in.code,
        note=req_in.note,
        owner_user_id=user_id,
    )
    owner = await User.filter(id=user_id).first()

    return Success(
        data={
            "id": obj.id,
            "name": obj.name,
            "code": obj.code,
            "note": obj.note,
            "owner_user_id": obj.owner_user_id,
            "owner_user_name": owner.username if owner else "",
            "create_time": _now_str(obj.created_at),
            "update_time": _now_str(obj.updated_at),
        }
    )


@router.get("", summary="项目列表", dependencies=[DependPermission])
async def list_projects(
    name: str | None = Query(None, description="项目名称"),
    code: str | None = Query(None, description="项目号"),
):
    q = Q()
    if name:
        q &= Q(name__contains=name)
    if code:
        q &= Q(code__contains=code)

    rows = await Project.filter(q).order_by("-id").all()
    owner_ids = list({int(p.owner_user_id) for p in rows if p.owner_user_id is not None})
    owner_rows = await User.filter(id__in=owner_ids).values("id", "username") if owner_ids else []
    owner_map = {int(r["id"]): r["username"] for r in owner_rows}
    data = [
        {
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "note": p.note,
            "owner_user_id": p.owner_user_id,
            "owner_user_name": owner_map.get(int(p.owner_user_id), ""),
            "create_time": _now_str(p.created_at),
            "update_time": _now_str(p.updated_at),
        }
        for p in rows
    ]
    return Success(data=data)


@router.put("/{project_id}", summary="更新项目", dependencies=[DependPermission])
async def update_project(project_id: int, req_in: ProjectUpdate):
    user_id = CTX_USER_ID.get()
    project = await Project.filter(id=project_id).first()
    if not project:
        return Fail(code=404, msg="项目不存在")
    if project.owner_user_id != user_id:
        return Fail(code=403, msg="无操作权限")

    update_dict = req_in.model_dump(exclude_unset=True)
    if update_dict:
        await project.update_from_dict(update_dict).save()
    owner = await User.filter(id=project.owner_user_id).first()

    return Success(
        data={
            "id": project.id,
            "name": project.name,
            "code": project.code,
            "note": project.note,
            "owner_user_id": project.owner_user_id,
            "owner_user_name": owner.username if owner else "",
            "create_time": _now_str(project.created_at),
            "update_time": _now_str(project.updated_at),
        }
    )


@router.delete("/{project_id}", summary="删除项目", dependencies=[DependPermission])
async def delete_project(project_id: int):
    user_id = CTX_USER_ID.get()
    project = await Project.filter(id=project_id).first()
    if not project:
        return Fail(code=404, msg="项目不存在")
    if project.owner_user_id != user_id:
        return Fail(code=403, msg="无操作权限")

    svc = await ComfyUIService.filter(project_id=project_id).first()
    if svc and svc.pid:
        stop_pid(int(svc.pid))
    await ComfyUIService.filter(project_id=project_id).delete()
    await Project.filter(id=project_id).delete()
    return Success(msg="Deleted")


@router.post("/{project_id}/open_comfy", summary="打开/启动 ComfyUI 服务", dependencies=[DependPermission])
async def open_comfy(project_id: int, request: Request):
    user_id = CTX_USER_ID.get()
    project = await Project.filter(id=project_id).first()
    if not project:
        return Fail(code=404, msg="项目不存在")

    # 资源级权限：项目所有者才能启动/打开
    if project.owner_user_id != user_id:
        return Fail(code=403, msg="无操作权限")

    # 若已存在服务记录：只能 owner 访问（双保险）
    existing = await ComfyUIService.filter(project_id=project_id).first()
    if existing and existing.user_id != user_id:
        return Fail(code=403, msg="无操作权限")

    try:
        svc = await ensure_comfyui_service(user_id=user_id, project_id=project_id)
    except Exception as e:  # noqa: BLE001
        return Fail(code=500, msg=f"启动 ComfyUI 失败：{e}")

    public_url = _get_public_comfy_url(port=int(svc.port), request=request)
    return Success(data=OpenComfyOut(comfy_url=public_url).model_dump())

