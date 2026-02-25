# ComfyUI 服务启动逻辑说明

本文档详细说明数据生成平台中 ComfyUI 服务的启动、管理和状态判断逻辑。

---

## 1. 启动触发

用户在个人工作台的项目卡片上点击 **"数据生成"** 按钮后，前端调用后端接口：

```
POST /api/projects/{projectId}/open_comfy
```

---

## 2. 后端处理逻辑

后端 `ensure_comfyui_service` 函数（位于 `app/services/comfyui_manager.py`）执行以下步骤：

### 2.1 检查现有服务记录

```python
existing = await ComfyUIService.filter(project_id=project_id).first()
```

- **如果存在记录且状态为 "在线"**：先调用 `is_healthy()` 进行健康检查
  - 若健康检查通过（返回 `true`），则**复用已有服务**，直接返回服务信息
  - 若健康检查失败，说明服务可能已崩溃，进入重启流程

- **如果不存在记录或服务状态为 "离线"**：进入启动新服务流程

### 2.2 启动新服务流程

1. **停止旧进程**（如果存在）：
   ```python
   if existing and existing.pid:
       stop_pid(int(existing.pid))
   ```

2. **选择可用端口**：
   - 从配置 `COMFYUI_PORT_RANGE`（默认 `8200-8299`）中选取空闲端口

3. **创建实例目录**：
   - 在 `COMFYUI_INSTANCE_BASE_DIR` 下创建用户-项目专属目录
   - 建立软链接指向共享的 `custom_nodes` 和 `models`

4. **启动 ComfyUI 进程**：
   ```python
   subprocess.Popen([
       python_exec,
       "main.py",
       "--listen", listen_address,
       "--port", port,
       "--disable-auto-launch",
       "--base-directory", instance_dir,
       ...
   ])
   ```

5. **等待健康检查**：
   - 最多等待 `COMFYUI_STARTUP_TIMEOUT_SECONDS`（默认 240 秒）
   - 每秒检查一次 `GET /system_stats` 是否返回 200

6. **保存服务记录**：
   - 记录端口、状态（online）、comfy_url、进程ID、启动时间等

---

## 3. 是否可以反复点击？

**是的，可以反复点击。**

系统设计为：
- **首次点击**：启动新的 ComfyUI 服务
- **后续点击**：
  - 若服务仍在线且健康 → **直接返回已有服务地址**（不会重复启动）
  - 若服务已崩溃/离线 → **自动重启**一个新实例

这确保了：
1. 用户体验：无须手动管理服务生命周期
2. 资源合理：避免重复启动占用端口和内存

---

## 4. 服务状态判断逻辑

### 4.1 心跳机制

后端定时运行 `heartbeat_loop()`（默认间隔 30 秒）：

```python
async def heartbeat_once():
    for service in all_services:
        ok = await is_healthy(service.comfy_url)
        if ok:
            service.status = "online"
        else:
            service.status = "offline"
```

- **健康检查**：访问 `GET {comfy_url}/system_stats`，超时 2.5 秒
- 返回 200 → 在线，否则 → 离线

### 4.2 前端显示

- **"已连接"**：状态为 `online`
- **"连接中断"**：状态为 `offline`

前端每 8 秒轮询项目列表接口，获取最新的服务状态。

---

## 5. 权限校验

后端接口 `POST /api/projects/{projectId}/open_comfy` 包含两层权限校验：

1. **项目所有权校验**：
   ```python
   if project.owner_user_id != user_id:
       return Fail(code=403, msg="无操作权限")
   ```

2. **服务访问校验**（双保险）：
   ```python
   if existing and existing.user_id != user_id:
       return Fail(code=403, msg="无操作权限")
   ```

这确保了：
- 只有项目所有者才能启动该项目的 ComfyUI
- 其他用户无法访问他人的服务

---

## 6. 关键配置项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `COMFYUI_REPO_PATH` | - | ComfyUI 仓库路径（必填） |
| `COMFYUI_PYTHON` | - | ComfyUI Python 解释器路径（必填） |
| `COMFYUI_PORT_RANGE` | `8200-8299` | 端口分配范围 |
| `COMFYUI_LISTEN` | `127.0.0.1` | 监听地址 |
| `COMFYUI_STARTUP_TIMEOUT_SECONDS` | `240` | 启动超时时间 |
| `COMFYUI_HEARTBEAT_INTERVAL_SECONDS` | `30` | 心跳检测间隔 |

---

## 7. 日志与调试

- **服务日志位置**：`{COMFYUI_LOG_DIR}/comfy_u{user_id}_p{project_id}_{port}.log`
- **数据库记录**：`comfyui_services` 表包含所有服务实例信息

如需调试，可查看后端日志或直接访问 `http://{host}:{port}/system_stats` 验证 ComfyUI 是否正常运行。
