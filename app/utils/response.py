from typing import Any, TypeVar, Generic, List

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


# 定义返回响应
def response(code: int = 200, message: str = "success", data: Any = None):
    content = {
        "code": code,
        "message": message,
        "data": data
    }
    # 目的是将任何对象（FastAPI对象、pydantic对象、orm对象）都能正常响应，转换成json
    return JSONResponse(content=jsonable_encoder(content))



