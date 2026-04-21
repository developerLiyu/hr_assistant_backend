import os
import uuid
import math
import subprocess
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from starlette.responses import JSONResponse

from app.crud.recording import (
    async_create_recording_db,
    async_get_recording_by_id_db,
    async_update_recording_db,
    async_get_recording_list_db,
    async_delete_recording_db
)
from app.schemas.recording import (
    RecordingUploadResponse,
    TranscribeResponse,
    TranscriptStatusResponse,
    TranscriptResponse,
    RecordingDetailResponse,
    RecordingListQuery,
    RecordingListResponse,
    RecordingItemResponse
)
from app.utils import file_util, oss_util, path_tool
from app.utils.response import response
from app.utils.logger_handler import logger




def format_duration(seconds: int) -> str:
    """将秒数格式化为 MM:SS 格式"""
    if seconds is None:
        return None
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def calculate_estimated_time(file_size: int, file_type: str) -> str:
    """根据文件大小和类型估算转写时间"""
    # 简单估算：每10MB约1分钟
    size_mb = file_size / (1024 * 1024)
    estimated_minutes = max(1, math.ceil(size_mb / 10))
    if estimated_minutes < 60:
        return f"约{estimated_minutes}分钟"
    else:
        hours = estimated_minutes // 60
        minutes = estimated_minutes % 60
        if minutes > 0:
            return f"约{hours}小时{minutes}分钟"
        return f"约{hours}小时"


async def async_upload_recording_service(
        file: UploadFile,
        resume_id: int,
        position_id: Optional[int] = None,
        interview_date: Optional[str] = None,
        interviewer: Optional[str] = None,
        db: AsyncSession = None
) -> JSONResponse:
    """
    上传录音文件服务
    :param file: 音频文件
    :param resume_id: 关联简历ID
    :param position_id: 关联岗位ID
    :param interview_date: 面试日期
    :param interviewer: 面试官
    :param db: 数据库会话
    :return:
    """
    try:
        # 1. 校验文件
        content_bytes = await file.read()
        valid, msg = await file_util.async_validate_audio_file(file.filename, len(content_bytes))
        if not valid:
            return response(code=1002, message=msg)

        # 2. 保存文件
        rel_path, abs_path = await file_util.async_save_audio_file(file, content_bytes)

        # 3. 获取文件大小
        file_size = len(content_bytes)
        ext = file.filename.split(".")[-1].lower()

        # 4. 获取音频时长
        duration = await async_get_audio_duration(abs_path)

        # 5. 构建数据并保存到数据库
        data = {
            "resume_id": resume_id,
            "position_id": position_id,
            "file_name": file.filename,
            "file_path": rel_path,
            "file_type": ext,
            "file_size": file_size,
            "duration": duration,
            "transcript_status": 0,
            "interviewer": interviewer,
            "interview_date": interview_date
        }

        recording = await async_create_recording_db(db, data)

        # 6. 构建响应
        duration_text = format_duration(recording.duration) if recording.duration else None

        upload_result = RecordingUploadResponse(
            id=recording.id,
            file_name=recording.file_name,
            duration=recording.duration,
            duration_text=duration_text,
            transcript_status=recording.transcript_status
        )

        # 7. 自动启动转写任务（复用转写服务的完整逻辑）
        import asyncio
        await async_update_recording_db(db, recording.id, {
            "transcript_status": 1,
            "transcript_error": None
        })
        asyncio.create_task(async_process_transcription_task(recording.id, db))

        return response(code=0, message="success", data=upload_result)

    except Exception as e:
        logger.error(f"上传录音失败：{str(e)}", exc_info=True)
        return response(code=1002, message=f"上传失败：{str(e)}")


async def async_get_audio_duration(audio_path: str) -> Optional[int]:
    """
    获取音频文件时长（秒）
    :param audio_path: 音频文件路径
    :return: 时长（秒），失败返回None
    """
    try:
        # 使用 ffprobe 获取音频时长
        cmd = [
            'ffprobe',  # FFmpeg的媒体信息探测工具
            '-v', 'error',  # 只输出错误信息，保持输出干净
            '-show_entries', 'format=duration',  # 只显示格式层面的duration字段
            '-of', 'default=noprint_wrappers=1:nokey=1',  # 输出格式：无包装、无键名
            audio_path  # 音频文件路径
        ]
        # cmd: 要执行的命令列表
        # capture_output = True: 捕获标准输出和标准错误
        # text = True: 以文本模式返回输出（而非字节）
        # timeout = 10: 设置10秒超时，防止命令卡死
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
            duration_seconds = float(result.stdout.strip())
            return int(duration_seconds)
        else:
            logger.warning(f"获取音频时长失败：{audio_path}")
            return None
    except Exception as e:
        logger.error(f"获取音频时长异常：{str(e)}", exc_info=True)
        return None


async def async_get_recording_list_service(query: RecordingListQuery, db: AsyncSession) -> RecordingListResponse:
    """
    获取录音列表服务
    :param query:
    :param db:
    :return:
    """
    data_result = await async_get_recording_list_db(query, db)

    # 分页数据处理
    total = data_result["total"]
    total_pages = total // query.page_size + (1 if total % query.page_size > 0 else 0)
    pagination = {
        "page": query.page,
        "page_size": query.page_size,
        "total": total,
        "total_pages": total_pages
    }

    # 录音列表处理
    data = []
    if data_result["data"]:
        for item in data_result["data"]:
            recording = RecordingItemResponse.model_validate(item)
            data.append(recording)

    return RecordingListResponse(list=data, pagination=pagination)


async def async_get_recording_detail_service(recording_id: int, db: AsyncSession) -> JSONResponse:
    """
    获取录音详情服务
    :param recording_id: 录音ID
    :param db:
    :return:
    """
    recording = await async_get_recording_by_id_db(db, recording_id)
    if not recording:
        return response(code=1002, message="录音不存在")

    detail = RecordingDetailResponse.model_validate(recording)
    return response(code=0, message="success", data=detail)


async def async_delete_recording_service(recording_id: int, db: AsyncSession) -> JSONResponse:
    """
    删除录音服务
    :param recording_id: 录音ID
    :param db:
    :return:
    """
    recording = await async_get_recording_by_id_db(db, recording_id)
    if not recording:
        return response(code=1002, message="录音不存在")

    # 删除数据库记录
    success = await async_delete_recording_db(db, recording_id)
    if not success:
        return response(code=1002, message="删除失败")

    # 删除物理文件
    try:
        # 删除原始音频文件
        if os.path.exists(recording.file_path):
            os.remove(recording.file_path)

        # 删除转换的文件
        preprocess_file_path = recording.file_path.rsplit(".", 1)[0] + "_processed.wav"
        if os.path.exists(preprocess_file_path):
            os.remove(preprocess_file_path)

    except Exception as e:
        # 文件删除失败不影响数据库删除
        print(f"⚠️ 删除音频文件失败：{str(e)}")

    return response(code=0, message="删除成功")


async def async_start_transcribe_service(recording_id: int, db: AsyncSession) -> JSONResponse:
    """
    开始语音转文字服务
    :param recording_id: 录音ID
    :param db:
    :return:
    """
    recording = await async_get_recording_by_id_db(db, recording_id)
    if not recording:
        return response(code=1002, message="录音不存在")

    # 检查转写状态
    if recording.transcript_status == 1:
        return response(code=1002, message="正在转写中，请稍候")

    if recording.transcript_status == 2:
        return response(code=1002, message="已完成转写，无需重复转写")

    # 更新状态为转写中
    await async_update_recording_db(db, recording_id, {
        "transcript_status": 1,
        "transcript_error": None
    })

    # 估算时间
    estimated_time = calculate_estimated_time(recording.file_size, recording.file_type)

    transcribe_result = TranscribeResponse(
        id=recording.id,
        transcript_status=1,
        estimated_time=estimated_time
    )

    # 启动异步转写任务
    import asyncio
    asyncio.create_task(async_process_transcription_task(recording_id, db))

    return response(code=0, message="success", data=transcribe_result)



async def async_get_transcript_status_service(recording_id: int, db: AsyncSession) -> JSONResponse:
    """
    获取转写状态服务
    :param recording_id: 录音ID
    :param db:
    :return:
    """
    recording = await async_get_recording_by_id_db(db, recording_id)
    if not recording:
        return response(code=1002, message="录音不存在")

    status_result = TranscriptStatusResponse.model_validate(recording)
    return response(code=0, message="success", data=status_result)


async def async_get_transcript_service(recording_id: int, db: AsyncSession) -> JSONResponse:
    """
    获取文字稿服务
    :param recording_id: 录音ID
    :param db:
    :return:
    """
    recording = await async_get_recording_by_id_db(db, recording_id)
    if not recording:
        return response(code=1002, message="录音不存在")

    # 如果未转写完成，返回提示
    if recording.transcript_status != 2:
        status_map = {0: "未转写", 1: "转写中", 3: "转写失败"}
        return response(code=1002, message=f"文字稿尚未完成：{status_map.get(recording.transcript_status, '未知状态')}")

    # 计算字数
    word_count = len(recording.transcript) if recording.transcript else 0

    transcript_result = TranscriptResponse(
        id=recording.id,
        transcript_status=recording.transcript_status,
        transcript=recording.transcript,
        word_count=word_count,
        updated_at=recording.updated_at
    )

    return response(code=0, message="success", data=transcript_result)


async def async_update_transcript_service(recording_id: int, transcript: str, db: AsyncSession) -> JSONResponse:
    """
    更新文字稿服务
    :param recording_id: 录音ID
    :param transcript: 文字稿内容
    :param db:
    :return:
    """
    recording = await async_get_recording_by_id_db(db, recording_id)
    if not recording:
        return response(code=1002, message="录音不存在")

    # 更新文字稿
    await async_update_recording_db(db, recording_id, {
        "transcript": transcript,
        "transcript_status": 2
    })

    return response(code=0, message="更新成功")


# ==================== 异步转写核心处理 ====================

async def async_process_transcription_task(recording_id: int, db: AsyncSession):
    """
    后台异步处理转写任务
    :param recording_id: 录音ID
    :param db: 数据库会话
    """
    from app.utils.llm_util import async_qwen_asr_transcribe, async_qwen_polish_transcript
    from app.core.db_config import async_session

    # 创建新的数据库会话（避免原会话关闭导致的问题）
    async with async_session() as new_db:
        try:
            recording = await async_get_recording_by_id_db(new_db, recording_id)
            if not recording:
                logger.warning(f"⚠️ 录音不存在：ID={recording_id}")
                return

            # 1. 音频预处理（格式转换/降噪）
            abs_path = path_tool.get_abs_path(recording.file_path)
            processed_abs_path = await async_preprocess_audio(abs_path)

            # 2. 将音频文件上传到 OSS，获取公网 URL
            oss_url = oss_util.upload_audio_to_oss(processed_abs_path)

            # 3. 调用Qwen3-ASR-Flash-Filetrans进行语音识别（传入 OSS URL）
            transcript = await async_qwen_asr_transcribe(oss_url)

            if not transcript:
                await async_update_recording_db(new_db, recording_id, {
                    "transcript_status": 3,
                    "transcript_error": "语音识别返回空结果"
                })
                await new_db.commit()
                return

            # 4. 后处理（添加标点/分段）
            processed_transcript = await async_qwen_polish_transcript(transcript)

            # 5. 保存到数据库
            await async_update_recording_db(new_db, recording_id, {
                "transcript_status": 2,
                "transcript": processed_transcript,
                "transcript_error": None
            })
            await new_db.commit()

            logger.info(f"✅ 转写完成：录音ID={recording_id}")

        except Exception as e:
            await new_db.rollback()
            logger.error(f"❌ 转写失败：录音ID={recording_id}, 错误：{str(e)}", exc_info=True)
            try:
                await async_update_recording_db(new_db, recording_id, {
                    "transcript_status": 3,
                    "transcript_error": str(e)
                })
                await new_db.commit()
            except Exception as update_error:
                logger.error(f"❌ 更新失败状态异常：{str(update_error)}", exc_info=True)



async def async_preprocess_audio(audio_path: str) -> str:
    """
    音频预处理（格式转换/降噪）
    统一转换为：wav格式，16000Hz采样率，单声道，16bit位深
    :param audio_path: 原始音频路径
    :return: 处理后的音频路径
    """
    try:
        # 生成输出文件路径
        output_path = audio_path.rsplit('.', 1)[0] + '_processed.wav'

        # 如果已存在处理过的文件，直接返回
        if os.path.exists(output_path):
            logger.info(f"使用已处理的音频文件：{output_path}")
            return output_path

        # 使用 ffmpeg 进行音频转换
        # -ar 16000: 采样率16000Hz
        # -ac 1: 单声道
        # -sample_fmt s16: 16bit位深
        cmd = [
            'ffmpeg',
            '-i', audio_path,
            '-ar', '16000',
            '-ac', '1',
            '-sample_fmt', 's16',
            '-y',  # 覆盖输出文件
            output_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0 and os.path.exists(output_path):
            logger.info(f"音频预处理成功：{output_path}")
            return output_path
        else:
            logger.error(f"音频预处理失败：{result.stderr}")
            # 如果处理失败，返回原文件路径
            return audio_path

    except subprocess.TimeoutExpired:
        logger.error(f"音频预处理超时：{audio_path}")
        return audio_path
    except Exception as e:
        logger.error(f"音频预处理异常：{str(e)}", exc_info=True)
        return audio_path


async def async_post_process_transcript(transcript: str) -> str:
    """
    后处理文字稿（添加标点/分段）
    :param transcript: 原始识别文字
    :return: 处理后的文字稿
    """
    # TODO: 这里可以调用LLM进行文字润色，添加标点符号
    # 示例：使用qwen3.5-plus进行文字整理
    # from app.utils.llm_util import async_qwen_polish_transcript
    # processed = await async_qwen_polish_transcript(transcript)
    # return processed

    # 暂时直接返回
    return transcript
