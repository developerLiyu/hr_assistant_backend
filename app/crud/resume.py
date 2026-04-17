from collections.abc import Sequence
from typing import Dict, Any, Optional, List

from sqlalchemy import bindparam, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.position import JobPosition
from app.models.resume import Resume
from app.schemas.resume import ResumeListQuery


async def async_create_resume_db(db: AsyncSession, data: Dict[str, Any]) -> Resume:
    """异步创建简历"""
    obj = Resume(**data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def async_get_resume_by_id_db(db: AsyncSession, resume_id: int) -> Optional[Resume]:
    """异步根据ID查询简历"""
    res = await db.execute(select(Resume).where(Resume.id == resume_id, Resume.is_deleted == 0))
    return res.scalar_one_or_none()



async def async_get_resume_by_ids_db(db: AsyncSession, resume_ids: list[int]) -> Optional[Sequence[Resume]]:
    """异步根据简历id列表查询简历集合"""
    if not resume_ids:
        return None

    base_sql = select(Resume).where(Resume.id.in_(resume_ids), Resume.is_deleted == 0)
    result = await db.execute(base_sql)
    return result.scalars().all()



async def async_update_parse_db(db: AsyncSession, resume_id: int, data: Dict[str, Any]):
    """异步更新解析数据"""
    obj = await async_get_resume_by_id_db(db, resume_id)
    if not obj:
        return
    for k, v in data.items():
        setattr(obj, k, v)
    await db.commit()

async def async_batch_update_parse_db(db: AsyncSession, resume_ids: list[int], data: Dict[str, Any]):
    """异步批量更新解析数据"""
    if not resume_ids:
        return

    # 获取查询结果，添加行级锁，防止并发修改，保证原子性
    result = await db.execute(
        select(Resume)
        .where(Resume.id.in_(resume_ids), Resume.is_deleted == 0)
        .with_for_update() # 添加行级锁
    )
    resumes = result.scalars().all()

    for resume in resumes:
        for k, v in data.items():
            setattr(resume, k, v)

    await db.commit()


async def async_update_milvus_id_db(db: AsyncSession, resume_id: int, milvus_id: str):
    """异步更新简历的Milvus ID"""
    obj = await async_get_resume_by_id_db(db, resume_id)
    if not obj:
        return
    obj.milvus_id = milvus_id
    await db.commit()



async def async_get_resume_list_db(query: ResumeListQuery, db: AsyncSession):
    """
    查询简历列表
    :param query:
    :param db:
    :return:
    """
    base_query = (select(Resume, JobPosition.position_name)
                  .outerjoin(JobPosition, JobPosition.id == Resume.position_id)
                  .where(Resume.is_deleted == 0))

    if query.keyword:
        base_query = base_query.where(Resume.candidate_name.like(bindparam("keyword", f"%{query.keyword}%")))
    if query.position_id:
        base_query = base_query.where(Resume.position_id == query.position_id)
    if query.education:
        base_query = base_query.where(Resume.education == query.education)
    if query.work_years_min:
        base_query = base_query.where(Resume.work_years >= query.work_years_min)
    if query.work_years_max:
        base_query = base_query.where(Resume.work_years <= query.work_years_max)
    if query.status:
        base_query = base_query.where(Resume.status == query.status)

    # 查询满足条件的总数
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0

    # 分页查询结果
    page = query.page
    page_size = query.page_size
    offset = (page - 1) * page_size
    data_query = base_query.offset(offset).limit(page_size)
    data_result = await db.execute(data_query)
    data = data_result.all()

    return {
        "total": total_count,
        "data": data
    }


async def async_get_resume_detail_db(id: int, db: AsyncSession):
    base_sql = (select(Resume, JobPosition.position_name)
                .outerjoin(JobPosition, JobPosition.id == Resume.position_id)
                .where(Resume.id == id, Resume.is_deleted == 0))
    result = await db.execute(base_sql)
    return result.scalar_one_or_none()

