from fastapi import APIRouter

from .auth import router as auth_router
from .logs import router as logs_router
from .projects import router as projects_router
from .roles import router as roles_router
from .server import router as server_router
from .system import router as system_router
from .stats import router as stats_router
from .users import router as users_router

compat_router = APIRouter()

# 兼容 art-design-pro 前端契约（不带 /v1 前缀）
compat_router.include_router(auth_router)
compat_router.include_router(users_router)
compat_router.include_router(roles_router)
compat_router.include_router(system_router)
compat_router.include_router(projects_router)
compat_router.include_router(logs_router)
compat_router.include_router(stats_router)
compat_router.include_router(server_router)

__all__ = ["compat_router"]

