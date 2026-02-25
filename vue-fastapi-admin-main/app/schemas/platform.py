from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., description="项目名称")
    code: str = Field(..., description="项目号")
    note: Optional[str] = Field(None, description="备注")


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, description="项目名称")
    note: Optional[str] = Field(None, description="备注")


class ProjectOut(BaseModel):
    id: int
    name: str
    code: str
    note: Optional[str] = None
    owner_user_id: int
    create_time: str
    update_time: str


class OpenComfyOut(BaseModel):
    comfy_url: str


class GenerationLogCreate(BaseModel):
    project_id: int = Field(..., description="项目ID")
    timestamp: Optional[datetime] = Field(None, description="生成时间(可选，默认当前时间)")
    status: str = Field(..., description="状态(成功/失败等)")
    prompt_id: Optional[str] = Field(None, description="ComfyUI prompt_id(可选)")
    concurrent_id: Optional[int] = Field(None, description="并发ID")
    details: Optional[Any] = Field(None, description="详情(错误/耗时等)")


class StatsPoint(BaseModel):
    key: str
    count: int

