from fastapi import APIRouter

from .v1 import v1_router
from .compat import compat_router
from .internal import internal_router

api_router = APIRouter()
api_router.include_router(v1_router, prefix="/v1")
api_router.include_router(compat_router)
api_router.include_router(internal_router)


__all__ = ["api_router"]
