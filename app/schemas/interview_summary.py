import json

from pydantic import BaseModel, computed_field, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime


# 核心问答模型
class KeyQaModel(BaseModel):
    question: str
    answer_summary: str
    answer_quality: str


class InterviewSummaryResponse(BaseModel):
    # 全量字段
    id: int
    recording_id: int
    resume_id: int
    summary_overview: str
    key_qa: Optional[list[KeyQaModel]] = None
    technical_skills: Optional[list[str]] = None
    soft_skills: Optional[list[str]] = None
    highlights: Optional[list[str]] = None
    concerns: Optional[list[str]] = None
    candidate_questions: Optional[list[str]] = None
    created_at: datetime
    updated_at: datetime

    # 严格对齐你的格式
    class Config:
        from_attributes = True

    # 自动处理TEXT字段类型的JSON字符串反序列化
    # mode="before"：设置在校验之前处理字段值
    @field_validator("highlights", "concerns", "candidate_questions", mode="before")
    @classmethod
    def parse_json_field(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    # # 计算属性
    # @computed_field
    # @property
    # def status_name(self) -> str:
    #     status_map = {1: "待筛选", 2: "初筛通过", 3: "面试中", 4: "已录用", 5: "已淘汰"}
    #     return status_map.get(self.status, "未知")


class InterviewSummaryRequest(BaseModel):
    # 全量字段
    # recording_id: Optional[int] = Field(None, description="面试录音ID") # Field表示请求体参数
    # resume_id: Optional[int] = None
    summary_overview: Optional[str] = None
    key_qa: Optional[list[KeyQaModel]] = None
    technical_skills: Optional[list[str]] = None
    soft_skills: Optional[list[str]] = None
    highlights: Optional[list[str]] = None
    concerns: Optional[list[str]] = None
    candidate_questions: Optional[list[str]] = None
    # created_at: Optional[datetime] = None
    # updated_at: Optional[datetime] = None



