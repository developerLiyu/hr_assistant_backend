from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse

from app.core.db_config import get_db
from app.schemas.interview_question import (
    QuestionGenerateRequest,
    QuestionListQuery,
    QuestionUpdateRequest,
    QuestionSaveToBankRequest
)
from app.services import interview_question as service
from app.utils.response import response

router = APIRouter(prefix="/api/v1/questions", tags=["面试题生成"])


@router.post("/generate", summary="生成面试题")
async def generate_questions(
    request: QuestionGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    生成面试题
    - mode: position(基于岗位) / resume(基于简历) / mixed(混合)
    - position_id: 岗位ID
    - resume_id: 简历ID
    - question_types: 题目类型列表 ["technical", "behavioral", "situational", "open"]
    - difficulty: 难度 junior/middle/senior
    - count: 生成数量
    - with_answer: 是否包含参考答案
    """
    return await service.generate_questions_service(request, db)


@router.get("/list", summary="获取题目列表")
async def get_questions_list(
    position_id: str = Query(None, description="岗位ID"),
    resume_id: str = Query(None, description="简历ID"),
    question_type_str: str = Query(None, description="题目类型"),
    difficulty_str: str = Query(None, description="难度"),
    is_saved: str = Query(None, description="是否保存"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """获取题目列表"""
    query = QuestionListQuery(
        position_id=position_id,
        resume_id=resume_id,
        question_type_str=question_type_str,
        difficulty_str=difficulty_str,
        is_saved=is_saved,
        page=page,
        page_size=page_size
    )
    result = await service.get_list_service(query, db)
    return response(code=0, message="success", data=result)


@router.get("/{question_id}", summary="获取题目详情")
async def get_question_detail(
    question_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取题目详情"""
    return await service.get_detail_service(question_id, db)


@router.put("/{question_id}", summary="编辑题目")
async def update_question(
    question_id: int,
    request: QuestionUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    编辑题目
    - question_content: 题目内容
    - reference_answer: 参考答案
    - scoring_points: 评分要点
    - difficulty: 难度
    - question_type: 题目类型
    """
    return await service.update_service(question_id, request, db)


@router.delete("/{question_id}", summary="删除题目")
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除题目"""
    return await service.delete_service(question_id, db)


@router.post("/save-to-bank", summary="保存到题库")
async def save_to_bank(
    request: QuestionSaveToBankRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    批量保存题目到题库
    - question_ids: 题目ID列表
    """
    return await service.save_to_bank_service(request, db)
