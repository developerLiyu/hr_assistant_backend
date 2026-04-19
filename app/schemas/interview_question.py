from pydantic import BaseModel, computed_field, Field
from typing import Optional, List
from datetime import datetime


# ------------------------------
# 1. 题目生成请求模型
# ------------------------------
class QuestionGenerateRequest(BaseModel):
    mode: str  # position/resume/mixed
    position_id: Optional[int] = None
    resume_id: Optional[int] = None
    question_types: List[str]  # ["technical", "behavioral"]
    difficulty: str  # junior/middle/senior
    count: int = 5
    with_answer: bool = True


# ------------------------------
# 2. 题目生成响应项
# ------------------------------
class QuestionGenerateItem(BaseModel):
    id: int
    question_type: str = Field(alias="type")
    # type_name: str
    difficulty: str
    # difficulty_name: str
    question_content: str = Field(alias="question")
    reference_answer: Optional[str] = None
    scoring_points: Optional[list] = None
    source: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True

    @computed_field
    @property
    def type_name(self) -> str:
        type_map = {
            "technical": "技术类",
            "behavioral": "行为类",
            "situational": "情景类",
            "open": "开放类"
        }
        return type_map.get(self.question_type, "未知")

    @computed_field
    @property
    def difficulty_name(self) -> str:
        difficulty_map = {
            "junior": "初级",
            "middle": "中级",
            "senior": "高级"
        }
        return difficulty_map.get(self.difficulty, "未知")



# ------------------------------
# 2-1. LLM返回的题目数据模型（用于解析LLM响应）
# ------------------------------
class LLMQuestionItem(BaseModel):
    """LLM生成的单道题目数据结构"""
    type: str = Field(..., description="题目类型：技术类/行为类/情景类/开放类")
    difficulty: str = Field(..., description="难度级别：初级/中级/高级")
    question: str = Field(..., description="题目内容")
    reference_answer: Optional[str] = Field(None, description="参考答案")
    scoring_points: Optional[List[str]] = Field(None, description="评分要点列表")
    source: str = Field(..., description="题目来源：基于岗位要求/基于候选人经历/基于岗位要求+候选人简历")


# ------------------------------
# 2-2. LLM返回的题目列表模型
# ------------------------------
class LLMQuestionResponse(BaseModel):
    """LLM生成的题目列表响应"""
    questions: List[LLMQuestionItem] = Field(..., description="题目列表")


# ------------------------------
# 2-3. 题目数据转换工具函数
# ------------------------------
def convert_llm_question_to_db_data(
        llm_question: LLMQuestionItem,
        position_id: Optional[int] = None,
        resume_id: Optional[int] = None
) -> dict:
    """
    将LLM返回的题目数据转换为数据库存储格式

    Args:
        llm_question: LLM返回的题目对象
        position_id: 关联的岗位ID
        resume_id: 关联的简历ID

    Returns:
        符合数据库模型的字典数据
    """
    # 类型映射：中文 -> 英文
    type_map = {
        "技术类": "technical",
        "行为类": "behavioral",
        "情景类": "situational",
        "开放类": "open"
    }

    # 难度映射：中文 -> 英文
    difficulty_map = {
        "初级": "junior",
        "中级": "middle",
        "高级": "senior"
    }

    return {
        "position_id": position_id,
        "resume_id": resume_id,
        "question_type": type_map.get(llm_question.type, "technical"),
        "difficulty": difficulty_map.get(llm_question.difficulty, "junior"),
        "question_content": llm_question.question,
        "reference_answer": llm_question.reference_answer,
        "scoring_points": llm_question.scoring_points or [],
        "source": llm_question.source,
        "is_saved": 0  # 默认未保存到题库
    }



# ------------------------------
# 3. 题目生成响应模型
# ------------------------------
class QuestionGenerateResponse(BaseModel):
    questions: List[QuestionGenerateItem]


# ------------------------------
# 4. 题目列表查询参数
# ------------------------------
class QuestionListQuery(BaseModel):
    position_id: Optional[str] = None
    resume_id: Optional[str] = None
    question_type_str: Optional[str] = None
    difficulty_str: Optional[str] = None
    is_saved: Optional[str] = None
    page: int = 1
    page_size: int = 10


# ------------------------------
# 5. 题目列表响应项
# ------------------------------
class QuestionListItem(BaseModel):
    id: int
    position_id: Optional[int]
    resume_id: Optional[int]
    question_type: str
    difficulty: str
    question_content: str = Field(alias="question")
    reference_answer: Optional[str] = None
    scoring_points: Optional[list] = None
    source: Optional[str] = None
    is_saved: int
    created_at: datetime
    # 联表字段
    position_name: Optional[str] = None
    candidate_name: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True

    @computed_field
    @property
    def type_name(self) -> str:
        type_map = {
            "technical": "技术类",
            "behavioral": "行为类",
            "situational": "情景类",
            "open": "开放类"
        }
        return type_map.get(self.question_type, "未知")

    @computed_field
    @property
    def difficulty_name(self) -> str:
        difficulty_map = {
            "junior": "初级",
            "middle": "中级",
            "senior": "高级"
        }
        return difficulty_map.get(self.difficulty, "未知")

    @computed_field
    @property
    def is_saved_name(self) -> str:
        saved_map = {0: "未保存", 1: "已保存"}
        return saved_map.get(self.is_saved, "未知")


# ------------------------------
# 6. 题目列表分页响应模型
# ------------------------------
class QuestionListResponse(BaseModel):
    list: List[QuestionListItem]
    pagination: dict[str, int]


# ------------------------------
# 7. 题目详情响应模型
# ------------------------------
class QuestionDetailResponse(BaseModel):
    id: int
    position_id: Optional[int]
    resume_id: Optional[int]
    question_type: str
    difficulty: str
    question_content: str = Field(alias="question")
    reference_answer: Optional[str] = None
    scoring_points: Optional[list] = None
    source: Optional[str] = None
    is_saved: int
    created_at: datetime
    position_name: Optional[str] = None
    candidate_name: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True

    @computed_field
    @property
    def type_name(self) -> str:
        type_map = {
            "technical": "技术类",
            "behavioral": "行为类",
            "situational": "情景类",
            "open": "开放类"
        }
        return type_map.get(self.question_type, "未知")

    @computed_field
    @property
    def difficulty_name(self) -> str:
        difficulty_map = {
            "junior": "初级",
            "middle": "中级",
            "senior": "高级"
        }
        return difficulty_map.get(self.difficulty, "未知")

    @computed_field
    @property
    def is_saved_name(self) -> str:
        saved_map = {0: "未保存", 1: "已保存"}
        return saved_map.get(self.is_saved, "未知")


# ------------------------------
# 8. 题目编辑请求模型
# ------------------------------
class QuestionUpdateRequest(BaseModel):
    question_content: Optional[str] = Field(None, alias="question")
    reference_answer: Optional[str] = None
    scoring_points: Optional[list] = None
    difficulty: Optional[str] = None
    question_type: Optional[str] = None

    class Config:
        populate_by_name = True


# ------------------------------
# 9. 保存到题库请求模型
# ------------------------------
class QuestionSaveToBankRequest(BaseModel):
    question_ids: List[int]
