from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependAuth
from app.models.admin import Api, Menu, Role, User
from app.schemas.base import Success

router = APIRouter(prefix="/v3/system", tags=["基础模块"])


def _to_component_path(component: str | None) -> str:
    if not component:
        return ""
    # 兼容旧初始化数据：后端使用 "Layout"，前端路由配置使用 "/index/index"
    if component == "Layout":
        return "/index/index"
    return component


def _build_menu_tree(menus: list[Menu]) -> list[Menu]:
    by_parent: dict[int, list[Menu]] = {}
    for m in menus:
        by_parent.setdefault(m.parent_id or 0, []).append(m)

    for lst in by_parent.values():
        lst.sort(key=lambda x: (x.order or 0, x.id))

    def build(parent_id: int) -> list[Menu]:
        children = by_parent.get(parent_id, [])
        for c in children:
            # 动态挂载 children，避免额外查询
            setattr(c, "__children__", build(c.id))
        return children

    return build(0)


async def _get_user_allowed_api_set(user: User) -> set[tuple[str, str]]:
    if user.is_superuser:
        api_objs: list[Api] = await Api.all()
        return set((api.method, api.path) for api in api_objs)

    roles: list[Role] = await user.roles
    apis = [await role.apis for role in roles]
    return set((api.method, api.path) for api in sum(apis, []))


def _extract_authlist_from_remark(remark: Any) -> list[dict[str, Any]]:
    """
    remark 约定（建议）：
    {
      "authList": [
        {"title":"新增","authMark":"add","apis":[{"method":"POST","path":"/api/projects"}]}
      ]
    }
    """
    if not isinstance(remark, dict):
        return []
    auth_list = remark.get("authList")
    if not isinstance(auth_list, list):
        return []
    result: list[dict[str, Any]] = []
    for item in auth_list:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        auth_mark = item.get("authMark")
        if isinstance(title, str) and isinstance(auth_mark, str):
            result.append(item)
    return result


def _filter_authlist_by_api_permission(
    auth_list: list[dict[str, Any]], allowed: set[tuple[str, str]]
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for item in auth_list:
        apis = item.get("apis")
        if not apis:
            filtered.append({"title": item["title"], "authMark": item["authMark"]})
            continue

        if not isinstance(apis, list):
            continue

        ok = False
        for api_item in apis:
            if not isinstance(api_item, dict):
                continue
            method = api_item.get("method")
            path = api_item.get("path")
            if isinstance(method, str) and isinstance(path, str) and (method, path) in allowed:
                ok = True
                break
        if ok:
            filtered.append({"title": item["title"], "authMark": item["authMark"]})
    return filtered


def _menu_to_app_route(menu: Menu, allowed_apis: set[tuple[str, str]]) -> dict[str, Any]:
    children: list[Menu] = getattr(menu, "__children__", [])

    auth_list_raw = _extract_authlist_from_remark(menu.remark)
    auth_list = _filter_authlist_by_api_permission(auth_list_raw, allowed_apis)

    meta: dict[str, Any] = {
        "title": menu.name,
        "icon": menu.icon,
        "isHide": bool(menu.is_hidden),
        "keepAlive": bool(menu.keepalive),
    }
    if auth_list:
        meta["authList"] = auth_list

    route: dict[str, Any] = {
        "id": menu.id,
        "path": menu.path,
        "name": f"Menu{menu.id}",
        "component": _to_component_path(menu.component),
        "redirect": menu.redirect or "",
        "meta": meta,
    }

    if children:
        route["children"] = [_menu_to_app_route(c, allowed_apis) for c in children]

    return route


@router.get("/menus", summary="菜单列表（兼容 art-design-pro）", dependencies=[DependAuth])
async def get_menus():
    user_id = CTX_USER_ID.get()
    user = await User.filter(id=user_id).first()

    if user.is_superuser:
        menus = await Menu.all()
    else:
        roles: list[Role] = await user.roles
        menus: list[Menu] = []
        for role in roles:
            menus.extend(await role.menus)
        menus = list(set(menus))

    tree = _build_menu_tree(menus)
    allowed = await _get_user_allowed_api_set(user)
    data = [_menu_to_app_route(m, allowed) for m in tree]
    return Success(data=data)

