from typing import Optional, List, Tuple, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.position import JobPosition
from app.models.recording import InterviewRecording
from app.models.resume import Resume
from app.schemas.recording import RecordingListQuery


async def async_create_recording_db(db: AsyncSession, data: dict) -> InterviewRecording:
    """异步创建录音记录"""
    obj = InterviewRecording(**data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def async_get_recording_by_id_db(db: AsyncSession, recording_id: int) -> Optional[InterviewRecording]:
    """异步根据ID查询录音"""
    res = await db.execute(select(InterviewRecording).where(InterviewRecording.id == recording_id))
    return res.scalar_one_or_none()


async def async_get_recording_info_by_id_db(db: AsyncSession, recording_id: int) -> Optional[Tuple[InterviewRecording, Optional[str], Optional[str]]]:
    """异步根据ID查询录音"""
    select_sql = (select(InterviewRecording, Resume.candidate_name, JobPosition.position_name)
                  .outerjoin(Resume, Resume.id == InterviewRecording.resume_id)
                  .outerjoin(JobPosition, JobPosition.id == InterviewRecording.position_id)
                  .where(InterviewRecording.id == recording_id)
                  )

    res = await db.execute(select_sql)
    return res.one_or_none()


async def async_update_recording_db(db: AsyncSession, recording_id: int, data: dict):
    """异步更新录音数据"""
    obj = await async_get_recording_by_id_db(db, recording_id)
    if not obj:
        return
    for k, v in data.items():
        setattr(obj, k, v)
    await db.commit()


async def async_get_recording_list_db(query: RecordingListQuery, db: AsyncSession):
    """
    查询录音列表
    :param query:
    :param db:
    :return:
    """
    base_query = select(InterviewRecording)

    if query.resume_id:
        base_query = base_query.where(InterviewRecording.resume_id == query.resume_id)
    if query.position_id:
        base_query = base_query.where(InterviewRecording.position_id == query.position_id)
    if query.interviewer:
        base_query = base_query.where(InterviewRecording.interviewer.like(f"%{query.interviewer}%"))
    if query.transcript_status is not None:
        base_query = base_query.where(InterviewRecording.transcript_status == query.transcript_status)
    if query.interview_date_start:
        base_query = base_query.where(InterviewRecording.interview_date >= query.interview_date_start)
    if query.interview_date_end:
        base_query = base_query.where(InterviewRecording.interview_date <= query.interview_date_end)

    # 查询总数
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0

    # 分页查询
    page = query.page
    page_size = query.page_size
    offset = (page - 1) * page_size
    data_query = base_query.order_by(InterviewRecording.created_at.desc()).offset(offset).limit(page_size)
    data_result = await db.execute(data_query)
    data = data_result.scalars().all()

    return {
        "total": total_count,
        "data": data
    }


async def async_delete_recording_db(db: AsyncSession, recording_id: int):
    """异步删除录音记录"""
    obj = await async_get_recording_by_id_db(db, recording_id)
    if not obj:
        return False
    await db.delete(obj)
    await db.commit()
    return True


async def async_get_recording_list_db_by_resume_id(resume_id: int, db: AsyncSession) -> Sequence[InterviewRecording]:
    """
    查询录音列表
    :param query:
    :param db:
    :return:
    """
    query_sql = select(InterviewRecording).where(InterviewRecording.resume_id == resume_id)
    result = await db.execute(query_sql)

    return result.scalars().all()

