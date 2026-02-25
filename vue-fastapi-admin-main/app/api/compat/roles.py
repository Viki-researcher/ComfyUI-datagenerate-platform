from fastapi import APIRouter, Query
from tortoise.expressions import Q

from app.core.dependency import DependPermission
from app.models.admin import Role
from app.schemas.base import Success

router = APIRouter(prefix="/role", tags=["角色模块"])


@router.get("/list", summary="角色列表（兼容 art-design-pro）", dependencies=[DependPermission])
async def list_roles(
    current: int = Query(1, ge=1, description="当前页"),
    size: int = Query(20, ge=1, le=200, description="每页数量"),
    roleName: str | None = Query(None, description="角色名称"),
):
    q = Q()
    if roleName:
        q &= Q(name__contains=roleName)

    total = await Role.filter(q).count()
    rows = (
        await Role.filter(q)
        .order_by("-id")
        .offset((current - 1) * size)
        .limit(size)
        .all()
    )

    records = []
    for r in rows:
        records.append(
            {
                "roleId": r.id,
                "roleName": r.name,
                "roleCode": f"R_{r.id}",
                "description": r.desc or "",
                "enabled": True,
                "createTime": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
            }
        )

    return Success(
        data={
            "records": records,
            "current": current,
            "size": size,
            "total": total,
        }
    )

