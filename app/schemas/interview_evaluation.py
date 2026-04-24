import json

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class InterviewEvaluationResponse(BaseModel):
    """面试评价响应模型"""
    # 全量字段
    id: Optional[int]
    resume_id: Optional[int]
    recording_id: Optional[int] = None
    summary_id: Optional[int] = None
    professional_score: int
    professional_comment: Optional[str] = None
    logic_score: int
    logic_comment: Optional[str] = None
    communication_score: int
    communication_comment: Optional[str] = None
    learning_score: int
    learning_comment: Optional[str] = None
    teamwork_score: int
    teamwork_comment: Optional[str] = None
    culture_score: int
    culture_comment: Optional[str] = None
    total_score: float
    recommendation: str
    ai_comment: Optional[str] = None
    key_strengths: Optional[list[str]] = None
    improvement_areas: Optional[list[str]] = None
    hiring_suggestion: Optional[str] = None
    hr_comment: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 面试官
    interviewer: Optional[str] = None
    # 面试日期
    interview_date: Optional[datetime] = None

    class Config:
        from_attributes = True

    # # 自动处理TEXT字段类型的JSON字符串反序列化
    # @field_validator("key_strengths", "improvement_areas", mode="before")
    # @classmethod
    # def parse_json_field(cls, value):
    #     if isinstance(value, str):
    #         try:
    #             return json.loads(value)
    #         except json.JSONDecodeError:
    #             return value
    #     return value


class InterviewEvaluationRequest(BaseModel):
    """面试评价请求模型"""
    # resume_id: Optional[int] = None
    # recording_id: Optional[int] = None
    # summary_id: Optional[int] = None
    # professional_score: Optional[int] = None
    # professional_comment: Optional[str] = None
    # logic_score: Optional[int] = None
    # logic_comment: Optional[str] = None
    # communication_score: Optional[int] = None
    # communication_comment: Optional[str] = None
    # learning_score: Optional[int] = None
    # learning_comment: Optional[str] = None
    # teamwork_score: Optional[int] = None
    # teamwork_comment: Optional[str] = None
    # culture_score: Optional[int] = None
    # culture_comment: Optional[str] = None
    # total_score: Optional[float] = None
    # recommendation: Optional[str] = None
    # ai_comment: Optional[str] = None
    # key_strengths: Optional[list[str]] = None
    # improvement_areas: Optional[list[str]] = None
    # hiring_suggestion: Optional[str] = None
    hr_comment: Optional[str] = None
