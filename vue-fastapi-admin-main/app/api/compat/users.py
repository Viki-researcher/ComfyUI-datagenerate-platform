from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from tortoise.expressions import Q

from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependAuth, DependPermission
from app.models.admin import Role, User
from app.schemas.base import Success

router = APIRouter(prefix="/user", tags=["用户模块"])


def _map_role_codes(user: User, roles: list[Role]) -> list[str]:
    if user.is_superuser:
        return ["R_SUPER"]
    # 兼容前端示例用的角色码；其余角色用 id 兜底，避免前端空角色导致 v-roles 全部失效
    result: list[str] = []
    for r in roles:
        if r.name in ("管理员", "admin", "Admin"):
            result.append("R_ADMIN")
        elif r.name in ("普通用户", "user", "User"):
            result.append("R_USER")
        else:
            result.append(f"R_{r.id}")
    return sorted(set(result))


@router.get("/info", summary="用户信息（兼容 art-design-pro）", dependencies=[DependAuth])
async def get_user_info():
    user_id = CTX_USER_ID.get()
    user = await User.filter(id=user_id).first()
    roles: list[Role] = await user.roles

    data = {
        "buttons": [],
        "roles": _map_role_codes(user, roles),
        "userId": user.id,
        "userName": user.username,
        "email": user.email,
        "avatar": "https://avatars.githubusercontent.com/u/54677442?v=4",
    }
    return Success(data=data)


@router.get("/list", summary="用户列表（兼容 art-design-pro）", dependencies=[DependPermission])
async def list_users(
    current: int = Query(1, ge=1, description="当前页"),
    size: int = Query(20, ge=1, le=200, description="每页数量"),
    userName: str | None = Query(None, description="用户名"),
    userEmail: str | None = Query(None, description="邮箱"),
    userPhone: str | None = Query(None, description="手机号"),
    status: str | None = Query(None, description="状态：'1'在线(启用)；其他视为禁用"),
):
    q = Q()
    if userName:
        q &= Q(username__contains=userName)
    if userEmail:
        q &= Q(email__contains=userEmail)
    if userPhone:
        q &= Q(phone__contains=userPhone)
    if status is not None:
        if str(status) == "1":
            q &= Q(is_active=True)
        else:
            q &= Q(is_active=False)

    total = await User.filter(q).count()
    rows = (
        await User.filter(q)
        .order_by("-id")
        .offset((current - 1) * size)
        .limit(size)
        .all()
    )

    records = []
    for u in rows:
        u_roles: list[Role] = await u.roles
        role_codes = _map_role_codes(u, u_roles)
        records.append(
            {
                "id": u.id,
                "avatar": "https://avatars.githubusercontent.com/u/54677442?v=4",
                "status": "1" if u.is_active else "4",
                "userName": u.username,
                "userGender": "",
                "nickName": u.alias or "",
                "userPhone": u.phone or "",
                "userEmail": u.email,
                "userRoles": role_codes,
                "createBy": "",
                "createTime": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else "",
                "updateBy": "",
                "updateTime": u.updated_at.strftime("%Y-%m-%d %H:%M:%S") if u.updated_at else "",
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

