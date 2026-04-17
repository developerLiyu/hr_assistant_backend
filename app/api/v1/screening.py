from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db_config import get_db
from app.schemas.screening import ScreeningMatchDataResponse, ScreeningMatchRequest
from app.services import screening

router = APIRouter(prefix="/api/v1/screening", tags=["智能简历筛选"])

# 岗位匹配筛选接口
@router.post("/match", summary="岗位匹配筛选")
async def resume_match_by_position(
        request: ScreeningMatchRequest,
        db: AsyncSession = Depends(get_db)
):
    return await screening.resume_match_by_position_service(request, db)

# 岗位匹配筛选接口
@router.post("/custom", summary="自定义筛选")
async def resume_match_by_query(
        request: ScreeningMatchRequest,
        db: AsyncSession = Depends(get_db)
):
    return await screening.resume_match_by_query_service(request, db)


@router.patch("/batch-mark", summary="批量标记筛选结果")
async def batch_mark(
                 resume_ids: str = Query(..., description="简历id字符串  用英文逗号分隔"),
                 status: int = Query(..., description="状态：1-待筛选 2-初筛通过 3-面试中 4-已录用 5-已淘汰"),
                 db: AsyncSession = Depends(get_db)):
    response = await screening.batch_mark_service(resume_ids, status, db)
    return response



