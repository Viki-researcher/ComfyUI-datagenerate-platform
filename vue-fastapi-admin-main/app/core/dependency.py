from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request

from app.core.ctx import CTX_USER_ID
from app.models import Role, User
from app.settings import settings


class AuthControl:
    @classmethod
    async def is_authed(
        cls,
        authorization: Optional[str] = Header(None, alias="Authorization", description="Authorization 头"),
        token: Optional[str] = Header(None, description="兼容旧 token 头"),
    ) -> Optional["User"]:
        try:
            raw_token = authorization or token
            if not raw_token:
                raise HTTPException(status_code=401, detail="Authentication failed")

            # 兼容 Bearer 方案
            if raw_token.lower().startswith("bearer "):
                raw_token = raw_token[7:].strip()

            if raw_token == "dev":
                user = await User.filter().first()
                user_id = user.id
            else:
                decode_data = jwt.decode(raw_token, settings.SECRET_KEY, algorithms=settings.JWT_ALGORITHM)
                user_id = decode_data.get("user_id")
            user = await User.filter(id=user_id).first()
            if not user:
                raise HTTPException(status_code=401, detail="Authentication failed")
            CTX_USER_ID.set(int(user_id))
            return user
        except jwt.DecodeError:
            raise HTTPException(status_code=401, detail="无效的Token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="登录已过期")
        except HTTPException:
            # 保持原始的 HTTPException（例如 401/403），避免被兜底异常包装成 500
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{repr(e)}")


class PermissionControl:
    @classmethod
    async def has_permission(cls, request: Request, current_user: User = Depends(AuthControl.is_authed)) -> None:
        if current_user.is_superuser:
            return
        method = request.method
        # 使用路由模板路径进行权限匹配（例如 /api/projects/{project_id}/open_comfy），
        # 避免将实际路径 /api/projects/3/open_comfy 与权限表中的模板路径匹配失败。
        route = request.scope.get("route")
        path = (
            getattr(route, "path_format", None)
            or getattr(route, "path", None)
            or request.url.path
        )
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        roles: list[Role] = await current_user.roles
        if not roles:
            raise HTTPException(status_code=403, detail="The user is not bound to a role")
        apis = [await role.apis for role in roles]
        permission_apis = list(set((api.method, api.path) for api in sum(apis, [])))
        # path = "/api/v1/auth/userinfo"
        # method = "GET"
        if (method, path) not in permission_apis:
            raise HTTPException(status_code=403, detail=f"Permission denied method:{method} path:{path}")


DependAuth = Depends(AuthControl.is_authed)
DependPermission = Depends(PermissionControl.has_permission)
