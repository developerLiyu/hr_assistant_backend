from compileall import compile_file

from pydantic import BaseModel, Field, computed_field
from typing import Optional
from datetime import datetime

# 创建岗位请求
class PositionCreate(BaseModel):
    position_name: str = Field(..., max_length=100, description="岗位名称")
    department: str = Field(..., max_length=100, description="所属部门")
    job_description: str = Field(..., description="岗位职责")
    requirements: str = Field(..., description="任职要求")
    salary_range: Optional[str] = Field(None, max_length=50, description="薪资范围")
    work_location: Optional[str] = Field(None, max_length=100, description="工作地点")
    headcount: int = Field(default=1, ge=1, description="招聘人数")
    status: Optional[int] = Field(default=1, ge=1, le=3)

# 更新岗位请求
class PositionUpdate(BaseModel):
    id: int = Field(..., description="岗位ID")
    position_name: str = Field(..., max_length=100, description="岗位名称")
    department: str = Field(..., max_length=100, description="所属部门")
    job_description: str = Field(..., description="岗位职责")
    requirements: str = Field(..., description="任职要求")
    salary_range: Optional[str] = Field(None, max_length=50, description="薪资范围")
    work_location: Optional[str] = Field(None, max_length=100, description="工作地点")
    headcount: int = Field(default=1, ge=1, description="招聘人数")
    status: Optional[int] = Field(default=1, ge=1, le=3)

# 岗位响应
class PositionResponse(BaseModel):
    id: int
    position_name: str
    department: str
    job_description: str
    requirements: str
    salary_range: Optional[str]
    work_location: Optional[str]
    headcount: int
    status: int
    # status_name: str = ""
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @computed_field # 装饰器：计算属性
    @property # 装饰器：定义是属性，名称为status_name
    def status_name(self) -> str:
        # 状态名称映射
        status_map = {1: "开放招聘", 2: "暂停招聘", 3: "已关闭"}
        return status_map.get(self.status, "未知")

# 分页响应
class PositionListResponse(BaseModel):
    list: list[PositionResponse] # 岗位列表
    pagination: dict[str, int] # 分页信息

