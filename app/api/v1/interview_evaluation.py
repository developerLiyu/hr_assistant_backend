from fastapi import APIRouter, Query, Path, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db_config import get_db
from app.schemas.interview_evaluation import InterviewEvaluationRequest
from app.services import interview_evaluation
from app.utils.response import response

router = APIRouter(prefix="/api/v1/evaluations", tags=["面试评价模块"])


@router.post("/generate", summary="AI生成面试评价")
async def generate(
    summary_id: int = Query(..., description="关联摘要ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    AI生成面试评价
    """
    return await interview_evaluation.generate_service(
        summary_id=summary_id,
        db=db
    )

@router.get("/{id}", summary="获取评价详情")
async def get_interview_evaluation_detail(
    id: int = Path(..., description="面试评价ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取评价详情
    """
    return await interview_evaluation.get_interview_evaluation_detail(
        id=id,
        db=db
    )

@router.put("/{id}/hr-comment", summary="HR补充评价")
async def update_interview_evaluation(
    id: int = Path(..., description="面试评价ID"),
    request: InterviewEvaluationRequest = Body(..., description="HR补充评价"),
    db: AsyncSession = Depends(get_db)
):
    """
    更新HR补充评价
    """
    return await interview_evaluation.update_interview_evaluation(
        id=id,
        request=request,
        db=db
    )


@router.get("/history/{resumeId}", summary="评价历史")
async def get_interview_evaluation_history(
    resume_id: int = Path(..., alias="resumeId", description="关联简历ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    评价历史
    """
    return await interview_evaluation.get_interview_evaluation_history(
        resume_id=resume_id,
        db=db
    )


