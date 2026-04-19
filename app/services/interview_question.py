from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.crud import position, resume
from app.crud.interview_question import (
    async_create_questions_batch_db,
    async_get_question_by_id_db,
    async_update_question_db,
    async_delete_question_db,
    async_get_question_list_db,
    async_get_question_detail_db,
    async_update_question_saved_db,
    async_get_questions_by_ids_db
)
from app.schemas.interview_question import (
    QuestionGenerateRequest,
    QuestionGenerateResponse,
    QuestionGenerateItem,
    QuestionListQuery,
    QuestionListResponse,
    QuestionListItem,
    QuestionDetailResponse,
    QuestionUpdateRequest,
    QuestionSaveToBankRequest, convert_llm_question_to_db_data
)
from app.utils import llm_util
from app.utils.response import response


async def generate_questions_by_position(
        request: QuestionGenerateRequest,
        db: AsyncSession) -> List[QuestionGenerateItem] | None:
    """
    基于岗位生成面试题目

    Args:
        request: 题目生成请求参数
        db: 数据库会话

    Returns:
        生成的题目列表
    """
    position_id = request.position_id

    # 获取岗位信息
    position_orm = await position.get_position_by_id(position_id, db)
    if not position_orm:
        return None

    # 调用LLM生成题目（传入英文参数）
    llm_result = await llm_util.async_create_questions_by_position(
        position_orm,
        request.question_types,  # 保持英文：technical/behavioral等
        request.difficulty,  # 保持英文：junior/middle/senior
        request.count,
        request.with_answer
    )

    if not llm_result or not llm_result.questions:
        return []

    # 将LLM返回的题目转换为数据库格式
    db_data_list = []
    response_items = []

    for llm_question in llm_result.questions:
        # 转换为数据库格式
        db_data = convert_llm_question_to_db_data(
            llm_question=llm_question,
            position_id=position_id,
            resume_id=None
        )
        db_data_list.append(db_data)

    # 批量保存到数据库
    if db_data_list:
        saved_questions = await async_create_questions_batch_db(db, db_data_list)

        # 封装返回的题目数据
        response_items = [QuestionGenerateItem.model_validate(question) for question in saved_questions]

    return response_items

async def generate_questions_by_resume(
        request: QuestionGenerateRequest,
        db: AsyncSession) -> List[QuestionGenerateItem] | None:
    """
    基于基于候选人经历生成面试题目

    Args:
        request: 题目生成请求参数
        db: 数据库会话

    Returns:
        生成的题目列表
    """
    resume_id = request.resume_id

    # 获取岗位信息
    resume_orm = await resume.async_get_resume_by_id_db(db, resume_id)
    if not resume_orm:
        return None

    # 调用LLM生成题目（传入英文参数）
    llm_result = await llm_util.async_create_questions_by_resume(
        resume_orm,
        request.question_types,  # 保持英文：technical/behavioral等
        request.difficulty,  # 保持英文：junior/middle/senior
        request.count,
        request.with_answer
    )

    if not llm_result or not llm_result.questions:
        return []

    # 将LLM返回的题目转换为数据库格式
    db_data_list = []
    response_items = []

    for llm_question in llm_result.questions:
        # 转换为数据库格式
        db_data = convert_llm_question_to_db_data(
            llm_question=llm_question,
            position_id=None,
            resume_id=resume_id
        )
        db_data_list.append(db_data)

    # 批量保存到数据库
    if db_data_list:
        saved_questions = await async_create_questions_batch_db(db, db_data_list)

        # 封装返回的题目数据
        response_items = [QuestionGenerateItem.model_validate(question) for question in saved_questions]

    return response_items


async def generate_questions_mixed(
        request: QuestionGenerateRequest,
        db: AsyncSession) -> List[QuestionGenerateItem] | None:
    """
    基于岗位要求+候选人简历混合模式生成面试题目

    Args:
        request: 题目生成请求参数
        db: 数据库会话

    Returns:
        生成的题目列表
    """
    position_id = request.position_id
    resume_id = request.resume_id

    # 获取岗位信息
    position_orm = await position.get_position_by_id(position_id, db)
    if not position_orm:
        return None

    # 获取简历信息
    resume_orm = await resume.async_get_resume_by_id_db(db, resume_id)
    if not resume_orm:
        return None

    # 调用LLM生成题目（传入英文参数）
    llm_result = await llm_util.async_create_questions_mixed(
        position_orm,
        resume_orm,
        request.question_types,  # 保持英文：technical/behavioral等
        request.difficulty,  # 保持英文：junior/middle/senior
        request.count,
        request.with_answer
    )

    if not llm_result or not llm_result.questions:
        return []

    # 将LLM返回的题目转换为数据库格式
    db_data_list = []
    response_items = []

    for llm_question in llm_result.questions:
        # 转换为数据库格式
        db_data = convert_llm_question_to_db_data(
            llm_question=llm_question,
            position_id=position_id,
            resume_id=resume_id
        )
        db_data_list.append(db_data)

    # 批量保存到数据库
    if db_data_list:
        saved_questions = await async_create_questions_batch_db(db, db_data_list)

        # 封装返回的题目数据
        response_items = [QuestionGenerateItem.model_validate(question) for question in saved_questions]

    return response_items



async def generate_questions_service(
        request: QuestionGenerateRequest,
        db: AsyncSession
) -> JSONResponse:
    """
    生成面试题服务

    :param request: 生成请求参数
    :param db: 数据库会话
    :return: 生成的题目列表
    """
    mode = request.mode

    try:
        if mode == "position":
            # 实现基于岗位要求的题目生成
            if not request.position_id:
                return response(code=1002, message="岗位ID不能为空")

            questions = await generate_questions_by_position(request, db)

            if not questions:
                return response(code=1002, message="未生成出任何题目")

            return response(code=0, message="success", data={
                "questions": questions
            })

        elif mode == "resume":
            # 实现基于候选人经历的题目生成
            if not request.resume_id:
                return response(code=1002, message="简历ID不能为空")

            questions = await generate_questions_by_resume(request, db)

            if not questions:
                return response(code=1002, message="未生成出任何题目")

            return response(code=0, message="success", data={
                "questions": questions
            })

        elif mode == "mixed":
            # 实现 基于岗位要求+候选人简历 混合模式题目生成
            if not request.position_id:
                return response(code=1002, message="岗位ID不能为空")
            if not request.resume_id:
                return response(code=1002, message="简历ID不能为空")

            questions = await generate_questions_mixed(request, db)

            if not questions:
                return response(code=1002, message="未生成出任何题目")

            return response(code=0, message="success", data={
                "questions": questions
            })

        else:
            return response(code=1001, message=f"不支持的生成模式: {mode}")

    except Exception as e:
        return response(code=500, message=f"生成题目失败: {str(e)}")




async def get_list_service(
    query: QuestionListQuery,
    db: AsyncSession
) -> QuestionListResponse:
    """
    获取题目列表
    :param query: 查询参数
    :param db: 数据库会话
    :return: 题目列表
    """
    # 根据条件获取题目列表和总数
    data_result = await async_get_question_list_db(query, db)

    # 分页数据处理
    total = data_result["total"]
    total_pages = total // query.page_size + (1 if total % query.page_size > 0 else 0)
    pagination = {
        "page": query.page,
        "page_size": query.page_size,
        "total": total,
        "total_pages": total_pages
    }

    # 题目列表处理
    data = []
    if data_result["data"]:
        for item, position_name, candidate_name in data_result["data"]:
            question = QuestionListItem.model_validate(item)
            question.position_name = position_name
            question.candidate_name = candidate_name
            data.append(question)

    return QuestionListResponse(list=data, pagination=pagination)


async def get_detail_service(
    question_id: int,
    db: AsyncSession
) -> JSONResponse:
    """
    获取题目详情
    :param question_id: 题目ID
    :param db: 数据库会话
    :return: 题目详情
    """
    data_result = await async_get_question_detail_db(question_id, db)
    if not data_result:
        return response(code=1002, message="题目不存在")

    # 处理题目详情数据
    question = QuestionDetailResponse.model_validate(data_result)

    return response(code=0, message="success", data=question)


async def update_service(
    question_id: int,
    request: QuestionUpdateRequest,
    db: AsyncSession
) -> JSONResponse:
    """
    编辑题目
    :param question_id: 题目ID
    :param request: 更新请求参数
    :param db: 数据库会话
    :return: 更新结果
    """
    question = await async_get_question_by_id_db(db, question_id)
    if not question:
        return response(code=1002, message="题目不存在")

    # 过滤掉None值，只更新提供的字段
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        return response(code=1001, message="没有需要更新的字段")

    updated_question = await async_update_question_db(db, question_id, update_data)
    
    return response(code=0, message="更新成功")


async def delete_service(
    question_id: int,
    db: AsyncSession
) -> JSONResponse:
    """
    删除题目
    :param question_id: 题目ID
    :param db: 数据库会话
    :return: 删除结果
    """
    question = await async_get_question_by_id_db(db, question_id)
    if not question:
        return response(code=1002, message="题目不存在")

    await async_delete_question_db(db, question_id)
    
    return response(code=0, message="删除成功")


async def save_to_bank_service(
    request: QuestionSaveToBankRequest,
    db: AsyncSession
) -> JSONResponse:
    """
    保存到题库
    :param request: 保存请求参数
    :param db: 数据库会话
    :return: 保存结果
    """
    if not request.question_ids:
        return response(code=1001, message="题目ID列表不能为空")

    # 验证题目是否存在
    questions = await async_get_questions_by_ids_db(db, request.question_ids)
    if not questions or len(questions) != len(request.question_ids):
        return response(code=1002, message="部分题目不存在")

    # 批量更新保存状态
    for question_id in request.question_ids:
        await async_update_question_saved_db(db, question_id, 1)

    return response(code=0, message="保存成功")
