from pydantic import BaseModel, computed_field
from typing import Optional, List


# ------------------------------
# 匹配接口 - 请求模型
# ------------------------------
class ScreeningMatchFilters(BaseModel):
    """匹配筛选条件"""
    min_education: Optional[str] = None
    min_work_years: Optional[int] = None
    required_skills: Optional[List[str]] = []


class ScreeningMatchRequest(BaseModel):
    """简历匹配接口请求体"""
    position_id: Optional[int] = None # 岗位匹配筛选
    query: Optional[str] = None # 自定义筛选
    top_n: int
    filters: Optional[ScreeningMatchFilters] = None


# ------------------------------
# 匹配接口 - 响应模型
# ------------------------------
class PositionInfo(BaseModel):
    """岗位信息（响应体中）"""
    id: int
    name: str


class MatchAnalysis(BaseModel):
    """匹配分析详情"""
    match_advantages: List[str] = [] #  匹配优势
    match_weaknesses: List[str] = [] #  匹配劣势
    overall_comment: Optional[str] = None # 匹配综合评语
    interview_suggestions: List[str] = [] # 面试建议


class MatchedResume(BaseModel):
    """匹配的简历项"""
    resume_id: Optional[int] = None
    position_id: Optional[int] = None
    candidate_name: Optional[str] = None
    education: Optional[str] = None
    school: Optional[str] = None
    work_years: Optional[int] = None
    current_position: Optional[str] = None
    current_company: Optional[str] = None
    resume_summary: Optional[str] = None
    skills: List[str] = []
    match_score: Optional[int] = None
    similarity: Optional[float] = None
    # recommendation: Optional[str] = None # 匹配推荐等级（不过和下面声明的@computed_field计算字段不能共存）
    match_analysis: Optional[MatchAnalysis] = None

    class Config:
        from_attributes = True  # 对齐参考代码的ORM适配配置

    @computed_field
    @property
    def recommendation(self) -> str:
        """根据匹配分数计算推荐等级"""
        if self.match_score and self.match_score >= 85:
            return "强烈推荐"
        elif self.match_score and self.match_score >= 70:
            return "推荐"
        elif self.match_score and self.match_score >= 55:
            return "一般"
        else:
            return "不推荐"


class ScreeningMatchDataResponse(BaseModel):
    """匹配响应数据体"""
    position: Optional[PositionInfo] = None
    query: Optional[str] = None
    total_matched: int
    results: List[MatchedResume] = []

    # class Config:
    #     from_attributes = True  # 对齐参考代码的ORM适配配置