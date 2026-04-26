from typing import Optional
from fastapi import APIRouter, Query, Path, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db_config import get_db
from app.schemas.candidate_comparison import CandidateComparisonRequest
from app.services import candidate_comparison
from app.utils.response import response

router = APIRouter(prefix="/api/v1/comparison", tags=["候选人对比模块"])


@router.post("/create", summary="创建候选人对比")
async def create_comparison(
    request: CandidateComparisonRequest = Body(..., description="候选人对比信息"),
    db: AsyncSession = Depends(get_db)
):
    """
    创建候选人对比
    """
    return await candidate_comparison.create_comparison_service(request, db)

@router.post("/{id}/analyze", summary="生成AI对比分析")
async def generate_comparison_ai_analysis(
    id: int = Path(..., description="候选人对比表主键"),
    db: AsyncSession = Depends(get_db)
):
    """
    生成AI对比分析
    """
    return await candidate_comparison.generate_comparison_ai_analysis_service(id, db)


@router.get("/{id}", summary="获取对比详情")
async def get_comparison_detail(
    id: int = Path(..., description="候选人对比表主键"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取对比详情
    """
    return await candidate_comparison.get_comparison_detail_service(id, db)






@router.get("/history/list", summary="获取候选人对比列表")
async def get_history_comparison_list(
    position_id: int = Query(..., description="岗位ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取候选人对比列表
    """
    return await candidate_comparison.get_history_comparison_list_service(position_id, page, page_size, db)


@router.get("/{id}/export", summary="导出PDF报告")
async def export_comparison_pdf(
    id: int = Path(..., description="候选人对比表主键"),
    db: AsyncSession = Depends(get_db)
):
    """
    导出候选人对比PDF报告
    """
    return await candidate_comparison.export_comparison_pdf_service(id, db)


