from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Query, Path, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_config import get_db
from app.schemas.resume import BatchUploadResponse, ParseResponse, ResumeListQuery, ResumeListResponse
from app.services.resume import async_upload_service, async_parse_service, get_list_service, get_detail_service, \
    delete_service, bind_position_service, update_status_service, download_resume_service, batch_download_resume_service

router = APIRouter(prefix="/api/v1/resumes", tags=["简历管理"])

# 上传接口
# 流程
# 上传多个文件(pdf、doc、docx、zip) -> 校验文件格式及大小 -> 读取文件内容 ->
# 调用大模型解析，提取结构化内容 -> 添加简历表数据（文件信息数据） ->
# 简历内容数据向量化并存入向量库 -> 更新简历表记录（简历提取的结构化数据以及对应的向量id）
@router.post("/upload", response_model=BatchUploadResponse, summary="上传简历")
async def upload_resumes(
    files: List[UploadFile] = File(..., description="上传文件信息"),
    position_id: Optional[int] = Query(None, description="关联岗位ID"),
    db: AsyncSession = Depends(get_db)
):
    return await async_upload_service(files, position_id, db)

# 解析接口
@router.put("/reparse/{resume_id}", response_model=ParseResponse, summary="重新解析简历")
async def parse_resume(
    resume_id: int = Path(...),
    db: AsyncSession = Depends(get_db)
):
    return await async_parse_service(resume_id, db, reparse_flag=True)



@router.post("/list", response_model=ResumeListResponse, summary="查询简历列表")
async def get_list(
    query: ResumeListQuery,
    db: AsyncSession = Depends(get_db)
):
    return await get_list_service(query, db)


@router.get("/detail/{id}", summary="获取简历详情")
async def get_detail(id: int = Path(..., description="简历id"),
                   db: AsyncSession = Depends(get_db)):
    """
    简历详情
    """
    response = await get_detail_service(id, db)
    return response

@router.delete("/delete/{id}", summary="删除简历")
async def delete(id: int = Path(..., description="简历id"),
                   db: AsyncSession = Depends(get_db)):
    response = await delete_service(id, db)
    return response

@router.put("/bind_position/{id}", summary="关联岗位")
async def bind_position(id: int = Path(..., description="简历id"),
                 position_id: int = Query(..., description="关联岗位ID"),
                 db: AsyncSession = Depends(get_db)):
    response = await bind_position_service(id, position_id, db)
    return response


@router.patch("/status/{id}", summary="更新简历状态")
async def update_status(id: int = Path(..., description="简历id"),
                 status: int = Query(..., description="状态：1-待筛选 2-初筛通过 3-面试中 4-已录用 5-已淘汰"),
                 db: AsyncSession = Depends(get_db)):
    response = await update_status_service(id, status, db)
    return response

@router.get("/download/{id}", summary="单个简历下载")
async def download_resume(id: int = Path(..., description="简历id"),
                 db: AsyncSession = Depends(get_db)):
    response = await download_resume_service(id, db)
    return response

@router.get("/batch-download", summary="批量下载简历（ZIP）")
async def batch_download_resume(
        ids: list[int] = Query(..., description="简历id列表"),
        db: AsyncSession = Depends(get_db)):
    response = await batch_download_resume_service(ids, db)
    return response

