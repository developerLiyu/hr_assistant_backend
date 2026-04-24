import logging
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.crud import interview_summary, resume, recording, position, interview_evaluation
from app.models.recording import InterviewRecording
from app.schemas.interview_evaluation import InterviewEvaluationResponse, InterviewEvaluationRequest
from app.utils import llm_util
from app.utils.response import response


async def generate_service(summary_id: int, db: AsyncSession, id: int = None) -> JSONResponse | None:
    try:
        # 获取面试摘要信息
        interview_summary_orm = await interview_summary.async_get_interview_summary_by_id_db(db, summary_id)

        # 获取候选人信息
        resume_id = interview_summary_orm.resume_id
        resume_orm = await resume.async_get_resume_by_id_db(db, resume_id)
        candidate_name = resume_orm.candidate_name

        # 获取面试录音信息（为了拿到岗位信息）
        recording_id = interview_summary_orm.recording_id
        recording_orm = await recording.async_get_recording_by_id_db(db, recording_id)
        position_id = recording_orm.position_id

        # 获取岗位信息
        position_orm = await position.get_position_by_id(position_id, db)
        position_name = position_orm.position_name
        requirements = position_orm.requirements

        # 调用LLM提取结构化数据（面试评价）
        interview_evaluation_response = await llm_util.async_generate_interview_evaluation(candidate_name, position_name, requirements, interview_summary_orm)

        # 保存面试评价信息
        interview_evaluation_response.resume_id = resume_id
        interview_evaluation_response.recording_id = recording_id
        interview_evaluation_response.summary_id = summary_id

        interview_evaluation_dict = interview_evaluation_response.model_dump(mode="json", exclude_none=True)
        interview_evaluation_orm = await interview_evaluation.async_create_interview_evaluation_db(db, interview_evaluation_dict)

        # 组装返回数据
        return response(code=0, message="success", data=InterviewEvaluationResponse.model_validate(interview_evaluation_orm))
    except Exception as e:
        logging.error(f"生成面试评价失败：{e}", exc_info=True)
        return response(code=500, message="生成面试评价失败")


async def get_interview_evaluation_detail(id: int, db: AsyncSession) -> JSONResponse | None:
    try:
        # 获取面试评价信息
        interview_evaluation_orm = await interview_evaluation.async_get_interview_evaluation_by_id_db(db, id)
        return response(code=0, message="success", data=InterviewEvaluationResponse.model_validate(interview_evaluation_orm))

    except Exception as e:
        logging.error(f"获取面试评价详情失败：{e}", exc_info=True)
        return response(code=500, message="获取面试评价详情失败")


async def update_interview_evaluation(id: int, request: InterviewEvaluationRequest, db: AsyncSession):
    try:
        # 获取面试评价信息
        update_data = request.model_dump(mode="json", exclude_none=True)
        result = await interview_evaluation.async_update_interview_evaluation_by_id_db(db, id, update_data)
        if not result:
            return response(code=500, message="更新失败")
        else:
            return response(code=0, message="更新成功")

    except Exception as e:
        logging.error(f"更新面试评价详情失败：{e}", exc_info=True)
        return response(code=500, message="更新面试评价详情失败")


async def get_interview_evaluation_history(resume_id: int, db: AsyncSession) -> JSONResponse | None:
    try:
        # 根据简历ID获取录音列表，然后组装字典  {简历ID：面试录音orm对象}
        recording_list: Sequence[InterviewRecording] = await recording.async_get_recording_list_db_by_resume_id(resume_id, db)
        recording_dict = None
        if recording_list:
            recording_dict = {item.id: item for item in recording_list}
        if not recording_dict:
            return response(code=404, message="没有面试录音信息")

        # 根据简历ID获取历史面试评价信息
        interview_evaluation_list = await interview_evaluation.async_get_interview_evaluation_list_db_by_resume_id(resume_id, db)
        if not interview_evaluation_list:
            return response(code=404, message="没有面试评价信息")

        # 补全面试评价信息
        result: list[InterviewEvaluationResponse] = []
        for item in interview_evaluation_list:
            one_response = InterviewEvaluationResponse.model_validate(item)

            interview_recording = recording_dict.get(item.recording_id)
            one_response.interviewer = interview_recording.interviewer if interview_recording else None
            one_response.interview_date = interview_recording.interview_date if interview_recording else None

            result.append(one_response)

        # 组装返回数据
        return response(code=0, message="success", data=result)

    except Exception as e:
        logging.error(f"获取历史面试评价信息失败：{e}", exc_info=True)
        return response(code=500, message="获取历史面试评价信息失败")