## 02 PostgreSQL 安装与初始化规范（本机 systemd 管理）

本文目标：在开发机（Linux）上以 **systemd** 方式安装并管理 PostgreSQL，并初始化平台所需的用户/数据库，最终让后端可以通过 `asyncpg` 连接成功。

> 说明：本文按 Debian/Ubuntu（apt）编写；若你使用 CentOS/RHEL，请将安装命令替换为 `yum/dnf` 对应包名与服务名。

---

## 1. 安装 PostgreSQL

### 1.1 使用自动安装脚本（推荐）

```bash
cd /home/admin1/ai02/codeyard/wk_codeyard/Code_backup/ComfulUI/docs/scripts
chmod +x install_postgres.sh
./install_postgres.sh
```

### 1.2 手动安装

或者使用系统源安装（推荐）：

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

安装后检查服务：

```bash
sudo systemctl status postgresql --no-pager
```

设置开机自启：

```bash
sudo systemctl enable postgresql
```

---

## 2. 初始化账号与数据库（两种策略）

平台后端默认连接参数来自后端配置（见 `vue-fastapi-admin-main/app/settings/config.py`）：\n
- `POSTGRES_HOST=127.0.0.1`\n
- `POSTGRES_PORT=5432`\n
- `POSTGRES_DB=data_generation`\n
- `POSTGRES_USER=postgres`\n
- `POSTGRES_PASSWORD=postgres`\n

你可以选择：\n
- **策略 A（简单）**：直接使用 `postgres` 超级用户（仅开发环境推荐）\n
- **策略 B（推荐）**：创建独立用户 `datagen` + 独立数据库 `data_generation`（开发/生产都适用）

### 2.1 策略 A：使用 postgres 用户

```bash
sudo -u postgres psql
```

在 psql 中设置密码（示例：`postgres`）：

```sql
ALTER USER postgres WITH PASSWORD 'postgres';
```

创建数据库：

```sql
CREATE DATABASE data_generation OWNER postgres;
```

退出：

```sql
\\q
```

### 2.2 策略 B：创建 datagen 用户（推荐）

```bash
sudo -u postgres psql
```

创建用户与数据库（示例密码 `datagen_dev_pw`，请自行更换）：

```sql
CREATE USER datagen WITH PASSWORD 'datagen_dev_pw';
CREATE DATABASE data_generation OWNER datagen;
GRANT ALL PRIVILEGES ON DATABASE data_generation TO datagen;
```

退出：

```sql
\\q
```

---

## 3. 网络与访问控制（开发机默认本机访问即可）

开发机通常只需要本机访问（`127.0.0.1`），无需开放到局域网。\n
若你确实需要允许其他机器访问，需要同时调整：\n
- `postgresql.conf` 的 `listen_addresses`\n
- `pg_hba.conf` 的访问规则\n

Ubuntu 上配置文件常见位置（具体版本可能不同）：\n
- `/etc/postgresql/<version>/main/postgresql.conf`\n
- `/etc/postgresql/<version>/main/pg_hba.conf`\n

修改后重启服务：

```bash
sudo systemctl restart postgresql
```

---

## 4. 连接自检（必须通过）

### 4.1 使用 psql 自检

若使用策略 A：

```bash
psql "host=127.0.0.1 port=5432 user=postgres dbname=data_generation"
```

若使用策略 B：

```bash
psql "host=127.0.0.1 port=5432 user=datagen password=datagen_dev_pw dbname=data_generation"
```

### 4.2 后端应用自检

后端会用 `tortoise.backends.asyncpg` 连接 PostgreSQL；确保后端环境变量与此处初始化一致。\n
建议把实际采用的连接参数写入 `docs/03_配置说明_前端后端ComfyUI.md` 对应章节，并在后续一键脚本里统一管理。

---

## 5. 生产化最低建议（先写入规范，避免以后返工）

- **不要在生产使用 postgres 超级用户跑业务**（建议策略 B，并最小权限）\n
- **仅监听内网地址**，并通过防火墙控制\n
- 开启定期备份（逻辑备份 `pg_dump` 或物理备份）\n
- 监控连接数、慢查询（必要时开启 `pg_stat_statements`）

