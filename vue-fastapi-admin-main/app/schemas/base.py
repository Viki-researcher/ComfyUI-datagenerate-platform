from typing import Any, Optional

from fastapi.responses import JSONResponse


class Success(JSONResponse):
    def __init__(
        self,
        code: int = 200,
        msg: Optional[str] = "OK",
        data: Optional[Any] = None,
        **kwargs,
    ):
        content = {"code": code, "msg": msg, "data": data}
        content.update(kwargs)
        # 前端（art-design-pro）默认只接受 2xx 响应，并在响应体内用 code 区分业务成功/失败。
        # 因此统一使用 HTTP 200，业务状态用 content.code 表达。
        super().__init__(content=content, status_code=200)


class Fail(JSONResponse):
    def __init__(
        self,
        code: int = 400,
        msg: Optional[str] = None,
        data: Optional[Any] = None,
        **kwargs,
    ):
        content = {"code": code, "msg": msg, "data": data}
        content.update(kwargs)
        super().__init__(content=content, status_code=200)


class SuccessExtra(JSONResponse):
    def __init__(
        self,
        code: int = 200,
        msg: Optional[str] = None,
        data: Optional[Any] = None,
        total: int = 0,
        page: int = 1,
        page_size: int = 20,
        **kwargs,
    ):
        content = {
            "code": code,
            "msg": msg,
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
        content.update(kwargs)
        super().__init__(content=content, status_code=200)
