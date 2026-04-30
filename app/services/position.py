from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import position
from app.schemas.position import PositionCreate, PositionResponse, PositionListResponse
from app.utils.response import response


async def create(request_data: PositionCreate, db: AsyncSession):
    """
    创建岗位
    :param request_data:
    :param db:
    :return:
    """
    # 校验岗位是否存在
    position_orm = await position.get_position_by_name_and_department(request_data.position_name, request_data.department, db)
    if position_orm:
        return response(code=1003, message="岗位已存在")

    # 不存在，则创建岗位
    position_orm = await position.create(request_data, db)
    return response(code=0, message="success", data=PositionResponse.model_validate(position_orm))



async def get_list(keyword, department, status, page, page_size, db):
    """
    获取岗位列表
    :param keyword: 岗位名称模糊搜索
    :param department: 部门筛选
    :param status: 状态筛选
    :param page: 页码
    :param page_size: 每页展示条数
    :param db:
    :return:
    """
    data_result = await position.get_list(keyword, department, status, page, page_size, db)
    total = data_result["total"]
    total_pages = total // page_size + (1 if total % page_size > 0 else 0)
    # 分页信息
    pagination = {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages
    }

    # 岗位列表（orm对象）
    data_orm = data_result["data"]
    # 转换为响应对象
    data_pydantic = [PositionResponse.model_validate(item) for item in data_orm]
    data = PositionListResponse(list=data_pydantic, pagination=pagination)

    return response(code=0, message="success", data=data)


async def get_detail(id, db):
    """
    获取岗位详情
    :param id:
    :param db:
    :return:
    """
    position_orm = await position.get_position_by_id(id, db)

    return response(code=0, message="success", data=PositionResponse.model_validate(position_orm))


async def update(request_data: PositionCreate, db: AsyncSession):
    """
    更新岗位
    :param request_data:
    :param db:
    :return:
    """
    # 校验岗位是否存在
    # position_orm = await position.get_position_by_name_and_department(request_data.position_name, request_data.department, db)
    # if position_orm:
    #     return response(code=1003, message="岗位已存在")

    # 不存在，则更新岗位
    position_orm = await position.update_data(request_data, db)
    return response(code=0, message="success", data=PositionResponse.model_validate(position_orm))


async def delete(id, db):
    """
    删除岗位
    :param id:
    :param db:
    :return:
    """
    delete_flag = await position.delete(id, db)
    if delete_flag:
        return response(code=0, message="success")
    else:
        return response(code=1002, message="删除失败")


async def update_status(id, status, db):

    position_orm, affect_rows = await position.update_status(id, status, db)
    if position_orm:
        return response(code=0, message="success", data=PositionResponse.model_validate(position_orm))
    else:
        return response(code=1002, message="更新失败")