from typing import Dict, Any, Optional, List
from collections.abc import Sequence

from sqlalchemy import bindparam, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.interview_question import InterviewQuestion
from app.models.position import JobPosition
from app.models.resume import Resume
from app.schemas.interview_question import QuestionListQuery


async def async_create_question_db(db: AsyncSession, data: Dict[str, Any]) -> InterviewQuestion:
    """异步创建面试题"""
    obj = InterviewQuestion(**data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def async_create_questions_batch_db(db: AsyncSession, data_list: List[Dict[str, Any]]) -> List[InterviewQuestion]:
    """异步批量创建面试题"""
    objects = [InterviewQuestion(**data) for data in data_list]
    db.add_all(objects)
    await db.commit()
    for obj in objects:
        await db.refresh(obj)
    return objects


async def async_get_question_by_id_db(db: AsyncSession, question_id: int) -> Optional[InterviewQuestion]:
    """异步根据ID查询面试题"""
    res = await db.execute(select(InterviewQuestion).where(InterviewQuestion.id == question_id))
    return res.scalar_one_or_none()


async def async_get_questions_by_ids_db(db: AsyncSession, question_ids: List[int]) -> Optional[Sequence[InterviewQuestion]]:
    """异步根据题目id列表查询题目集合"""
    if not question_ids:
        return None
    base_sql = select(InterviewQuestion).where(InterviewQuestion.id.in_(question_ids))
    result = await db.execute(base_sql)
    return result.scalars().all()


async def async_update_question_db(db: AsyncSession, question_id: int, data: Dict[str, Any]) -> Optional[InterviewQuestion]:
    """异步更新面试题"""
    obj = await async_get_question_by_id_db(db, question_id)
    if not obj:
        return None
    for k, v in data.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


async def async_delete_question_db(db: AsyncSession, question_id: int) -> bool:
    """异步删除面试题"""
    obj = await async_get_question_by_id_db(db, question_id)
    if not obj:
        return False
    await db.delete(obj)
    await db.commit()
    return True


async def async_get_question_list_db(query: QuestionListQuery, db: AsyncSession):
    """
    查询面试题列表
    :param query: 查询参数
    :param db: 数据库会话
    :return: 包含总数和数据的字典
    """
    base_query = (
        select(InterviewQuestion, JobPosition.position_name, Resume.candidate_name)
        .outerjoin(JobPosition, JobPosition.id == InterviewQuestion.position_id)
        .outerjoin(Resume, Resume.id == InterviewQuestion.resume_id)
    )

    if query.position_id:
        base_query = base_query.where(InterviewQuestion.position_id == query.position_id)
    if query.resume_id:
        base_query = base_query.where(InterviewQuestion.resume_id == query.resume_id)
    if query.question_type_str:
        # 转换成列表，用于查询
        question_type_list = query.question_type_str.split(",")
        base_query = base_query.where(InterviewQuestion.question_type.in_(question_type_list))
    if query.difficulty_str:
        difficulty_list = query.difficulty_str.split(",")
        base_query = base_query.where(InterviewQuestion.difficulty.in_(difficulty_list))
    if query.is_saved:
        base_query = base_query.where(InterviewQuestion.is_saved == query.is_saved)

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


async def async_get_question_detail_db(question_id: int, db: AsyncSession):
    """
    查询面试题详情
    :param question_id: 题目ID
    :param db: 数据库会话
    :return: 题目详情
    """
    base_sql = (
        select(InterviewQuestion, JobPosition.position_name, Resume.candidate_name)
        .outerjoin(JobPosition, JobPosition.id == InterviewQuestion.position_id)
        .outerjoin(Resume, Resume.id == InterviewQuestion.resume_id)
        .where(InterviewQuestion.id == question_id)
    )
    result = await db.execute(base_sql)
    return result.scalar_one_or_none()


async def async_update_question_saved_db(db: AsyncSession, question_id: int, is_saved: int) -> Optional[InterviewQuestion]:
    """异步更新题目保存状态"""
    obj = await async_get_question_by_id_db(db, question_id)
    if not obj:
        return None
    obj.is_saved = is_saved
    await db.commit()
    await db.refresh(obj)
    return obj
