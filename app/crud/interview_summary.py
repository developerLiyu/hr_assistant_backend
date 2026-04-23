from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.interview_summary import InterviewSummary
from app.models.recording import InterviewRecording
from app.schemas.recording import RecordingListQuery




async def async_create_interview_summary_db(db: AsyncSession, data: dict) -> InterviewSummary:
    """异步创建面试摘要"""
    obj = InterviewSummary(**data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def async_get_interview_summary_by_recording_id_db(db: AsyncSession, recording_id: int) -> Optional[InterviewSummary]:
    """异步根据录音ID查询面试摘要信息"""
    res = await db.execute(select(InterviewSummary).where(InterviewSummary.recording_id == recording_id))
    return res.scalar_one_or_none()


async def async_get_interview_summary_by_id_db(db: AsyncSession, id: int) -> Optional[InterviewSummary]:
    res = await db.execute(select(InterviewSummary).where(InterviewSummary.id == id))
    return res.scalar_one_or_none()


async def async_update_interview_summary_by_id_db(db: AsyncSession, id: int, data: dict):
    """异步更新面试摘要数据"""
    obj = await async_get_interview_summary_by_id_db(db, id)
    if not obj:
        return

   # 更新数据
    for k, v in data.items():
        setattr(obj, k, v)

    await db.commit()
    await db.refresh(obj)
    return obj


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
