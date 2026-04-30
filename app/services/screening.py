import io
import os
import urllib.parse
import zipfile
from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from starlette.responses import JSONResponse, FileResponse, StreamingResponse

from app.schemas.screening import ScreeningMatchRequest, ScreeningMatchDataResponse, MatchedResume, MatchAnalysis, \
    PositionInfo
from app.utils import milvus_util, llm_util
from app.utils.response import response

from app.crud import position, resume


async def resume_match_by_position_service(request: ScreeningMatchRequest, db: AsyncSession) -> ScreeningMatchDataResponse:
    # 获取页面条件
    position_id = request.position_id
    top_n = request.top_n

    # 获取岗位要求信息（职责和要求）
    position_obj = await position.get_position_by_id(position_id, db)
    job_decription = position_obj.job_description
    requirements = position_obj.requirements
    yaoqiu_message = "\n".join([job_decription, requirements])

    # 将岗位要求信息进行向量化
    yaoqiu_message_embedding: List[float] = await milvus_util.async_generate_embedding(yaoqiu_message)

    # 在简历向量库中进行搜索，找到匹配的简历信息[{"resume_id": 简历id, "similarity": 相似度（保留4位小数）}]
    resume_info_list: List[dict] = await milvus_util.async_search_embedding(yaoqiu_message_embedding, top_n)

    # 根据简历id信息，获取简历信息
    resume_ids = []
    if resume_info_list:
        resume_ids = [resume_info["resume_id"] for resume_info in resume_info_list]

    resume_obj_list = await resume.async_get_resume_by_ids_db(db, resume_ids)

    # 将简历信息和相似度信息封装到MatchedResume模型类中，返回list[MatchedResume]
    matched_resumes: List[MatchedResume] = []

    if resume_info_list and resume_obj_list:
        # 创建简历ID到Resume对象的映射，方便快速查找
        resume_map = {resume_obj.id: resume_obj for resume_obj in resume_obj_list}

        # 按照resume_info_list的顺序（即相似度排序）构建MatchedResume列表
        for resume_info in resume_info_list:
            resume_id = resume_info["resume_id"]
            similarity = resume_info["similarity"]

            # 从映射中获取对应的简历对象
            resume_obj = resume_map.get(resume_id)
            if resume_obj:
                matched_resume = MatchedResume.model_validate(resume_obj)
                matched_resume.resume_id = resume_id
                matched_resume.similarity = similarity
                matched_resume.match_score = int(similarity * 100 * 0.6 + 40)

                matched_resumes.append(matched_resume)

    # 先过滤出指定岗位id的简历
    matched_resumes = [resume for resume in matched_resumes if resume.position_id == position_id]

    # 判断是否有过滤条件，有过滤条件过滤出符合条件的简历
    if request.filters:
        min_education = request.filters.min_education
        min_work_years = request.filters.min_work_years
        required_skills = request.filters.required_skills

        if min_education:
            # 学历筛选（博士/硕士/本科/大专）
            education_level_map = {
                "博士": 4,
                "硕士": 3,
                "本科": 2,
                "大专": 1
            }

            min_edu_level = education_level_map.get(min_education, 0)

            filtered_resumes = []
            for matched_resume in matched_resumes:
                resume_edu = matched_resume.education
                if resume_edu:
                    resume_edu_level = education_level_map.get(resume_edu, 0)
                    if resume_edu_level >= min_edu_level:
                        filtered_resumes.append(matched_resume)

            matched_resumes = filtered_resumes

        if min_work_years:
            # 最小工作年限筛选
            filtered_resumes = []
            for matched_resume in matched_resumes:
                work_years = matched_resume.work_years
                if work_years:
                    if work_years >= min_work_years:
                        filtered_resumes.append(matched_resume)

            matched_resumes = filtered_resumes

        if required_skills:
            # 技能筛选：简历技能必须包含所有必需技能
            filtered_resumes = []
            for matched_resume in matched_resumes:
                resume_skills = set(matched_resume.skills) if matched_resume.skills else set()
                required_skills_set = set(required_skills)

                # 检查简历技能是否包含所有必需技能
                if required_skills_set.issubset(resume_skills):
                    filtered_resumes.append(matched_resume)

            matched_resumes = filtered_resumes

    if matched_resumes:
        # 调用大模型生成匹配分析报告
        for matched_resume in matched_resumes:
            # 调用大模型生成匹配分析报告
            match_analysis: MatchAnalysis = await llm_util.async_qwen_get_match_analysis(matched_resume, position_obj)
            matched_resume.match_analysis = match_analysis

        # 按照匹配度排序
        matched_resumes = sorted(matched_resumes, key=lambda x: x.match_score, reverse=True)

        # 组装返回结果
        position_info = PositionInfo(id=position_obj.id, name=position_obj.position_name)
        total_matched = len(matched_resumes)
        data = ScreeningMatchDataResponse(position=position_info, total_matched=total_matched, results=matched_resumes)
        return response(code=0, message="success", data=data)

    else:
        return response(code=0, message="success", data=None)



async def resume_match_by_query_service(request: ScreeningMatchRequest, db: AsyncSession) -> ScreeningMatchDataResponse:
    # 获取页面条件
    yaoqiu_message = request.query
    top_n = request.top_n

    # 将岗位要求信息进行向量化
    yaoqiu_message_embedding: List[float] = await milvus_util.async_generate_embedding(yaoqiu_message)

    # 在简历向量库中进行搜索，找到匹配的岗位信息[{"resume_id": 简历id, "similarity": 相似度（保留4位小数）}]
    resume_info_list: List[dict] = await milvus_util.async_search_embedding(yaoqiu_message_embedding, top_n)

    # 根据简历id信息，获取简历信息
    resume_ids = []
    if resume_info_list:
        resume_ids = [resume_info["resume_id"] for resume_info in resume_info_list]

    resume_obj_list = await resume.async_get_resume_by_ids_db(db, resume_ids)

    # 将简历信息和相似度信息封装到MatchedResume模型类中，返回list[MatchedResume]
    matched_resumes: List[MatchedResume] = []

    if resume_info_list and resume_obj_list:
        # 创建简历ID到Resume对象的映射，方便快速查找
        resume_map = {resume_obj.id: resume_obj for resume_obj in resume_obj_list}

        # 按照resume_info_list的顺序（即相似度排序）构建MatchedResume列表
        for resume_info in resume_info_list:
            resume_id = resume_info["resume_id"]
            similarity = resume_info["similarity"]

            # 从映射中获取对应的简历对象
            resume_obj = resume_map.get(resume_id)
            if resume_obj:
                matched_resume = MatchedResume.model_validate(resume_obj)
                matched_resume.resume_id = resume_id
                matched_resume.similarity = similarity
                matched_resume.match_score = int(similarity * 100 * 0.6 + 40)

                matched_resumes.append(matched_resume)

    if matched_resumes:
        # 调用大模型生成匹配分析报告
        for matched_resume in matched_resumes:
            # 调用大模型生成匹配分析报告
            match_analysis: MatchAnalysis = await llm_util.async_qwen_get_match_analysis_use_custom(matched_resume, yaoqiu_message)
            matched_resume.match_analysis = match_analysis

        # 按照匹配度排序
        matched_resumes = sorted(matched_resumes, key=lambda x: x.match_score, reverse=True)

        # 组装返回结果
        total_matched = len(matched_resumes)
        data = ScreeningMatchDataResponse(query=yaoqiu_message, total_matched=total_matched, results=matched_resumes)
        return response(code=0, message="success", data=data)

    else:
        return response(code=0, message="success", data=None)



async def batch_mark_service(resume_ids: str, status: int, db: AsyncSession):
    """
    批量标记筛选结果
    :param resume_ids: 简历id字符串  用英文逗号分隔
    :param status: 状态：1-待筛选 2-初筛通过 3-面试中 4-已录用 5-已淘汰
    :param db:
    :return:
    """

    # 转换resume_ids为list[int]
    resume_id_list = [int(resume_id) for resume_id in resume_ids.split(",")]
    await resume.async_batch_update_parse_db(db, resume_id_list, {"status": status})

    return response(code=0, message="success", data=None)