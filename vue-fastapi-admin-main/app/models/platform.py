from tortoise import fields

from .base import BaseModel, TimestampMixin


class Project(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=100, description="项目名称", index=True)
    code = fields.CharField(max_length=50, unique=True, description="项目号", index=True)
    note = fields.TextField(null=True, description="备注")
    owner_user_id = fields.BigIntField(description="创建者用户ID", index=True)

    class Meta:
        table = "projects"


class ComfyUIService(BaseModel, TimestampMixin):
    user_id = fields.BigIntField(description="用户ID", index=True)
    project_id = fields.BigIntField(description="项目ID", index=True)
    port = fields.IntField(description="端口号", index=True)
    status = fields.CharField(max_length=20, default="online", description="状态(online/offline)", index=True)
    comfy_url = fields.CharField(max_length=255, description="访问地址")
    last_heartbeat = fields.DatetimeField(null=True, description="最后心跳时间", index=True)
    pid = fields.IntField(null=True, description="进程PID", index=True)
    base_dir = fields.CharField(max_length=255, null=True, description="实例base目录")
    log_path = fields.CharField(max_length=255, null=True, description="实例日志路径")
    start_time = fields.DatetimeField(null=True, description="启动时间", index=True)

    class Meta:
        table = "comfyui_services"
        unique_together = ("user_id", "project_id")


class GenerationLog(BaseModel, TimestampMixin):
    user_id = fields.BigIntField(description="用户ID", index=True)
    project_id = fields.BigIntField(description="项目ID", index=True)
    timestamp = fields.DatetimeField(description="生成时间", index=True)
    status = fields.CharField(max_length=20, description="状态(成功/失败等)", index=True)
    prompt_id = fields.CharField(max_length=64, null=True, description="ComfyUI prompt_id", index=True)
    concurrent_id = fields.BigIntField(null=True, description="并发ID", index=True)
    details = fields.JSONField(null=True, description="详情(错误/耗时等)")

    class Meta:
        table = "generation_logs"
        indexes = (("project_id", "timestamp"), ("user_id", "timestamp"))
        unique_together = (("project_id", "prompt_id"),)

