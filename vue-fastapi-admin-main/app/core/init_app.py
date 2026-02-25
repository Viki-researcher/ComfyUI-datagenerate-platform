import shutil

from aerich import Command
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise.expressions import Q

from app.api import api_router
from app.controllers.api import api_controller
from app.controllers.user import UserCreate, user_controller
from app.core.exceptions import (
    DoesNotExist,
    DoesNotExistHandle,
    HTTPException,
    HttpExcHandle,
    IntegrityError,
    IntegrityHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResponseValidationError,
    ResponseValidationHandle,
)
from app.log import logger
from app.models.admin import Api, Menu, Role
from app.schemas.menus import MenuType
from app.settings.config import settings

from .middlewares import BackGroundTaskMiddleware, HttpAuditLogMiddleware


def make_middlewares():
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        ),
        Middleware(BackGroundTaskMiddleware),
        Middleware(
            HttpAuditLogMiddleware,
            methods=["GET", "POST", "PUT", "DELETE"],
            exclude_paths=[
                "/api/v1/base/access_token",
                "/api/auth/login",
                "/docs",
                "/openapi.json",
            ],
        ),
    ]
    return middleware


def register_exceptions(app: FastAPI):
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)


def register_routers(app: FastAPI, prefix: str = "/api"):
    app.include_router(api_router, prefix=prefix)


async def init_superuser():
    user = await user_controller.model.exists()
    if not user:
        await user_controller.create_user(
            UserCreate(
                username="admin",
                email="admin@admin.com",
                password="123456",
                is_active=True,
                is_superuser=True,
            )
        )


async def init_menus():
    menus = await Menu.exists()
    if not menus:
        parent_menu = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="系统管理",
            path="/system",
            order=1,
            parent_id=0,
            icon="carbon:gui-management",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/system/user",
        )
        children_menu = [
            Menu(
                menu_type=MenuType.MENU,
                name="用户管理",
                path="user",
                order=1,
                parent_id=parent_menu.id,
                icon="material-symbols:person-outline-rounded",
                is_hidden=False,
                component="/system/user",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="角色管理",
                path="role",
                order=2,
                parent_id=parent_menu.id,
                icon="carbon:user-role",
                is_hidden=False,
                component="/system/role",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="菜单管理",
                path="menu",
                order=3,
                parent_id=parent_menu.id,
                icon="material-symbols:list-alt-outline",
                is_hidden=False,
                component="/system/menu",
                keepalive=False,
                remark={
                    "authList": [
                        {
                            "title": "新增",
                            "authMark": "add",
                            "apis": [{"method": "POST", "path": "/api/v1/menu/create"}],
                        },
                        {
                            "title": "编辑",
                            "authMark": "edit",
                            "apis": [{"method": "POST", "path": "/api/v1/menu/update"}],
                        },
                        {
                            "title": "删除",
                            "authMark": "delete",
                            "apis": [{"method": "DELETE", "path": "/api/v1/menu/delete"}],
                        },
                    ]
                },
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="API管理",
                path="api",
                order=4,
                parent_id=parent_menu.id,
                icon="ant-design:api-outlined",
                is_hidden=False,
                component="/system/api",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="部门管理",
                path="dept",
                order=5,
                parent_id=parent_menu.id,
                icon="mingcute:department-line",
                is_hidden=False,
                component="/system/dept",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="审计日志",
                path="auditlog",
                order=6,
                parent_id=parent_menu.id,
                icon="ph:clipboard-text-bold",
                is_hidden=False,
                component="/system/auditlog",
                keepalive=False,
            ),
        ]
        await Menu.bulk_create(children_menu)
        # 注意：菜单数据需要与前端 views 组件路径一致，否则动态路由会加载失败。
        # 这里不再创建示例用的“一级菜单 /top-menu”，避免前端找不到对应组件。


async def init_apis():
    apis = await api_controller.model.exists()
    if not apis:
        await api_controller.refresh_api()


async def ensure_menu_auth_marks():
    """
    为需要按钮权限的菜单补齐 meta.authList 配置（写入 Menu.remark）。
    说明：art-design-pro 的 `v-auth` 指令读取的是当前路由 `meta.authList[].authMark`。
    """
    menu = await Menu.filter(component="/system/menu").first()
    if menu and not menu.remark:
        menu.remark = {
            "authList": [
                {"title": "新增", "authMark": "add", "apis": [{"method": "POST", "path": "/api/v1/menu/create"}]},
                {"title": "编辑", "authMark": "edit", "apis": [{"method": "POST", "path": "/api/v1/menu/update"}]},
                {
                    "title": "删除",
                    "authMark": "delete",
                    "apis": [{"method": "DELETE", "path": "/api/v1/menu/delete"}],
                },
            ]
        }
        await menu.save()


async def ensure_platform_menus():
    """
    数据生成平台菜单（用于 art-design-pro 后端模式动态路由）。
    component 字段必须与前端 views 组件路径一致：
    - Layout -> /index/index（由 compat 菜单接口转换）
    - 子页面 -> /platform/***
    """
    platform = await Menu.filter(path="/platform").first()
    if not platform:
        platform = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="数据生成平台",
            path="/platform",
            order=0,
            parent_id=0,
            icon="ri:dashboard-line",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/platform/workbench",
        )

    async def ensure_child(name: str, path: str, order: int, component: str, remark=None):
        exists = await Menu.filter(parent_id=platform.id, path=path).first()
        if exists:
            if remark and not exists.remark:
                exists.remark = remark
                await exists.save()
            return
        await Menu.create(
            menu_type=MenuType.MENU,
            name=name,
            path=path,
            order=order,
            parent_id=platform.id,
            icon="",
            is_hidden=False,
            component=component,
            keepalive=True,
            redirect="",
            remark=remark,
        )

    await ensure_child(
        name="个人工作台",
        path="workbench",
        order=1,
        component="/platform/workbench",
        remark={
            "authList": [
                {"title": "新建项目", "authMark": "project_add", "apis": [{"method": "POST", "path": "/api/projects"}]},
                {
                    "title": "数据生成",
                    "authMark": "open_comfy",
                    "apis": [{"method": "POST", "path": "/api/projects/{project_id}/open_comfy"}],
                },
                {
                    "title": "编辑项目",
                    "authMark": "project_edit",
                    "apis": [{"method": "PUT", "path": "/api/projects/{project_id}"}],
                },
                {
                    "title": "删除项目",
                    "authMark": "project_delete",
                    "apis": [{"method": "DELETE", "path": "/api/projects/{project_id}"}],
                },
            ]
        },
    )
    await ensure_child(name="数据统计", path="stats", order=2, component="/platform/stats")
    await ensure_child(name="生成日志", path="logs", order=3, component="/platform/logs")
    await ensure_child(name="服务器监控", path="monitor", order=4, component="/platform/monitor")


async def ensure_role_policies():
    """
    角色与权限策略（可重复执行，保证初始化后的数据库符合平台预期）。
    - 管理员：拥有全部菜单 + 全部 API
    - 普通用户：仅拥有“数据生成平台”菜单；拥有基础模块+平台业务模块 API
    """
    admin_role = await Role.filter(name="管理员").first()
    user_role = await Role.filter(name="普通用户").first()
    if not admin_role or not user_role:
        return

    all_apis = await Api.all()
    all_menus = await Menu.all()
    await admin_role.apis.clear()
    await admin_role.apis.add(*all_apis)
    await admin_role.menus.clear()
    await admin_role.menus.add(*all_menus)

    # 普通用户菜单：只给平台菜单（及其子菜单）
    platform = await Menu.filter(path="/platform").first()
    user_menus = []
    if platform:
        platform_children = await Menu.filter(parent_id=platform.id).all()
        user_menus = [platform, *platform_children]

    await user_role.menus.clear()
    if user_menus:
        await user_role.menus.add(*user_menus)

    # 普通用户 API：基础模块 + 平台业务模块
    allow_tags = ["基础模块", "项目模块", "日志模块", "统计模块", "监控模块"]
    basic_apis = await Api.filter(Q(tags__in=allow_tags))
    await user_role.apis.clear()
    await user_role.apis.add(*basic_apis)


async def init_db():
    command = Command(tortoise_config=settings.TORTOISE_ORM)
    try:
        await command.init_db(safe=True)
    except FileExistsError:
        pass

    await command.init()
    try:
        await command.migrate()
    except AttributeError:
        logger.warning("unable to retrieve model history from database, model history will be created from scratch")
        shutil.rmtree("migrations")
        await command.init_db(safe=True)

    await command.upgrade(run_in_transaction=True)


async def init_roles():
    roles = await Role.exists()
    if not roles:
        admin_role = await Role.create(
            name="管理员",
            desc="管理员角色",
        )
        user_role = await Role.create(
            name="普通用户",
            desc="普通用户角色",
        )

        # 初始绑定由 ensure_role_policies() 统一收敛
        pass


async def init_data():
    await init_db()
    await init_superuser()
    await init_menus()
    await ensure_platform_menus()
    await init_apis()
    await ensure_menu_auth_marks()
    await init_roles()
    await ensure_role_policies()
