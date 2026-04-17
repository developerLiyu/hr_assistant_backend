from typing import Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.db_config import get_db
from app.services import position
from app.schemas.position import PositionCreate, PositionUpdate
from app.utils.data_util import parse_optional_int

router = APIRouter(prefix="/api/v1/positions", tags=["岗位管理"])

@router.post("/create", summary="创建岗位")
async def create(request_data: PositionCreate, db: AsyncSession = Depends(get_db)):
    """
    创建岗位
    """
    response = await position.create(request_data, db)
    return response

@router.get("/list", summary="获取岗位列表")
async def get_list(keyword: Optional[str] = Query(None, description="岗位名称模糊搜索"),
                   department: Optional[str] = Query(None, description="部门筛选"),
                   status: Optional[str] = Query(None, description="状态筛选"),
                   page: int = Query(1, description="页码"),
                   page_size: int = Query(10, description="每页条数"),
                   db: AsyncSession = Depends(get_db)):
    """
    岗位列表
    """
    response = await position.get_list(keyword, department, status, page, page_size, db)
    return response

@router.get("/detail/{id}", summary="获取岗位详情")
async def get_detail(id: int = Path(..., description="岗位id"),
                   db: AsyncSession = Depends(get_db)):
    """
    创建岗位
    """
    response = await position.get_detail(id, db)
    return response


@router.put("/update", summary="更新岗位")
async def update(request_data: PositionUpdate, db: AsyncSession = Depends(get_db)):
    """
    创建岗位
    """
    response = await position.update(request_data, db)
    return response



@router.delete("/delete/{id}", summary="删除岗位")
async def delete(id: int = Path(..., description="岗位id"),
                   db: AsyncSession = Depends(get_db)):
    """
    创建岗位
    """
    response = await position.delete(id, db)
    return response


@router.patch("/{id}/status", summary="更新岗位状态")
async def update_status(id: int = Path(..., description="岗位id"),
                 status: int = Query(default=1, ge=1, le=3, description="状态：1-开放 2-暂停 3-关闭"),
                 db: AsyncSession = Depends(get_db)):
    """
    创建岗位
    """
    response = await position.update_status(id, status, db)
    return response

