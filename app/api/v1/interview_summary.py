from fastapi import APIRouter, Query, Path, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db_config import get_db
from app.schemas.interview_summary import InterviewSummaryRequest
from app.services.interview_summary import generate_service, get_interview_summary_service, \
    update_interview_summary_service, regenerate_interview_summary_service
from app.utils.response import response

router = APIRouter(prefix="/api/v1/summaries", tags=["面试摘要提取模块"])


@router.post("/generate", summary="生成摘要")
async def generate(
    recording_id: int = Query(..., description="面试录音ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    生成摘要
    """
    return await generate_service(
        recording_id=recording_id,
        db=db
    )

@router.get("/{recordingId}", summary="获取面试摘要")
async def get_interview_summary(
    recording_id: int = Path(..., alias="recordingId", description="面试录音ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取面试摘要
    """
    return await get_interview_summary_service(
        recording_id=recording_id,
        db=db
    )


@router.put("/{id}", summary="编辑摘要")
async def update_interview_summary(
    id: int = Path(..., description="面试摘要ID"),
    request: InterviewSummaryRequest = Body(..., description="面试摘要信息"),
    db: AsyncSession = Depends(get_db)
):
    """
    编辑摘要
    """
    return await update_interview_summary_service(
        id=id,
        request=request,
        db=db
    )

@router.post("/{id}/regenerate", summary="重新生成摘要")
async def regenerate_interview_summary(
    id: int = Path(..., description="面试摘要ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    编辑摘要
    """
    return await regenerate_interview_summary_service(
        id=id,
        db=db
    )




