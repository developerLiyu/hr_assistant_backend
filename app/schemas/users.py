from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserRequest(BaseModel):
    """
    用户登录请求参数
    """
    username: str = Field(..., description="用户名", max_length=50)
    password: str = Field(..., description="密码", max_length=100)

class SysUserBase(BaseModel):
    """
    用户信息基础数据模型
    """
    """
        系统用户基础模型
        包含核心业务字段，被其他模型继承
        """
    username: str = Field(
        ...,
        description="用户名",
        max_length=50
    )
    # password: str = Field(
    #     ...,
    #     description="密码(加密)",
    #     max_length=100
    # )
    real_name: Optional[str] = Field(
        None,
        description="真实姓名",
        max_length=50
    )
    email: Optional[str] = Field(
        None,
        description="邮箱",
        max_length=100
    )
    phone: Optional[str] = Field(
        None,
        description="手机号",
        max_length=20
    )
    avatar: Optional[str] = Field(
        None,
        description="头像URL",
        max_length=500
    )
    status: int = Field(
        default=1,
        description="状态：1-正常 0-禁用"
    )
    last_login_time: Optional[datetime] = Field(
        None,
        description="最后登录时间"
    )

# sys_user对应完整模型：包含了用户信息基础类SysUserBase
class SysUser(SysUserBase):
    """
    系统用户完整模型
    用途：数据库查询后返回的完整对象映射
    包含所有数据库字段
    """
    id: int = Field(..., description="主键ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        # 核心配置：支持从 ORM 模型（如 SQLAlchemy）直接转换
        from_attributes = True

# data 数据类型
class UserAuthResponse(BaseModel):
    token: str
    user_info: SysUser = Field(..., alias="userInfo")

    # 模型配置类
    model_config = ConfigDict(
        populate_by_name=True, # 使用别名兼容
        from_attributes=True # 允许从ORM对象中获取属性值
    )


class SysUserCreate(SysUserBase):
    """
    系统用户创建模型
    用途：前端创建用户时传入的参数
    排除：数据库自动生成的字段（id/created_at/updated_at）
    """
    pass

# 更新用户信息的模型类
class SysUserUpdate(BaseModel):
    """
    系统用户更新模型
    用途：前端修改用户信息时传入的参数
    所有字段均为可选（只更新需要修改的字段）
    """
    username: Optional[str] = Field(None, description="用户名", max_length=50)
    password: Optional[str] = Field(None, description="密码(加密)", max_length=100)
    real_name: Optional[str] = Field(None, description="真实姓名", max_length=50)
    email: Optional[str] = Field(None, description="邮箱", max_length=100)
    phone: Optional[str] = Field(None, description="手机号", max_length=20)
    avatar: Optional[str] = Field(None, description="头像URL", max_length=500)
    status: Optional[int] = Field(None, description="状态：1-正常 0-禁用")
    last_login_time: Optional[datetime] = Field(None, description="最后登录时间")


# 修改密码
class UpdatePasswordRequest(BaseModel):
    old_password: str = Field(..., alias="oldPassword", description="旧密码")
    new_password: str = Field(..., max_length=6, alias="newPassword", description="新密码")

