# 数据生成平台 API 与数据模型规范（契约主导：art-design-pro）

> 本文用于把《数据生成平台系统概述》中的需求点落到“页面 → API → 数据表”，并对齐 `art-design-pro` 的前端请求封装与权限机制，以及 `vue-fastapi-admin-main` 的后端 RBAC/JWT/ORM 结构。

## 1. 需求原文摘录（用于对齐）

- **总体架构与流程**（需求原文）：
  - “系统架构如下：用户通过前端界面进行操作，前端调用后端提供的 RESTful API；后端负责处理业务逻辑，并与 ComfyUI 服务进行通信，最终将结果反馈给前端；数据库记录用户、项目、ComfyUI 服务状态和生成日志等信息……整体流程为：用户 → 前端界面 → 后端 API → （必要时）ComfyUI → 后端 → 前端展现结果。”（见 `docs/数据生成平台系统概述.md`）
- **鉴权头协议**（需求原文）：
  - “前端在发起请求时在 Header 中附加 Authorization: Bearer <token>，后端通过 FastAPI 依赖注入自动校验用户身份”（见 `docs/数据生成平台系统概述.md`）
- **open_comfy 权限约束**（需求原文）：
  - “某项目的 ComfyUI 服务由用户A启动，则用户B…后端会拒绝操作并提示权限不足…后端接口 POST /api/projects/{projectId}/open_comfy 必须验证当前用户为该 ComfyUI 服务的拥有者，否则返回 403 错误。”（见 `docs/数据生成平台系统概述.md`）
- **统计/导出/监控接口**（需求原文）：
  - “GET /api/stats… GET /api/export… GET /api/server/stats…”（见 `docs/数据生成平台系统概述.md`）

## 2. 页面 → API → 表（映射清单）

### 2.1 登录/注册
- **页面**
  - 登录页：`art-design-pro/src/views/auth/login/index.vue`
  - 注册页：`art-design-pro/src/views/auth/register/index.vue`（当前页面内标注了 TODO，需接真实 API）
- **API（前端契约）**
  - `POST /api/auth/login`：入参 `{ userName, password }`，出参 `data: { token, refreshToken }`（见 `art-design-pro/src/api/auth.ts`）
  - `POST /api/auth/register`：入参 `{ username, email, password }`（需求文档定义）
  - `GET /api/user/info`：返回 `data: { buttons, roles, userId, userName, email, avatar? }`（见 `art-design-pro/src/types/api/api.d.ts`、`art-design-pro/src/api/auth.ts`）
- **表**
  - `user`（框架既有）：包含 `id/username/email/password_hash/is_active/is_superuser/created_at/updated_at/...`（见 `vue-fastapi-admin-main/app/models/admin.py`）

### 2.2 个人工作台（项目卡片 + 数据生成按钮）
- **页面（建议新增）**
  - 工作台/项目列表页：展示项目卡片（名称、项目号、创建时间、备注、服务状态）+ “数据生成”按钮
- **API（需求文档定义）**
  - `POST /api/projects`：新建项目（见 `docs/数据生成平台系统概述.md` “新建项目”）
  - `GET /api/projects`：项目列表（见 `docs/数据生成平台系统概述.md` “项目列表”）
  - `POST /api/projects/{projectId}/open_comfy`：打开/启动 ComfyUI（见 `docs/数据生成平台系统概述.md` “数据生成按钮逻辑”）
- **表（需求文档定义）**
  - `projects`：`id, name, code, note, owner_user_id, create_time`（需求文档示例）
  - `comfyui_services`：`service_id/user_id/project_id/port/status/last_heartbeat`（需求文档示例）

### 2.3 数据统计（图表 + 明细表 + 导出）
- **页面（建议新增）**
  - 统计看板页：筛选（时间范围、维度、项目、用户）+ 折线图 + 明细表 + 导出按钮
- **API（需求文档定义）**
  - `POST /api/logs`：写入生成日志（需求文档示例）
  - `GET /api/logs`：查询明细日志（需求文档示例）
  - `GET /api/stats`：聚合统计（按 day/project/user）
  - `GET /api/export`：导出（Excel 文件流）
- **表**
  - `generation_logs`：`log_id/user_id/project_id/timestamp/status/concurrent_id/details`（需求文档示例）

### 2.4 服务器监控（只读）
- **页面（建议新增）**
  - 监控页：定时轮询显示 CPU/内存/SWAP/磁盘（需求文档明确“移除所有开关机或重启按钮，仅保留监控功能”）
- **API**
  - `GET /api/server/stats`：返回 `{ cpu, memory, swap, disk }`（需求文档示例）

## 3. 与 art-design-pro 的契约对齐要点（必须遵守）

- **统一请求封装**：页面不直接发请求，统一通过 `src/api/*.ts` 调用 `src/utils/http/index.ts`（该封装会注入 `Authorization` 并统一处理 401、成功/失败提示）。\n- **统一响应格式**：前端封装默认按 `code===200` 识别成功（见 `art-design-pro/src/utils/http/status.ts` 与 `src/utils/http/index.ts`）。因此后端建议使用 HTTP 200 并在响应体中用 `{ code, msg, data }` 表达业务状态。\n- **菜单/按钮权限数据形状**：后端菜单接口需返回可直接作为 `AppRouteRecord[]` 的结构，并在 `meta.authList` 里提供 `{ title, authMark }` 供 `v-auth/hasAuth` 使用（见 `art-design-pro/src/types/router/index.ts`、`src/directives/core/auth.ts`）。\n
