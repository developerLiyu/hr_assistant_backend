from pydantic import BaseModel, computed_field
from typing import Optional
from datetime import datetime, date


# 上传录音响应
class RecordingUploadResponse(BaseModel):
    id: int
    file_name: str
    duration: Optional[int] = None
    transcript_status: int
    duration_text: Optional[str] = None

    class Config:
        from_attributes = True

    @computed_field
    @property
    def transcript_status_name(self) -> str:
        status_map = {0: "未转写", 1: "转写中", 2: "已完成", 3: "失败"}
        return status_map.get(self.transcript_status, "未知")


# 转写响应
class TranscribeResponse(BaseModel):
    id: int
    transcript_status: int
    estimated_time: Optional[str] = None

    class Config:
        from_attributes = True

    @computed_field
    @property
    def transcript_status_name(self) -> str:
        status_map = {0: "未转写", 1: "转写中", 2: "已完成", 3: "失败"}
        return status_map.get(self.transcript_status, "未知")


# 转写状态响应
class TranscriptStatusResponse(BaseModel):
    id: int
    transcript_status: int
    transcript_error: Optional[str] = None

    class Config:
        from_attributes = True

    @computed_field
    @property
    def transcript_status_name(self) -> str:
        status_map = {0: "未转写", 1: "转写中", 2: "已完成", 3: "失败"}
        return status_map.get(self.transcript_status, "未知")


# 文字稿响应
class TranscriptResponse(BaseModel):
    id: int
    transcript_status: int
    transcript: Optional[str] = None
    word_count: Optional[int] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 录音详情响应
class RecordingDetailResponse(BaseModel):
    id: int
    resume_id: int
    position_id: Optional[int] = None
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    duration: Optional[int] = None
    transcript: Optional[str] = None
    transcript_status: int
    transcript_error: Optional[str] = None
    interviewer: Optional[str] = None
    interview_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # 支持读取ORM对象的属性值
        # populate_by_name = True # 支持使用别名


    @computed_field
    @property
    def transcript_status_name(self) -> str:
        status_map = {0: "未转写", 1: "转写中", 2: "已完成", 3: "失败"}
        return status_map.get(self.transcript_status, "未知")


# 录音列表查询参数
class RecordingListQuery(BaseModel):
    resume_id: Optional[str] = None
    position_id: Optional[str] = None
    interviewer: Optional[str] = None
    transcript_status: Optional[str] = None
    interview_date_start: Optional[date] = None
    interview_date_end: Optional[date] = None
    page: int = 1
    page_size: int = 10


# 录音列表项响应
class RecordingItemResponse(BaseModel):
    id: int
    resume_id: int
    position_id: Optional[int] = None
    file_name: str
    file_type: str
    duration: Optional[int] = None
    transcript_status: int
    interviewer: Optional[str] = None
    interview_date: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @computed_field
    @property
    def transcript_status_name(self) -> str:
        status_map = {0: "未转写", 1: "转写中", 2: "已完成", 3: "失败"}
        return status_map.get(self.transcript_status, "未知")


# 录音列表响应
class RecordingListResponse(BaseModel):
    list: list[RecordingItemResponse]
    pagination: dict[str, int]
