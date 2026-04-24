from typing import Sequence

from sqlalchemy import select
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