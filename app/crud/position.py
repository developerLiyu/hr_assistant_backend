from sys import exc_info

from sqlalchemy import select, bindparam, func, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.position import JobPosition
from app.schemas.position import PositionCreate
from app.utils.logger_handler import logger


async def create(position_data: PositionCreate, db: AsyncSession):
    """
    创建岗位
    """
    position_orm = JobPosition(**position_data.model_dump())
    db.add(position_orm)
    await db.commit()
    await db.refresh(position_orm)

    return position_orm


async def get_position_by_name_and_department(position_name: str, department: str, db: AsyncSession):
    """
    查询岗位信息
    :param position_name: 岗位名称
    :param department: 所属部门
    :param db:
    :return:
    """
    base_query = (select(JobPosition)
                  .where(JobPosition.position_name == position_name, JobPosition.department == department, JobPosition.is_deleted == 0))
    orm_obj = await db.execute(base_query)
    return orm_obj.scalar_one_or_none()


async def get_list(keyword, department, status, page, page_size, db):

    base_query = (select(JobPosition)
                  .where(JobPosition.is_deleted == 0))
    if keyword:
        base_query = base_query.where(JobPosition.position_name.like(bindparam("keyword", f"%{keyword}%")))
    if department:
        base_query = base_query.where(JobPosition.department == department)
    if status:
        base_query = base_query.where(JobPosition.status == status)

    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0

    # 分页查询结果
    offset = (page - 1) * page_size
    data_query = base_query.offset(offset).limit(page_size)
    data_result = await db.execute(data_query)
    data = data_result.scalars().all()

    return {
        "total": total_count,
        "data": data
    }


async def get_position_by_id(id, db):
    base_query = select(JobPosition).where(JobPosition.id == id, JobPosition.is_deleted == 0)
    orm_obj = await db.execute(base_query)

    return orm_obj.scalar_one_or_none()


async def update_data(request_data, db):
    """
    更新岗位
    """
    position_obj = await get_position_by_id(request_data.id, db)
    # if position_obj is None:
    #     return None

    # 更新字段值
    # exclude={"id"}：忽略 id 字段
    # exclude_unset=True：忽略未设置值的字段
    # exclude_none=True：忽略值为 None 的字段
    update_data_dict = request_data.model_dump(exclude={"id"}, exclude_unset=True, exclude_none=True)
    for key, value in update_data_dict.items():
        setattr(position_obj, key, value)

    # 提交事务
    await db.commit()
    # 刷新对象，获取更新后的对象
    await db.refresh(position_obj)

    return position_obj


async def delete(id, db):
    """
    删除岗位（软删除）
    """
    position_obj = await get_position_by_id(id, db)
    if position_obj is None:
        return False

    position_obj.is_deleted = 1

    await db.commit()
    await db.refresh(position_obj)

    return True


async def update_status(id, status, db):
    """
    更新岗位状态
    :param id: 岗位id
    :param status: 岗位装填
    :param db: AsyncSession
    :return: 返回更新之后的对象、影响行数
    """
    try:
        stmt = update(JobPosition).where(JobPosition.id == id, JobPosition.is_deleted == 0).values(status=status)
        result = await db.execute(stmt)
        # print(f"===================={type(result)}")
        # 获取更新行数
        affected_rows = result.rowcount
        if affected_rows == 0:
            return None, 0

        # 提交事务
        await db.commit()

        # 查询更新后的对象
        position_obj = await get_position_by_id(id, db)
        return position_obj, affected_rows

    except Exception as e:
        await db.rollback()
        logger.error(
            f"更新岗位状态失败 - ID: {id}, 目标状态：{status}, 错误：{e}",
            extra={"id": id, "target_status": status},
            exc_info=True  # 关键：这会记录完整堆栈
        )
        raise




