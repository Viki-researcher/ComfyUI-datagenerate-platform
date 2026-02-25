from __future__ import annotations

from collections import Counter
from datetime import datetime
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from tortoise.expressions import Q

from app.core.dependency import DependPermission
from app.models.admin import User
from app.models.platform import GenerationLog, Project
from app.schemas.base import Success

router = APIRouter(tags=["统计模块"])


def _parse_date(s: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError("invalid date format")


@router.get("/stats", summary="统计聚合", dependencies=[DependPermission])
async def get_stats(
    dimension: str = Query("day", description="维度：day/project/user"),
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    project_id: int | None = Query(None, description="项目ID(可选)"),
    user_id: int | None = Query(None, description="用户ID(可选)"),
    status: str | None = Query(None, description="状态(可选，如 成功/失败)"),
):
    q = Q()
    if start_date:
        q &= Q(timestamp__gte=_parse_date(start_date))
    if end_date:
        q &= Q(timestamp__lte=_parse_date(end_date))
    if project_id is not None:
        q &= Q(project_id=project_id)
    if user_id is not None:
        q &= Q(user_id=user_id)
    if status:
        q &= Q(status=status)

    rows = await GenerationLog.filter(q).all()

    keys: list[str] = []
    if dimension == "day":
        keys = [r.timestamp.strftime("%Y-%m-%d") for r in rows]
        counter = Counter(keys)
        data = [{"date": k, "count": counter[k]} for k in sorted(counter.keys())]
    elif dimension == "project":
        keys = [str(r.project_id) for r in rows]
        counter = Counter(keys)
        ids = [int(k) for k in counter.keys()]
        projects = {p.id: p for p in await Project.filter(id__in=ids).all()} if ids else {}
        data = [
            {
                "project_id": int(k),
                "project_name": projects.get(int(k)).name if int(k) in projects else "",
                "count": counter[k],
            }
            for k in sorted(counter.keys(), key=int)
        ]
    elif dimension == "user":
        keys = [str(r.user_id) for r in rows]
        counter = Counter(keys)
        ids = [int(k) for k in counter.keys()]
        users = {u.id: u for u in await User.filter(id__in=ids).all()} if ids else {}
        data = [
            {
                "user_id": int(k),
                "user_name": users.get(int(k)).username if int(k) in users else "",
                "count": counter[k],
            }
            for k in sorted(counter.keys(), key=int)
        ]
    else:
        data = []

    return Success(data=data)


@router.get("/export", summary="导出统计(Excel)", dependencies=[DependPermission])
async def export_stats(
    dimension: str = Query("day", description="维度：day/project/user"),
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    project_id: int | None = Query(None, description="项目ID(可选)"),
    user_id: int | None = Query(None, description="用户ID(可选)"),
    status: str | None = Query(None, description="状态(可选，如 成功/失败)"),
):
    q = Q()
    if start_date:
        q &= Q(timestamp__gte=_parse_date(start_date))
    if end_date:
        q &= Q(timestamp__lte=_parse_date(end_date))
    if project_id is not None:
        q &= Q(project_id=project_id)
    if user_id is not None:
        q &= Q(user_id=user_id)
    if status:
        q &= Q(status=status)
    rows = await GenerationLog.filter(q).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "stats"

    if dimension == "day":
        ws.append(["date", "count"])
        counter = Counter([r.timestamp.strftime("%Y-%m-%d") for r in rows])
        for k in sorted(counter.keys()):
            ws.append([k, counter[k]])
    elif dimension == "project":
        ws.append(["project_id", "project_name", "count"])
        counter = Counter([str(r.project_id) for r in rows])
        ids = [int(k) for k in counter.keys()]
        projects = {p.id: p for p in await Project.filter(id__in=ids).all()} if ids else {}
        for k in sorted(counter.keys(), key=int):
            pid = int(k)
            ws.append([pid, projects.get(pid).name if pid in projects else "", counter[k]])
    elif dimension == "user":
        ws.append(["user_id", "user_name", "count"])
        counter = Counter([str(r.user_id) for r in rows])
        ids = [int(k) for k in counter.keys()]
        users = {u.id: u for u in await User.filter(id__in=ids).all()} if ids else {}
        for k in sorted(counter.keys(), key=int):
            uid = int(k)
            ws.append([uid, users.get(uid).username if uid in users else "", counter[k]])
    else:
        ws.append(["key", "count"])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    suffix = f"{(start_date or 'all').replace('-','')}_{(end_date or 'all').replace('-','')}"
    filename = f"stats_{dimension}_{suffix}.xlsx"
    headers = {"Content-Disposition": f'attachment; filename=\"{filename}\"'}
    return StreamingResponse(
        buf,
        headers=headers,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

