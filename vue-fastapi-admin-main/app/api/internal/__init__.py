from fastapi import APIRouter

from .comfy import router as comfy_router

internal_router = APIRouter(prefix="/internal")
internal_router.include_router(comfy_router)

__all__ = ["internal_router"]

