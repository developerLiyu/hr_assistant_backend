import json
import os
import uuid
import math
import subprocess
from datetime import datetime
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from starlette.responses import JSONResponse

from app.crud.interview_summary import async_create_interview_summary_db, \
    async_get_interview_summary_by_recording_id_db, async_update_interview_summary_by_id_db, \
    async_get_interview_summary_by_id_db
from app.crud.recording import async_get_recording_info_by_id_db
from app.schemas.interview_summary import InterviewSummaryResponse, InterviewSummaryRequest
from app.utils import file_util, oss_util, path_tool
from app.utils.llm_util import generate_interview_summary_by_recording, generate_interview_summary_by_summary_info
from app.utils.response import response
from app.utils.logger_handler import logger


async def generate_service(recording_id: int, db: AsyncSession, id: int = None) -> JSONResponse | None:
    try:
        # 获取录音信息（包含候选人姓名、应聘岗位名称信息）
        recording_info = await async_get_recording_info_by_id_db(db, recording_id)
        if not recording_info:
            return response(code=404, message="录音信息不存在", data=None)

        recording, candidate_name, position_name = recording_info

        # 获取录音转文字信息
        transcript = recording.transcript
        # 录音时长，转成分钟
        duration = math.ceil(recording.duration / 60)

        # 调用模型获取结构化数据（分段处理）
        summary_response_arr = []
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=10000,  # 每个文本块的最大字符数。面试对话可能较长，适当增大
            chunk_overlap=300,  # 相邻文本块之间的重叠字符数。增加重叠，保持对话连贯性
            separators=["\n\n", "\n", "。", "！", "？", " ", ""]  # 分割符优先级列表，按顺序尝试使用这些分隔符进行切分。加入中文标点
        )
        chunks = text_splitter.split_text(transcript)
        for chunk in chunks:
            summary_response = await generate_interview_summary_by_recording(duration, candidate_name, position_name, chunk)
            if summary_response:
                summary_response_arr.append(summary_response)

        # 汇总所有面试摘要
        all_summary_info = "\n\n".join(
            # mode="json"和exclude_none=True：转换成JSON对象（即字典），并格式化输出，排除值为None的字段
            # indent=4和ensure_ascii=False：格式化输出（缩进4个字符），并确保字符编码为UTF-8（即可以有中文字符）
            [f"【分段摘要{index+1}】\n{json.dumps(summary_response.model_dump(mode="json", exclude_none=True), indent=4, ensure_ascii=False)}"
             for index, summary_response in enumerate(summary_response_arr)
            ]
        )
        final_summary_response = await generate_interview_summary_by_summary_info(duration, candidate_name, position_name, all_summary_info)
        if not final_summary_response:
            return response(code=500, message="生成面试摘要失败", data=None)

        # 处理结构化数据保存入库
        summary_dict = final_summary_response.model_dump(mode="json", exclude={"id", "created_at", "updated_at"}, exclude_none=True)
        summary_dict["recording_id"] = recording.id
        summary_dict["resume_id"] = recording.resume_id

        # 将列表字段转换为JSON字符串（数据库字段类型是text）
        import json as json_module
        for field in ["highlights", "concerns", "candidate_questions"]:
            if field in summary_dict and isinstance(summary_dict[field], list):
                summary_dict[field] = json_module.dumps(summary_dict[field], ensure_ascii=False)

        summary_info = None
        if not id:
            # 新增面试摘要
            summary_info = await async_create_interview_summary_db(db, summary_dict)
        else:
            # 更新面试摘要
            summary_info = await async_update_interview_summary_by_id_db(db, id, summary_dict)

        return response(code=0, message="success", data=InterviewSummaryResponse.model_validate(summary_info))

        # # 组装返回数据 - 处理TEXT字段的JSON字符串反序列化
        # response_dict = {
        #     "id": summary_info.id,
        #     "recording_id": summary_info.recording_id,
        #     "resume_id": summary_info.resume_id,
        #     "summary_overview": summary_info.summary_overview,
        #     "key_qa": summary_info.key_qa,
        #     "technical_skills": summary_info.technical_skills,
        #     "soft_skills": summary_info.soft_skills,
        #     "created_at": summary_info.created_at,
        #     "updated_at": summary_info.updated_at,
        # }
        # for field in ["highlights", "concerns", "candidate_questions"]:
        #     field_value = getattr(summary_info, field, None)
        #     if field_value and isinstance(field_value, str):
        #         # 将字符串转换成列表
        #         try:
        #             field_value = json_module.loads(field_value)
        #         except json_module.JSONDecodeError:
        #             pass
        #
        #         response_dict[field] = field_value
        #
        #
        # return response(code=0, message="success", data=InterviewSummaryResponse.model_validate(response_dict))
    except Exception as e:
        logger.error(f"生成面试摘要失败：{e}", exc_info=True)
        return response(code=500, message="生成面试摘要失败", data=None)



async def get_interview_summary_service(recording_id: int, db: AsyncSession) -> JSONResponse | None:
    try:
        # 获取面试摘要信息
        summary_info = await async_get_interview_summary_by_recording_id_db(db, recording_id)

        # 组装返回数据
        return response(code=0, message="success", data=InterviewSummaryResponse.model_validate(summary_info))
    except Exception as e:
        logger.error(f"获取面试摘要失败：{e}", exc_info=True)
        return response(code=500, message="获取面试摘要失败", data=None)



async def update_interview_summary_service(id: int, request: InterviewSummaryRequest, db: AsyncSession) -> JSONResponse | None:
    try:
        # 获取更新信息
        data_dict = request.model_dump(mode="json", exclude_none=True)

        # 将列表字段转换为JSON字符串（数据库字段类型是text）
        import json as json_module
        for field in ["highlights", "concerns", "candidate_questions"]:
            if field in data_dict and isinstance(data_dict[field], list):
                data_dict[field] = json_module.dumps(data_dict[field], ensure_ascii=False)

        await async_update_interview_summary_by_id_db(db, id, data_dict)


        # 组装返回数据
        return response(code=0, message="更新成功")
    except Exception as e:
        logger.error(f"更新面试摘要失败：{e}", exc_info=True)
        return response(code=500, message="更新面试摘要失败", data=None)



async def regenerate_interview_summary_service(id: int, db: AsyncSession) -> JSONResponse | None:
    try:
        # 获取面试摘要信息
        interview_summary = await async_get_interview_summary_by_id_db(db, id)
        if not interview_summary:
            return response(code=404, message="面试摘要不存在", data=None)

        # 调用面试摘要生成逻辑
        return await generate_service(interview_summary.recording_id, db, id)

    except Exception as e:
        logger.error(f"重新生成面试摘要失败：{e}", exc_info=True)
        return response(code=500, message="重新生成面试摘要失败", data=None)






