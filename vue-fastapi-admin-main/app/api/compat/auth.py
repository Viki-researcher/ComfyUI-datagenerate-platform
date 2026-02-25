from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.controllers.user import user_controller
from app.models.admin import Role
from app.schemas.base import Success
from app.schemas.login import CredentialsSchema, JWTPayload
from app.schemas.users import UserCreate
from app.settings import settings
from app.utils.jwt_utils import create_access_token

router = APIRouter(prefix="/auth", tags=["基础模块"])


class LoginIn(BaseModel):
    userName: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class LoginOut(BaseModel):
    token: str
    refreshToken: str = ""


@router.post("/login", summary="登录（兼容 art-design-pro）")
async def login(req_in: LoginIn):
    # 复用原框架的认证逻辑
    user = await user_controller.authenticate(
        CredentialsSchema(username=req_in.userName, password=req_in.password)
    )
    await user_controller.update_last_login(user.id)

    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + access_token_expires

    token = create_access_token(
        data=JWTPayload(
            user_id=user.id,
            username=user.username,
            is_superuser=user.is_superuser,
            exp=expire,
        )
    )
    data = LoginOut(token=token, refreshToken="")
    return Success(data=data.model_dump())


class RegisterIn(BaseModel):
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    password: str = Field(..., description="密码")


@router.post("/register", summary="注册（兼容需求文档/平台）")
async def register(req_in: RegisterIn):
    if await user_controller.get_by_username(req_in.username):
        return Success(code=400, msg="用户名已存在", data=None)
    if await user_controller.get_by_email(req_in.email):
        return Success(code=400, msg="邮箱已存在", data=None)

    user = await user_controller.create_user(
        UserCreate(
            username=req_in.username,
            email=req_in.email,
            password=req_in.password,
            is_active=True,
            is_superuser=False,
            role_ids=[],
            dept_id=0,
        )
    )

    # 默认绑定“普通用户”角色，确保具备基础权限集合
    role = await Role.filter(name="普通用户").first()
    if role:
        await user.roles.add(role)

    return Success(data={"userId": user.id})

