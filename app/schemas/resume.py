from pydantic import BaseModel, computed_field
from typing import Optional, List, Any
from datetime import datetime

# 子模型：工作经历
class WorkExperience(BaseModel):
    company: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None

# 子模型：项目经验
class ProjectExperience(BaseModel):
    project_name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None

# 子模型：教育经历
class EducationExperience(BaseModel):
    school: Optional[str] = None
    major: Optional[str] = None
    degree: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class UploadResult(BaseModel):
    file_name: str
    success: bool
    message: str
    resume_id: Optional[int] = None

class BatchUploadResponse(BaseModel):
    total: int
    success_count: int
    fail_count: int
    results: List[UploadResult]

class ParseResponse(BaseModel):
    resume_id: int
    status: int
    message: str

    @computed_field
    @property
    def status_name(self) -> str:
        status_map = {0: "未解析", 1: "解析中", 2: "解析成功", 3: "解析失败"}
        return status_map.get(self.status, "未知")

# 完整解析结果模型
class ResumeParseResult(BaseModel):
    candidate_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    education: Optional[str] = None
    school: Optional[str] = None
    major: Optional[str] = None
    work_years: Optional[float] = None
    current_company: Optional[str] = None
    current_position: Optional[str] = None
    skills: List[str] = []
    work_experience: List[WorkExperience] = []
    project_experience: List[ProjectExperience] = []
    education_experience: List[EducationExperience] = []
    resume_summary: Optional[str] = None



# ------------------------------
# 1. 列表查询参数
# ------------------------------
class ResumeListQuery(BaseModel):
    keyword: Optional[str] = None
    position_id: Optional[int] = None
    education: Optional[str] = None
    work_years_min: Optional[int] = None
    work_years_max: Optional[int] = None
    status: Optional[int] = None
    page: int = 1
    page_size: int = 10

# ------------------------------
# 2. 简历响应模型（对齐你的PositionResponse）
# ------------------------------
class ResumeResponse(BaseModel):
    id: int
    candidate_name: str
    phone: Optional[str] # 手机号，脱敏处理
    education: Optional[str]
    work_years: Optional[int]
    current_company: Optional[str]
    position_id: Optional[int]
    status: int
    created_at: datetime
    # 联表字段
    position_name: Optional[str] = None # 关联岗位名称

    class Config:
        from_attributes = True

    @computed_field
    @property
    def status_name(self) -> str:
        status_map = {1: "待筛选",2: "初筛通过",3: "面试中",4: "已录用",5: "已淘汰"}
        return status_map.get(self.status, "未知")

# ------------------------------
# 3. 分页响应模型（对齐你的PositionListResponse）
# ------------------------------
class ResumeListResponse(BaseModel):
    list: list[ResumeResponse]
    pagination: dict[str, int]



# ------------------------------
# 【新增】简历详情响应模型（全字段 + 计算属性）
# ------------------------------
class ResumeDetailResponse(BaseModel):
    # 全量字段（和ORM完全一致）
    id: int
    candidate_name: str
    phone: Optional[str]
    email: Optional[str]
    education: Optional[str]
    school: Optional[str]
    major: Optional[str]
    work_years: Optional[int]
    current_company: Optional[str]
    current_position: Optional[str]
    skills: Optional[list]
    work_experience: Optional[list]
    project_experience: Optional[list]
    education_experience: Optional[list]
    resume_summary: Optional[str]
    original_content: Optional[str]
    file_path: str
    file_name: str
    file_type: str
    file_size: Optional[int]
    milvus_id: Optional[str]
    position_id: Optional[int]
    status: int
    parse_status: int
    is_deleted: int
    created_at: datetime
    updated_at: datetime
    # 联表岗位名称
    position_name: Optional[str] = None
    # 岗位信息（id，名称）
    position: Optional[dict[str, Any]] = None

    # 严格对齐你的格式
    class Config:
        from_attributes = True

    # 计算属性（和岗位模型写法一致）
    @computed_field
    @property
    def status_name(self) -> str:
        status_map = {1: "待筛选", 2: "初筛通过", 3: "面试中", 4: "已录用", 5: "已淘汰"}
        return status_map.get(self.status, "未知")

    @computed_field
    @property
    def parse_status_name(self) -> str:
        parse_map = {0: "未解析", 1: "解析中", 2: "解析成功", 3: "解析失败"}
        return parse_map.get(self.parse_status, "未知")

    @computed_field
    @property
    def is_deleted_name(self) -> str:
        delete_map = {0: "未删除", 1: "已删除"}
        return delete_map.get(self.is_deleted, "未知")


