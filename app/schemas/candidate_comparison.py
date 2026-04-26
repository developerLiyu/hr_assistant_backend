import json

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime


class PositionInfo(BaseModel):
    """岗位信息"""
    id: int
    name: str


class EvaluationScore(BaseModel):
    """评价分数"""
    professional_score: int = Field(..., description="专业能力评分")
    logic_score: int = Field(..., description="逻辑思维评分")
    communication_score: int = Field(..., description="沟通表达评分")
    learning_score: int = Field(..., description="学习能力评分")
    teamwork_score: int = Field(..., description="团队协作评分")
    culture_score: int = Field(..., description="文化匹配评分")
    total_score: float = Field(..., description="综合得分")


class CandidateInfo(BaseModel):
    """候选人信息"""
    resume_id: int = Field(..., description="简历ID")
    name: str = Field(..., description="姓名")
    education: Optional[str] = Field(None, description="学历")
    school: Optional[str] = Field(None, description="学校")
    work_years: Optional[int] = Field(None, description="工作年限")
    current_position: Optional[str] = Field(None, description="当前职位")
    current_company: Optional[str] = Field(None, description="当前公司")
    skills: Optional[List[str]] = Field(None, description="技能列表")
    evaluation: Optional[EvaluationScore] = Field(None, description="评价分数")
    highlights: Optional[List[str]] = Field(None, description="面试亮点")
    concerns: Optional[List[str]] = Field(None, description="面试疑虑")



class CandidateComparisonDetailResponse(BaseModel):
    """候选人对比详情响应模型"""
    id: int = Field(..., description="对比记录ID")
    position: PositionInfo = Field(..., description="岗位信息")
    candidates: List[CandidateInfo] = Field(..., description="候选人列表")



class CandidateComparisonAIAnalysis(BaseModel):
    """候选人对比AI分析结果模型（用于LLM输出）"""
    comparison_summary: str
    candidate_analysis: list[dict]
    ranking: list[dict]
    recommendation: dict
    hiring_advice: str


class CandidateComparisonResponse(BaseModel):
    """候选人对比响应模型"""
    id: int
    position_id: int
    resume_ids: list[int]
    comparison_data: Optional[dict | list] = None
    comparison_summary: Optional[str] = None
    candidate_analysis: Optional[dict | list] = None
    ranking: Optional[dict | list] = None
    recommendation: Optional[dict | list] = None
    hiring_advice: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

    # # 自动处理JSON字段类型的字符串反序列化
    # @field_validator("comparison_data", "candidate_analysis", "ranking", "recommendation", mode="before")
    # @classmethod
    # def parse_json_field(cls, value):
    #     if isinstance(value, str):
    #         try:
    #             return json.loads(value)
    #         except json.JSONDecodeError:
    #             return value
    #     return value



class CandidateComparisonRequest(BaseModel):
    """候选人对比请求模型"""
    position_id: int = Field(..., description="岗位ID")
    resume_ids: list[int] = Field(..., description="简历ID列表")



class PageInfo(BaseModel):
    """候选人对比列表响应模型"""
    page: int = Field(..., description="页数")
    page_size: int = Field(..., description="每页数量")
    total: int = Field(..., description="总记录数")
    total_pages: int = Field(..., description="总页数")



class CandidateComparisonListResponse(BaseModel):
    """候选人对比列表响应模型"""
    page_info: PageInfo = Field(..., description="分页信息")
    list: List[CandidateComparisonResponse] = Field(..., description="候选人对比信息列表")
