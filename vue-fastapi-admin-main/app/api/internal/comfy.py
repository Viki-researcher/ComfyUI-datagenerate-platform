from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from app.models.platform import ComfyUIService, GenerationLog
from app.schemas.base import Fail, Success
from app.settings.config import settings

router = APIRouter(prefix="/comfy", tags=["内部回调"])


class ComfyCallbackIn(BaseModel):
    project_id: int = Field(..., description="项目ID")
    prompt_id: Optional[str] = Field(None, description="ComfyUI prompt_id")
    status: str = Field(..., description="状态(成功/失败等)")
    concurrent_id: Optional[int] = Field(None, description="并发ID")
    details: Optional[Any] = Field(None, description="详情(错误/耗时等)")
    timestamp: Optional[datetime] = Field(None, description="生成时间(可选，默认当前时间)")


@router.post("/callback", summary="ComfyUI 生成回调（secret 校验）")
async def comfy_callback(req_in: ComfyCallbackIn, x_platform_secret: str | None = Header(default=None)):
    secret = settings.PLATFORM_INTERNAL_SECRET
    if not secret:
        return Fail(code=500, msg="PLATFORM_INTERNAL_SECRET 未配置，回调已禁用")
    if not x_platform_secret or x_platform_secret != secret:
        return Fail(code=403, msg="invalid secret")

    svc = await ComfyUIService.filter(project_id=req_in.project_id).first()
    if not svc:
        return Fail(code=404, msg="service not found")

    ts = req_in.timestamp or datetime.now()
    obj = await GenerationLog.create(
        user_id=svc.user_id,
        project_id=req_in.project_id,
        timestamp=ts,
        status=req_in.status,
        prompt_id=req_in.prompt_id,
        concurrent_id=req_in.concurrent_id,
        details=req_in.details,
    )

    return Success(
        data={
            "id": obj.id,
            "project_id": obj.project_id,
            "user_id": obj.user_id,
            "timestamp": ts.strftime(settings.DATETIME_FORMAT),
            "status": obj.status,
            "prompt_id": obj.prompt_id,
        }
    )

