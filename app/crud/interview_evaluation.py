from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.interview_evaluation import InterviewEvaluation


async def async_create_interview_evaluation_db(db: AsyncSession, interview_summary_dict: dict) -> InterviewEvaluation:
    obj = InterviewEvaluation(**interview_summary_dict)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def async_get_interview_evaluation_by_id_db(db: AsyncSession, id: int) -> InterviewEvaluation | None:
    select_sql = select(InterviewEvaluation).where(InterviewEvaluation.id == id)
    result = await db.execute(select_sql)

    return result.scalar_one_or_none()


async def async_update_interview_evaluation_by_id_db(db: AsyncSession, id: int, update_data: dict):
    obj = await async_get_interview_evaluation_by_id_db(db, id)

    if not obj:
        return

    for k, v in update_data.items():
        setattr(obj, k, v)

    await db.commit()
    await db.refresh(obj)
    return obj


async def async_get_interview_evaluation_list_db_by_resume_id(resume_id, db) -> Sequence[InterviewEvaluation] | None:
    select_sql = select(InterviewEvaluation).where(InterviewEvaluation.resume_id == resume_id).order_by(InterviewEvaluation.created_at.desc())
    result = await db.execute(select_sql)

    return result.scalars().all()

async def async_get_interview_evaluation_list_db_by_resume_ids(resume_ids: list[int], db: AsyncSession) -> Sequence[InterviewEvaluation] | None:
    """
    根据resume_ids条件，查询所有面试评价记录（多个resume_id对应的记录）。
    并且保证每个resume_id只有一条记录（最新的created_at时间的记录）
    :param resume_ids:
    :param db:
    :return:
    """
    subquery = (
        select(InterviewEvaluation.resume_id, func.max(InterviewEvaluation.created_at).label("created_at"))
        .where(InterviewEvaluation.resume_id.in_(resume_ids))
        .group_by(InterviewEvaluation.resume_id)
        .subquery()
    )

    # join：表示内连接
    # .c：表示columns的缩写
    select_sql = (
        select(InterviewEvaluation)
        .join(
            subquery,
            (InterviewEvaluation.resume_id == subquery.c.resume_id) &
            (InterviewEvaluation.created_at == subquery.c.created_at)
        ).order_by(InterviewEvaluation.resume_id)
    )
    result = await db.execute(select_sql)

    return result.scalars().all()