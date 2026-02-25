import os
import typing

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    VERSION: str = "0.1.0"
    APP_TITLE: str = "Vue FastAPI Admin"
    PROJECT_NAME: str = "Vue FastAPI Admin"
    APP_DESCRIPTION: str = "Description"

    CORS_ORIGINS: typing.List = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: typing.List = ["*"]
    CORS_ALLOW_HEADERS: typing.List = ["*"]

    DEBUG: bool = True

    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    BASE_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))
    LOGS_ROOT: str = os.path.join(BASE_DIR, "app/logs")
    SECRET_KEY: str = "3488a63e1765035d386f05409663f55c83bfae3b3c61a932744b20ad14244dcf"  # openssl rand -hex 32
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 day
    # 数据库默认连接（需求：PostgreSQL 异步连接）。可通过环境变量切换：
    # - DB_DEFAULT_CONNECTION=postgres|sqlite
    DB_DEFAULT_CONNECTION: str = "postgres"

    # PostgreSQL（asyncpg）
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "data_generation"

    # ComfyUI 进程管理（数据生成平台）
    # - COMFYUI_REPO_PATH: ComfyUI 仓库根目录（例如 .../ComfyUI-master-fitow）
    # - COMFYUI_PYTHON: ComfyUI 环境的 python 可执行文件路径
    COMFYUI_REPO_PATH: str = ""
    COMFYUI_PYTHON: str = ""
    # ComfyUI 进程监听地址（传给 `python main.py --listen`）
    # - 仅本机访问：127.0.0.1
    # - 局域网/远程访问：0.0.0.0
    COMFYUI_LISTEN: str = "127.0.0.1"
    # 后端内部访问 ComfyUI 的主机名/IP（用于健康检查、history 拉取等）。
    # 默认自动推导：若 COMFYUI_LISTEN=0.0.0.0，则 internal_host=127.0.0.1；否则 internal_host=COMFYUI_LISTEN。
    COMFYUI_INTERNAL_HOST: str = ""
    # 前端打开 ComfyUI 的对外访问基地址（可选）。
    # 例如：COMFYUI_PUBLIC_BASE_URL="http://10.10.1.199"（无需带端口，端口由后端分配后拼接）
    # 为空时：后端会尝试从请求的 Host / X-Forwarded-* 推导。
    COMFYUI_PUBLIC_BASE_URL: str = ""
    COMFYUI_PORT_RANGE: str = "8200-8299"
    COMFYUI_INSTANCE_BASE_DIR: str = os.path.join("runtime", "comfy_instances")
    COMFYUI_LOG_DIR: str = os.path.join("runtime", "comfy_logs")
    COMFYUI_STARTUP_TIMEOUT_SECONDS: int = 60
    COMFYUI_HEARTBEAT_INTERVAL_SECONDS: int = 30
    COMFYUI_FORCE_CPU: bool = False
    COMFYUI_HISTORY_SYNC_INTERVAL_SECONDS: int = 10

    # ComfyUI -> 平台回调（可选）
    PLATFORM_INTERNAL_SECRET: str = ""
    PLATFORM_CALLBACK_URL: str = "http://127.0.0.1:9999/api/internal/comfy/callback"

    TORTOISE_ORM: dict = {}
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        self.TORTOISE_ORM = {
            "connections": {
                "sqlite": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {"file_path": f"{self.BASE_DIR}/db.sqlite3"},
                },
                "postgres": {
                    "engine": "tortoise.backends.asyncpg",
                    "credentials": {
                        "host": self.POSTGRES_HOST,
                        "port": self.POSTGRES_PORT,
                        "user": self.POSTGRES_USER,
                        "password": self.POSTGRES_PASSWORD,
                        "database": self.POSTGRES_DB,
                    },
                },
            },
            "apps": {
                "models": {
                    "models": ["app.models", "aerich.models"],
                    "default_connection": self.DB_DEFAULT_CONNECTION,
                },
            },
            "use_tz": False,
            "timezone": "Asia/Shanghai",
        }


settings = Settings()
