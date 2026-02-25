# art-design-pro 使用方法手册

> 适用项目：数据生成平台前端（Vue3 + Element Plus）

## 1. 框架定位与技术栈

- art-design-pro 是企业级后台模板，核心技术栈是 Vue3 + TypeScript + Vite + Element Plus。
- 强调的开发方式：使用组合式能力与封装组件（如 `useTable`、`ArtForm`）提升页面交付效率。

原文摘录（官方文档）：
- “UI 组件库：Element Plus”“核心框架：Vue 3、TypeScript、Vite”（见 `https://www.artd.pro/docs/zh/guide/introduce.html`）。

出处：
- `https://www.artd.pro/docs/zh/guide/introduce.html`
- `https://www.artd.pro/docs/zh/guide/quick-start.html`
- `art-design-pro/README.zh-CN.md`

---

## 2. 推荐目录与职责

- `src/api`：按业务域封装请求函数（页面不直接写 axios）。
- `src/store/modules`：管理登录态、用户信息、菜单与标签页状态。
- `src/router`：静态路由、动态路由、前后置守卫、权限验证。
- `src/components/core/forms`：通用表单/搜索组件（`ArtForm`、`ArtSearchBar`）。
- `src/utils/http`：统一请求拦截、响应解析、错误处理。

出处：
- `art-design-pro/src/store/modules/user.ts`
- `art-design-pro/src/router/guards/beforeEach.ts`
- `art-design-pro/src/components/core/forms/art-form/index.vue`
- `art-design-pro/src/utils/http/index.ts`

---

## 3. 开发环境与后端模式对接（必须掌握）

### 3.1 访问模式（frontend / backend）
- art-design-pro 通过环境变量 `VITE_ACCESS_MODE` 区分权限模式（见 `art-design-pro/src/hooks/core/useAppMode.ts` 与 `art-design-pro/.env`）。
  - `frontend`：菜单/路由来自前端 `router/modules/*`（适合本地无后端快速开发）。
  - `backend`：菜单/路由来自后端接口（适合企业级 RBAC + 动态路由）。

### 3.2 本地代理与 API 统一前缀
- Vite 开发代理把 `/api` 转发到 `VITE_API_PROXY_URL`（见 `art-design-pro/vite.config.ts` 的 `server.proxy['/api']`）。
- 因此前端所有接口统一以 `/api/...` 开头（见 `art-design-pro/src/api/*.ts`），无需在页面中拼接后端完整域名。

---

## 4. 登录鉴权标准用法

### 4.1 登录流程
- 登录页通过 `fetchLogin` 发起认证请求。
- 成功后调用 `userStore.setToken()` + `userStore.setLoginStatus(true)`。
- 跳转到 `redirect` 或首页。

### 4.2 路由守卫
- `beforeEach` 在访问受保护页面前校验 `isLogin`。
- 未登录跳转登录并记录目标路径；登录后自动回跳。
- 首次登录后会拉取用户信息与菜单并注册动态路由。

### 4.3 请求拦截
- 请求拦截器自动添加 `Authorization`。
- 响应中业务 `code !== success` 统一抛错。
- 401 触发统一登出，避免各页面重复处理会话失效逻辑。

出处：
- `art-design-pro/src/views/auth/login/index.vue`
- `art-design-pro/src/store/modules/user.ts`
- `art-design-pro/src/router/guards/beforeEach.ts`
- `art-design-pro/src/utils/http/index.ts`

---

## 5. 权限控制标准用法

### 5.1 三种权限入口
- `v-roles`：按角色控制可见性（粗粒度）。
- `v-auth`：按权限码控制按钮可见性（后端模式常用）。
- `hasAuth`：在脚本内进行编程式权限判断。

### 5.2 模式差异
- 前端模式：`hasAuth` 读取 `userStore.info.buttons`。
- 后端模式：`hasAuth` / `v-auth` 基于路由 `meta.authList`。

### 5.3 开发约束
- 前端按钮禁用/隐藏只是交互层，后端必须做最终权限校验。
- 对关键操作（删除、导出、批量）必须同时做按钮与接口双重权限保护。

出处：
- `art-design-pro/src/directives/core/roles.ts`
- `art-design-pro/src/directives/core/auth.ts`
- `art-design-pro/src/hooks/core/useAuth.ts`
- `art-design-pro/src/views/examples/permission/button-auth/index.vue`

---

## 6. API 封装规范

- 每个业务域建立独立 API 文件，如 `project.ts`、`stats.ts`。
- 统一返回类型使用 `BaseResponse<T>` 思路（`code/msg/data`）。
- POST/PUT 请求参数通过封装层传递，页面仅关注业务参数对象。
- 错误提示默认走全局错误处理；特殊场景再局部覆盖。

建议示例结构：
- `src/api/auth.ts`
- `src/api/logs.ts`
- `src/api/stats.ts`
- `src/api/server.ts`
- `src/api/projects.ts`（本项目新增：项目/ComfyUI 入口）

出处：
- `art-design-pro/src/api/auth.ts`
- `art-design-pro/src/utils/http/index.ts`
- `art-design-pro/src/types/common/response.ts`

---

## 7. 表单设计规范（强烈推荐）

### 7.1 组件选型
- 搜索筛选：`ArtSearchBar`
- 新增/编辑：`ArtForm`

### 7.2 字段配置方式
- 以 `items` 数组定义字段：`key/label/type/props/options/hidden/span`。
- 复杂字段使用 `render` 自定义渲染，避免在页面中散落大量模板逻辑。

### 7.3 校验与交互
- 提交前必须 `validate`。
- 重置时同时清理 UI 状态与 `modelValue` 值。
- 对密码、邮箱、手机号等字段复用 `utils/form/validator.ts` 规则。

出处：
- `art-design-pro/src/components/core/forms/art-form/index.vue`
- `art-design-pro/src/components/core/forms/art-search-bar/index.vue`
- `art-design-pro/src/utils/form/validator.ts`
- `art-design-pro/src/views/examples/forms/index.vue`

---

## 8. 数据生成平台页面落地（本项目已实现）

- **个人工作台页**：`art-design-pro/src/views/platform/workbench/index.vue`
  - 项目卡片（名称/项目号/创建时间/备注）+ “数据生成”按钮（`window.open(comfy_url)`）。
  - 新建/编辑项目用 `ArtForm`（字段配置驱动），避免散落模板逻辑。
- **生成日志页**：`art-design-pro/src/views/platform/logs/index.vue`
  - `useTable + ArtSearchBar` 实现筛选/分页/刷新。
- **统计页**：`art-design-pro/src/views/platform/stats/index.vue`
  - 趋势图使用内置 `ArtLineChart`（ECharts 按需配置见 `art-design-pro/src/plugins/echarts.ts`）。
- **服务器监控页**：`art-design-pro/src/views/platform/monitor/index.vue`
  - 仅读轮询展示（CPU/内存/SWAP/磁盘），符合需求“移除所有开关机或重启按钮，仅保留监控功能”（见 `docs/数据生成平台系统概述.md`）。

配套 API 封装：
- `art-design-pro/src/api/projects.ts`
- `art-design-pro/src/api/logs.ts`
- `art-design-pro/src/api/stats.ts`
- `art-design-pro/src/api/server.ts`

出处：
- `docs/数据生成平台系统概述.md`
- `docs/数据生成平台API与数据模型规范.md`

---

## 9. 与后端契约清单（前端必须遵守）

- **鉴权头**：前端请求封装会把 `accessToken` 写入 `Authorization` 头（见 `art-design-pro/src/utils/http/index.ts`），后端需兼容 `Authorization: <token>` 与 `Authorization: Bearer <token>`（需求文档也明确了 Bearer 形式，见 `docs/数据生成平台系统概述.md`）。
- **统一响应**：前端按 `ApiStatus.success=200` 判断成功（见 `art-design-pro/src/utils/http/status.ts`），后端需统一返回 `{ code, msg, data }`，并保证失败时 `msg` 可被拦截器展示。
- **分页结构（重要）**：由于请求封装会“只返回 data”，表格分页接口应把分页字段放在 `data` 内：`{ records, current, size, total }`（见 `art-design-pro/src/utils/table/tableConfig.ts` 与 `useTable` 适配逻辑）。
- **open_comfy 交互**：`open_comfy` 成功返回 `comfy_url`，前端新标签打开；非 owner 由后端返回 403（需求明确“必须验证当前用户为该服务的拥有者，否则返回 403”，见 `docs/数据生成平台系统概述.md`）。

出处：
- `art-design-pro/src/utils/http/index.ts`
- `art-design-pro/src/utils/http/status.ts`
- `art-design-pro/src/utils/table/tableConfig.ts`
- `docs/数据生成平台系统概述.md`

