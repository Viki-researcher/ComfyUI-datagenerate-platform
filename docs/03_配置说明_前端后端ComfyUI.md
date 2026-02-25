## 03 配置说明（前端 art-design-pro / 后端 vue-fastapi-admin-main / ComfyUI-master-fitow）

本文目标：把平台运行所需的**关键配置**集中说明，避免“前端/后端/ComfyUI 各自一套口径”。

---

## 1. 端口与地址约定（开发默认）

- **后端 FastAPI**：`http://127.0.0.1:9999`\n
  - API 前缀：`/api`（例如登录：`POST /api/auth/login`）\n
  - Swagger：`http://127.0.0.1:9999/docs`\n
- **前端 Vite DevServer**：`http://127.0.0.1:3006`\n
  - 前端所有请求以 `/api/...` 开头，通过 Vite 代理转发到后端\n
- **ComfyUI 实例**：由后端按项目按需拉起\n
  - 端口池建议：`8200-8299`（避免占用 ComfyUI 默认 `8188`）\n
  - 健康检查建议：`GET /system_stats`\n

---

## 1.1 局域网访问（可选）

如果你希望在局域网其它机器上访问平台：

- 将 `docs/.env.platform` 中 `FRONTEND_HOST` / `BACKEND_HOST` 设置为 `0.0.0.0`
- 访问地址用服务器的局域网 IP（不要在其它机器上使用 `localhost`），例如：`http://10.10.1.199:3006`

## 2. 前端（art-design-pro）配置

文件位置：\n
- `art-design-pro/.env`（通用）\n
- `art-design-pro/.env.development`（开发环境）\n

### 2.1 开启后端权限模式（必须）

将 `VITE_ACCESS_MODE` 设置为 `backend`，让前端从后端拉取菜单与按钮权限（RBAC）。\n
默认文件 `art-design-pro/.env` 里目前是 `frontend`，需要改为：

- `VITE_ACCESS_MODE = backend`

### 2.2 开发代理指向本机后端（必须）

将 `art-design-pro/.env.development` 里的 `VITE_API_PROXY_URL` 指向后端，例如：

- `VITE_API_PROXY_URL = http://127.0.0.1:9999`

说明：前端请求会统一走 `/api/...`，Vite 代理把 `/api` 转发到该地址。

---

## 3. 后端（vue-fastapi-admin-main）配置

后端配置入口：`vue-fastapi-admin-main/app/settings/config.py`（`BaseSettings` 从环境变量读取）。\n
你需要至少确认以下环境变量：

### 3.1 数据库（PostgreSQL / asyncpg）

建议开发默认：

- `DB_DEFAULT_CONNECTION=sqlite`（本机无 sudo/未装 PG 时，用于快速联调）\n
- `DB_DEFAULT_CONNECTION=postgres`（安装并初始化 PostgreSQL 后切换）\n
- `POSTGRES_HOST=127.0.0.1`\n
- `POSTGRES_PORT=5432`\n
- `POSTGRES_USER=datagen`（或 `postgres`，按你的初始化策略）\n
- `POSTGRES_PASSWORD=...`\n
- `POSTGRES_DB=data_generation`

### 3.2 ComfyUI 进程管理（后续实现 `open_comfy` 真启动时需要）

建议新增并统一使用下列环境变量（后续会在后端代码中读取）：\n

- `COMFYUI_REPO_PATH`：ComfyUI 仓库目录（本仓库默认：`.../ComfyUI-master-fitow`）\n
- `COMFYUI_PYTHON`：ComfyUI conda 环境的 python 路径\n
  - 推荐填写 `$(conda info --base)/envs/datagen-comfyui/bin/python`\n
- `COMFYUI_LISTEN`：ComfyUI 进程监听地址（传给 `python main.py --listen`）\n
  - 仅本机联调：`127.0.0.1`\n
  - 局域网/远程访问：`0.0.0.0`\n
- `COMFYUI_INTERNAL_HOST`：后端内部访问 ComfyUI 的 host（用于健康检查、拉取 `/history`）\n
  - 默认自动推导：当 `COMFYUI_LISTEN=0.0.0.0` 时内部会用 `127.0.0.1`；一般无需配置\n
- `COMFYUI_PUBLIC_BASE_URL`：前端打开 ComfyUI 的对外基地址（不带端口），例如 `http://10.10.1.199`\n
  - 若不配置，后端会尝试从请求 Host / `X-Forwarded-*` 推导；在 dev 代理/反向代理下可能不稳定，建议显式配置\n
- `COMFYUI_PORT_RANGE=8200-8299`\n
- `COMFYUI_INSTANCE_BASE_DIR`：每个 (user,project) 的 ComfyUI base dir 根目录（例如 `./runtime/comfy_instances`）\n
- `COMFYUI_LOG_DIR`：ComfyUI 进程日志目录（例如 `./runtime/comfy_logs`）\n
- `COMFYUI_FORCE_CPU=true|false`：若为 CPU-only torch，必须为 `true`（后端启动 ComfyUI 会自动追加 `--cpu`）\n
- `COMFYUI_HISTORY_SYNC_INTERVAL_SECONDS=10`：轮询 `GET /history` 自动写生成日志的间隔\n
- `COMFYUI_HEARTBEAT_INTERVAL_SECONDS=30`：心跳检查间隔\n
- `COMFYUI_STARTUP_TIMEOUT_SECONDS=240`：`open_comfy` 等待启动健康检查的超时时间\n
- `PLATFORM_INTERNAL_SECRET`：启用 ComfyUI 回调写日志的 secret（Header：`X-Platform-Secret`）\n
- `PLATFORM_CALLBACK_URL`：后端回调地址（默认：`http://127.0.0.1:9999/api/internal/comfy/callback`）\n

---

## 4. ComfyUI（ComfyUI-master-fitow）说明

ComfyUI 启动参数（关键）：\n
- `--listen`：监听地址\n
- `--port`：监听端口（参数定义见 `ComfyUI-master-fitow/comfy/cli_args.py`）\n
- 建议额外加 `--disable-auto-launch`（避免启动时弹浏览器）

示例（未来由后端启动，不建议手工长期运行多个实例）：\n

```bash
conda activate datagen-comfyui
cd ComfyUI-master-fitow
python main.py --listen 127.0.0.1 --port 8200 --disable-auto-launch
```

---

## 5. 统一配置的落地方式（推荐）

为了减少“环境变量散落”，建议在仓库根目录新增：\n
- `docs/.env.platform`：开发机统一配置（提交 `.env.platform.example`，本机复制后修改）\n
- `docs/scripts/`：一键启动脚本读取该 env 文件并导出到进程环境

一键启动脚本已落在：`docs/scripts/start_all.sh` / `stop_all.sh` / `status.sh`。

