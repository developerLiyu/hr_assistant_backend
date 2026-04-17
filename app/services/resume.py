import io
import os
import urllib.parse
import zipfile
from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from starlette.responses import JSONResponse, FileResponse, StreamingResponse

from app.crud.resume import (
    async_create_resume_db,
    async_get_resume_by_id_db,
    async_update_parse_db, async_update_milvus_id_db, async_get_resume_list_db, async_get_resume_detail_db,
    async_get_resume_by_ids_db
)
from app.utils.file_util import async_validate_file, async_save_and_extract_text, async_unzip_file
from app.utils.llm_util import async_qwen_parse
from app.schemas.resume import UploadResult, BatchUploadResponse, ParseResponse, ResumeListQuery, ResumeListResponse, \
    ResumeResponse, ResumeDetailResponse
from app.utils.milvus_util import async_generate_embedding, async_insert_embedding, async_upsert_embedding, \
    async_delete_embedding
from app.utils.response import response


# 内部处理单个文件（普通文件/ZIP内部文件）
async def _process_single_file(file: UploadFile, position_id: int, db: AsyncSession):
    try:
        content_bytes = await file.read()
        valid, msg = await async_validate_file(file.filename, len(content_bytes))
        # 将指针重置到文件开头。保证后面可以去读完整文件
        await file.seek(0)
        if not valid:
            return UploadResult(file_name=file.filename, success=False, message=msg)

        rel_path, original_content = await async_save_and_extract_text(file)

        # 解析文本内容，用于后面存储
        parse_data = await async_qwen_parse(original_content)
        if not parse_data or not parse_data.get("candidate_name"):
            return UploadResult(file_name=file.filename, success=False, message="文本内容无效")

        data = {
            "candidate_name": parse_data.get("candidate_name"),
            "file_path": rel_path,
            "file_name": file.filename,
            "file_type": file.filename.split(".")[-1].lower(),
            "file_size": len(content_bytes),
            "position_id": position_id,
            "status": 1, # 状态：1-待筛选 2-初筛通过 3-面试中 4-已录用 5-已淘汰
            "parse_status": 0, # 解析状态：0-未解析 1-解析中 2-解析成功 3-解析失败
            "original_content": original_content
        }
        resume = await async_create_resume_db(db, data)

        # 【核心】上传后自动触发解析
        await async_parse_service(resume.id, db, parse_data)

        return UploadResult(
            file_name=file.filename, success=True,
            message="上传成功", resume_id=resume.id
        )

    except Exception as e:
        return UploadResult(file_name=file.filename, success=False, message=str(e))


# 主上传服务（支持 普通文件 + ZIP）
async def async_upload_service(
        files: List[UploadFile],
        position_id: Optional[int],
        db: AsyncSession
) -> BatchUploadResponse:
    results = []
    success = 0
    fail = 0

    for file in files:
        ext = file.filename.split(".")[-1].lower()

        # ==============================================
        # 【核心】如果是ZIP，解压后批量处理
        # ==============================================
        if ext == "zip":
            inner_files = await async_unzip_file(file)
            if not inner_files:
                results.append(UploadResult(file_name=file.filename, success=False, message="ZIP内无合法简历"))
                fail += 1
                continue
            # 遍历解压后的文件
            for f, fname in inner_files:
                res = await _process_single_file(f, position_id, db)
                results.append(res)
                if res.success:
                    success += 1
                else:
                    fail += 1
            continue

        # 普通文件直接处理
        res = await _process_single_file(file, position_id, db)
        results.append(res)
        if res.success:
            success += 1
        else:
            fail += 1

    return BatchUploadResponse(
        total=len(results),
        success_count=success,
        fail_count=fail,
        results=results
    )


# 解析服务（集成向量化+Milvus存储）
async def async_parse_service(resume_id: int, db: AsyncSession, parse_data: dict[str, Any] = None, reparse_flag: bool = False) -> ParseResponse:
    """
    解析服务（集成向量化+Milvus存储）
    :param resume_id: 简历id
    :param db:
    :param parse_data: 解析数据
    :param reparse_flag: 是否重新解析接口标志  True：是  False：不是（默认）
    :return:
    """

    resume = await async_get_resume_by_id_db(db, resume_id)
    if not resume:
        return ParseResponse(resume_id=resume_id, status=3, message="简历不存在")

    if not reparse_flag:
        # 不是重新解析，则判断是否已经解析
        if resume.parse_status == 2:
            return ParseResponse(resume_id=resume_id, status=2, message="已解析")

    # 标记为解析中
    await async_update_parse_db(db, resume_id, {"parse_status": 1})

    try:
        original_content = resume.original_content
        if not original_content:
            await async_update_parse_db(db, resume_id, {"parse_status": 3})
            return ParseResponse(resume_id=resume_id, status=3, message="原始文本为空")

        # 1. LLM解析简历（在之前已经执行了解析）
        if parse_data:
            parse_data = parse_data
        else:
            parse_data = await async_qwen_parse(original_content)

        if not parse_data:
            await async_update_parse_db(db, resume_id, {"parse_status": 3})
            return ParseResponse(resume_id=resume_id, status=3, message="LLM解析返回空")

        # 2. 拼接向量化文本（原始文本+技能+工作经历+项目经验）
        skills = parse_data.get("skills", [])
        work_exp = parse_data.get("work_experience", [])
        project_exp = parse_data.get("project_experience", [])

        # 拼接工作经历文本
        work_exp_text = "\n".join([
            f"{exp.get('company', '')} {exp.get('position', '')}: {exp.get('description', '')}"
            for exp in work_exp
        ])
        # 拼接项目经验文本
        project_exp_text = "\n".join([
            f"{proj.get('project_name', '')} {proj.get('role', '')}: {proj.get('description', '')}"
            for proj in project_exp
        ])
        # 最终拼接文本
        vector_text = f"""
            {original_content}
            技能标签：{" ".join(skills)}
            工作经历：{work_exp_text}
            项目经验：{project_exp_text}
        """.strip()

        # 3. 生成1536维向量
        embedding = await async_generate_embedding(vector_text)

        if len(embedding) != 1536:
            await async_update_parse_db(db, resume_id, {"parse_status": 3})
            return ParseResponse(resume_id=resume_id, status=3, message="向量维度异常")

        # 判断embedding结果是否都为0
        if all(v == 0 for v in embedding):
            await async_update_parse_db(db, resume_id, {"parse_status": 3})
            return ParseResponse(resume_id=resume_id, status=3, message="向量生成异常")

        milvus_id = None
        if reparse_flag:
            # 重新解析，则更新向量
            milvus_id = await async_upsert_embedding(int(resume.milvus_id), resume_id, embedding)
            print(f"Milvus更新成功：{milvus_id}")
        else:
            # 首次解析，则插入向量
            milvus_id = await async_insert_embedding(resume_id, embedding)
            print(f"Milvus插入成功：{milvus_id}")

        if not milvus_id:
            await async_update_parse_db(db, resume_id, {"parse_status": 3})
            return ParseResponse(resume_id=resume_id, status=3, message="Milvus更新失败")

        # 5. 更新简历解析数据和Milvus ID
        update_data = {**parse_data, "parse_status": 2}
        await async_update_parse_db(db, resume_id, update_data)
        await async_update_milvus_id_db(db, resume_id, str(milvus_id))

        return ParseResponse(resume_id=resume_id, status=2, message="解析+向量化完成")

    except Exception as e:
        await async_update_parse_db(db, resume_id, {"parse_status": 3})
        return ParseResponse(resume_id=resume_id, status=3, message=f"解析异常：{str(e)}")







async def get_list_service(query: ResumeListQuery, db: AsyncSession) -> ResumeListResponse:
    """
    查询简历列表
    :param query:
    :param db:
    :return:
    """
    # 根据条件获取简历列表和总数
    data_result = await async_get_resume_list_db(query, db)

    # 对查询结果进行处理
    # 分页数据处理
    total = data_result["total"]
    total_pages = total // query.page_size + (1 if total % query.page_size > 0 else 0)
    pagination = {
        "page": query.page,
        "page_size": query.page_size,
        "total": total,
        "total_pages": total_pages
    }

    # 简历列表处理
    data = []
    if data_result["data"]:
        for item, position_name in data_result["data"]:
            resume = ResumeResponse.model_validate(item)
            # 添加岗位名称
            resume.position_name = position_name
            # 手机号脱密
            resume.phone = f"{resume.phone[:3]}****{resume.phone[-4:]}"
            data.append(resume)

    # 返回处理后的结果
    return ResumeListResponse(list=data, pagination=pagination)


async def get_detail_service(resume_id: int, db: AsyncSession) -> JSONResponse:
    """
    查询简历详情
    :param id:简历id
    :param db:
    :return:
    """
    data_result = await async_get_resume_detail_db(resume_id, db)
    if not data_result:
        return response(code=1002, message="数据不存在")

    # 处理简历详情数据
    resume = ResumeDetailResponse.model_validate(data_result)
    resume.phone = f"{resume.phone[:3]}****{resume.phone[-4:]}"
    resume.position = {
        "id": resume.position_id,
        "name": resume.position_name
    }

    # 返回处理后的结果
    return response(code=0, message="success", data=resume)


async def delete_service(resume_id: int, db: AsyncSession) -> JSONResponse:
    """
    删除简历
    操作：软删除简历 + 删除向量库中对应的记录
    :param id:简历id
    :param db:
    :return:
    """
    resume = await async_get_resume_by_id_db(db, resume_id)
    if not resume:
        return response(code=1002, message="简历不存在")

    # 软删除简历
    await async_update_parse_db(db, resume_id, {"is_deleted": 1})

    # 如果存在Milvus向量ID，则删除向量库中的记录
    if resume.milvus_id:
        try:
            await async_delete_embedding(int(resume.milvus_id))
        except Exception as e:
            print(f"⚠️ 删除Milvus向量失败（不影响软删除）：{str(e)}")

    # 返回处理后的结果
    return response(code=0, message="删除成功")


# ... existing code ...


async def bind_position_service(resume_id: int, position_id: int, db: AsyncSession) -> JSONResponse:
    """
    关联岗位
    :param id:简历id
    :param db:
    :return:
    """
    await async_update_parse_db(db, resume_id, {"position_id": position_id})

    # 返回处理后的结果
    return response(code=0, message="关联岗位成功")

async def update_status_service(resume_id: int, status: int, db: AsyncSession) -> JSONResponse:
    """
    更新简历状态
    :param id:简历id
    :param db:
    :return:
    """
    await async_update_parse_db(db, resume_id, {"status": status})

    # 返回处理后的结果
    return response(code=0, message="更新简历状态成功")

async def download_resume_service(resume_id: int, db: AsyncSession) -> FileResponse:
    """
    单个简历下载
    :param id:简历id
    :param db:
    :return:
    """
    resume = await async_get_resume_by_id_db(db, resume_id)
    if not resume:
        return response(code=1002, message="简历不存在")

    # 获取简历绝对路径
    abs_path = os.path.join(os.getenv("UPLOAD_DIR"), resume.file_path)

    # 校验文件是否存在
    if not os.path.exists(abs_path):
        return response(code=1002, message="简历不存在")

    # 返回文件下载响应（自动处理文件名、MIME类型）
    return FileResponse(
        path=abs_path,
        filename=resume.file_name, # 前端下载显示的原始文件名
        media_type="application/octet-stream"
    )


async def batch_download_resume_service(resume_ids: list[int], db: AsyncSession) -> StreamingResponse:
    """
    简历批量下载
    :param resume_ids:简历ID集合 [1,2,3,4]
    :param db:
    :return: ZIP压缩包流（浏览器自动下载）
    """
    resumes = await async_get_resume_by_ids_db(db, resume_ids)
    if not resumes:
        return response(code=1002, message="未找到有效简历")
    try:
        # 2. 内存流式生成ZIP（不写磁盘，高性能）
        zip_io = io.BytesIO()
        # 参数说明：
        # zip_io：内存流对象（在内存执行写入操作）  ZIP_DEFLATED：压缩算法
        with zipfile.ZipFile(zip_io, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for resume in resumes:
                # 获取绝对路径
                file_path = os.path.join(os.getenv("UPLOAD_DIR"), resume.file_path)
                # 跳过不存在的文件
                if not os.path.exists(file_path):
                    continue
                # 把文件写入ZIP（用原始文件名）
                zip_file.write(file_path, arcname=resume.file_name)

        # 3. 重置流指针
        zip_io.seek(0)

        # 4. 生成ZIP文件名
        zip_name = f"简历批量下载_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"

        # 对文件名进行URL编码，避免中文编码问题
        encoded_zip_name = urllib.parse.quote(zip_name)

        # 生成ASCII备用文件名（用于不支持UTF-8的客户端）
        ascii_zip_name = f"resume_batch_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"

        # 5. 返回ZIP流式响应
        return StreamingResponse(
            iter([zip_io.getvalue()]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=\"{ascii_zip_name}\" ;filename*=UTF-8''{encoded_zip_name}"
            }
        )

    except Exception as e:
        return response(code=1002, message=f"批量下载异常：{str(e)}")


