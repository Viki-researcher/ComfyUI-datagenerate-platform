# vue-fastapi-admin-main 使用方法手册

> 适用项目：数据生成平台后端（FastAPI + Tortoise ORM）

## 1. 框架定位与核心能力

- 后端提供 FastAPI 异步服务，内置 JWT 鉴权、RBAC 权限、动态路由配套能力。
- 可作为中台后端骨架，快速扩展业务域模型与 RESTful API。

原文摘录（项目 README）：
- “融合了 RBAC 权限管理、动态路由和 JWT 鉴权”（见 `https://github.com/mizhexiaoxiao/vue-fastapi-admin` 的 README）。

出处：
- `vue-fastapi-admin-main/README.md`（项目 README 也明确“RBAC 权限管理、动态路由和 JWT 鉴权”，可对照 `https://github.com/mizhexiaoxiao/vue-fastapi-admin`）

---

## 2. 项目结构与分层职责

- `app/api/v1`：路由层（参数接收、响应返回、依赖注入）。
- `app/controllers`：业务控制层（复用 CRUD、聚合业务逻辑）。
- `app/models`：数据模型层（Tortoise ORM）。
- `app/schemas`：请求/响应结构定义（Pydantic）。
- `app/core`：依赖注入、中间件、初始化、异常处理。
- `app/utils`：JWT、密码、工具方法。

出处：
- `vue-fastapi-admin-main/README.md`
- `vue-fastapi-admin-main/app/core/init_app.py`

---

## 3. 登录鉴权标准用法

### 3.1 登录
- 登录接口示例：`/api/v1/base/access_token`
- 成功后返回 access token（JWT），用于后续受保护接口访问。

### 3.2 鉴权依赖
- 使用 `DependAuth` 保护接口。
- `AuthControl.is_authed` 负责解码 JWT、查询用户、写入上下文用户 ID。

补充（为对齐前端契约）：
- 兼容 `Authorization` 头与 `Bearer` 形式（见 `vue-fastapi-admin-main/app/core/dependency.py`）。

### 3.3 密码策略
- 使用 Argon2 哈希与校验（`get_password_hash` / `verify_password`）。
- 严禁明文密码存储。

出处：
- `vue-fastapi-admin-main/app/api/v1/base/base.py`
- `vue-fastapi-admin-main/app/core/dependency.py`
- `vue-fastapi-admin-main/app/utils/password.py`
- `vue-fastapi-admin-main/app/utils/jwt_utils.py`

---

## 4. 权限分配规范（RBAC）

### 4.1 模型关系
- `User` 多对多 `Role`
- `Role` 多对多 `Menu`
- `Role` 多对多 `Api`

### 4.2 判定逻辑
- `PermissionControl.has_permission` 基于 `(request.method, request.url.path)` 与授权 API 集合比对。
- 超级管理员可直接放行。

### 4.3 路由接入
- 路由组通过 `dependencies=[DependPermission]` 启用接口级权限校验。

### 4.4 与前端按钮权限（authMark）对齐（本项目约定）
- 前端 `art-design-pro` 的 `v-auth` / `hasAuth` 读取的是路由 `meta.authList[].authMark`（源码事实见 `art-design-pro/src/directives/core/auth.ts`、`art-design-pro/src/types/router/index.ts`）。
- 本项目约定把按钮权限配置写入 `Menu.remark`（JSON），结构示例：
  - `{"authList":[{"title":"新增","authMark":"add","apis":[{"method":"POST","path":"/api/v1/menu/create"}]}]}`
- `GET /api/v3/system/menus` 返回菜单时，会基于当前用户授权的 API 集合过滤 `authList`，从而实现“按钮可见性与接口权限一致”（见 `vue-fastapi-admin-main/app/api/compat/system.py` 与初始化补齐逻辑 `app/core/init_app.py::ensure_menu_auth_marks`、`ensure_platform_menus`）。
出处：
- `vue-fastapi-admin-main/app/models/admin.py`
- `vue-fastapi-admin-main/app/core/dependency.py`
- `vue-fastapi-admin-main/app/api/v1/__init__.py`

---

## 5. API 设计与返回规范

### 5.1 统一响应
- **统一响应体**：`{ code, msg, data }`（见 `vue-fastapi-admin-main/app/schemas/base.py`）。
- **与 art-design-pro 对齐的关键点**：为了让前端能稳定读取 `msg` 并按响应体 `code` 做统一处理，后端将 `Success/Fail/SuccessExtra` 与异常处理统一为 **HTTP 200**，业务状态通过响应体 `code` 表达（见 `app/schemas/base.py`、`app/core/exceptions.py`）。
- **分页接口（前端 useTable 兼容）**：由于前端请求封装会“只返回 data”，表格分页接口推荐返回 `data: { records, current, size, total }`（compat 层已实现示例：`app/api/compat/users.py`、`roles.py`、`logs.py`）。

### 5.2 RESTful 约定
- 资源接口建议保持“列表/详情/创建/更新/删除”一致结构。
- 列表接口支持分页与过滤条件。

### 5.3 控制器复用
- 继承 `CRUDBase` 减少重复代码；复杂逻辑在 Controller 中扩展。

出处：
- `vue-fastapi-admin-main/app/schemas/base.py`
- `vue-fastapi-admin-main/app/api/v1/users/users.py`
- `vue-fastapi-admin-main/app/core/crud.py`

---

## 6. PostgreSQL 异步连接与迁移规范

### 6.1 数据库连接
- 在 `app/settings/config.py` 中启用 `postgres` 连接，驱动为 `tortoise.backends.asyncpg`，并用 `asyncpg` 作为驱动（见 `vue-fastapi-admin-main/app/settings/config.py` 与依赖安装）。
- 默认连接由 `DB_DEFAULT_CONNECTION` 控制（默认 `postgres`）；PostgreSQL 连接参数由 `POSTGRES_HOST/PORT/USER/PASSWORD/DB` 控制（见 `app/settings/config.py`）。

### 6.2 迁移工具
- 使用 Aerich 管理迁移。
- 常用命令：`aerich migrate`、`aerich upgrade`。

### 6.3 初始化流程
- 应用启动初始化可执行：建库/迁移、超级用户、菜单、API、角色初始化。

出处：
- `vue-fastapi-admin-main/app/settings/config.py`
- `vue-fastapi-admin-main/pyproject.toml`
- `vue-fastapi-admin-main/Makefile`
- `vue-fastapi-admin-main/app/core/init_app.py`

---

## 7. 日志审计与可观测

- `HttpAuditLogMiddleware` 会记录请求路径、方法、用户、耗时、请求参数、响应摘要。
- 建议将核心业务接口纳入审计，排除登录、docs 等噪声路径。

出处：
- `vue-fastapi-admin-main/app/core/middlewares.py`
- `vue-fastapi-admin-main/app/models/admin.py`（`AuditLog`）

---

## 8. 数据生成平台落地扩展指南

## 8.1 推荐新增业务域
- `projects`：项目主数据
- `comfyui_services`：服务实例与心跳状态
- `generation_logs`：生成记录与统计基础

本仓库已落地的模型位置：
- `vue-fastapi-admin-main/app/models/platform.py`
- 对应迁移（示例）：`vue-fastapi-admin-main/migrations/models/*_init.py`（包含 `projects/comfyui_services/generation_logs` 表）

## 8.2 推荐新增 API 组
- `/api/projects/*`
- `/api/projects/{id}/open_comfy`
- `/api/logs`、`/api/stats`、`/api/export`
- `/api/server/stats`

本仓库已落地（前端契约优先）的 compat API：
- `vue-fastapi-admin-main/app/api/compat/auth.py`：`/api/auth/login`、`/api/auth/register`
- `vue-fastapi-admin-main/app/api/compat/users.py`：`/api/user/info`、`/api/user/list`
- `vue-fastapi-admin-main/app/api/compat/roles.py`：`/api/role/list`
- `vue-fastapi-admin-main/app/api/compat/system.py`：`/api/v3/system/menus`
- `vue-fastapi-admin-main/app/api/compat/projects.py`：`/api/projects`、`/api/projects/{project_id}/open_comfy`
- `vue-fastapi-admin-main/app/api/compat/logs.py`：`/api/logs`
- `vue-fastapi-admin-main/app/api/compat/stats.py`：`/api/stats`、`/api/export`
- `vue-fastapi-admin-main/app/api/compat/server.py`：`/api/server/stats`

## 8.3 与 ComfyUI 交互分层建议
- `api` 层：参数校验、权限校验、返回响应
- `controller` 层：业务编排
- `service` 层：ComfyUI 通信、端口管理、健康检查、重试
- `model` 层：服务状态与日志持久化

## 8.4 关键约束
- 单用户-单项目-单服务实例（建议唯一约束）。
- owner 级资源权限必须后端强校验，前端按钮控制仅为体验层。
- 统计/导出接口必须走鉴权并记录审计日志。

出处：
- `docs/数据生成平台系统概述.md`
- `docs/前端契约与后端适配差异清单.md`
- `vue-fastapi-admin-main/app/core/dependency.py`
- `vue-fastapi-admin-main/app/schemas/base.py`

