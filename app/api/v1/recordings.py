from typing import Optional
from datetime import date
from fastapi import APIRouter, UploadFile, File, Query, Path, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_config import get_db
from app.schemas.recording import (
    RecordingUploadResponse,
    TranscribeResponse,
    TranscriptStatusResponse,
    TranscriptResponse,
    RecordingListQuery,
    RecordingListResponse,
    RecordingDetailResponse
)
from app.services.recording import (
    async_upload_recording_service,
    async_get_recording_list_service,
    async_get_recording_detail_service,
    async_delete_recording_service,
    async_start_transcribe_service,
    async_get_transcript_status_service,
    async_get_transcript_service,
    async_update_transcript_service,
    async_process_transcription_task
)
from app.utils.response import response

router = APIRouter(prefix="/api/v1/recordings", tags=["录音管理模块"])


@router.post("/upload", summary="上传录音")
async def upload_recording(
    file: UploadFile = File(..., description="音频文件"),
    resume_id: int = Form(..., description="关联候选人ID"),
    position_id: Optional[int] = Form(None, description="关联岗位ID"),
    interview_date: Optional[date] = Form(None, description="面试日期"),
    interviewer: Optional[str] = Form(None, description="面试官姓名"),
    db: AsyncSession = Depends(get_db)
):
    """
    上传录音文件
    支持格式：MP3, WAV, M4A, AAC
    """
    return await async_upload_recording_service(
        file=file,
        resume_id=resume_id,
        position_id=position_id,
        interview_date=str(interview_date) if interview_date else None,
        interviewer=interviewer,
        db=db
    )


@router.get("/", summary="获取录音列表")
async def get_recording_list(
    resume_id: Optional[str] = Query(None, description="关联简历ID"),
    position_id: Optional[str] = Query(None, description="关联岗位ID"),
    interviewer: Optional[str] = Query(None, description="面试官姓名（模糊匹配）"),
    transcript_status: Optional[str] = Query(None, description="转写状态"),
    interview_date_start: Optional[date] = Query(None, description="面试开始日期"),
    interview_date_end: Optional[date] = Query(None, description="面试结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """获取录音列表"""
    query = RecordingListQuery(
        resume_id=resume_id,
        position_id=position_id,
        interviewer=interviewer,
        transcript_status=transcript_status,
        interview_date_start=interview_date_start,
        interview_date_end=interview_date_end,
        page=page,
        page_size=page_size
    )
    return await async_get_recording_list_service(query, db)



@router.get("/{id}", summary="获取录音详情")
async def get_recording_detail(
    id: int = Path(..., description="录音ID"),
    db: AsyncSession = Depends(get_db)
):
    """获取录音详情"""
    return await async_get_recording_detail_service(id, db)


@router.post("/{id}/transcribe", summary="语音转写")
async def start_transcribe(
    id: int = Path(..., description="录音ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    开始语音转文字
    调用Qwen3-ASR-Flash进行转写
    """
    # 开始转写
    start_response = await async_start_transcribe_service(id, db)

    # # 如果成功启动转写，在后台异步处理
    # # 注意：这里使用fire-and-forget模式，实际生产环境建议使用Celery等任务队列
    # import asyncio
    # asyncio.create_task(async_process_transcription_task(id, db))

    return start_response


@router.get("/{id}/status", summary="获取转写状态")
async def get_transcript_status(
    id: int = Path(..., description="录音ID"),
    db: AsyncSession = Depends(get_db)
):
    """查询转写状态"""
    return await async_get_transcript_status_service(id, db)


@router.get("/{id}/transcript", summary="获取文字稿")
async def get_transcript(
    id: int = Path(..., description="录音ID"),
    db: AsyncSession = Depends(get_db)
):
    """获取文字稿"""
    return await async_get_transcript_service(id, db)


@router.put("/{id}/transcript", summary="更新文字稿")
async def update_transcript(
    id: int = Path(..., description="录音ID"),
    transcript: str = Query(..., description="文字稿内容"),
    db: AsyncSession = Depends(get_db)
):
    """编辑文字稿"""
    return await async_update_transcript_service(id, transcript, db)


@router.delete("/{id}", summary="删除录音")
async def delete_recording(
    id: int = Path(..., description="录音ID"),
    db: AsyncSession = Depends(get_db)
):
    """删除录音"""
    return await async_delete_recording_service(id, db)
