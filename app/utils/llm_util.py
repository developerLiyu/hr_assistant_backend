import os
from functools import lru_cache
from typing import Any, Coroutine

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
# ✅ 修复：正确导入最新版 LangChain 模块
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
import dashscope

from app.models.position import JobPosition
from app.models.resume import Resume
from app.schemas.interview_question import LLMQuestionItem
from app.schemas.interview_summary import InterviewSummaryResponse
from app.schemas.resume import ResumeParseResult
from app.schemas.screening import MatchedResume, MatchAnalysis
from app.utils.logger_handler import logger

# 通义千问配置
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.5-plus")
BASE_URL = os.getenv("BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.1))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 4096))


# 打印提示词内容
def print_prompt(prompt: PromptTemplate):
    print("=" * 22 + " Prompt " + "=" * 22)
    # 获取提示词内容
    print(f"Prompt: {prompt.to_string()}")
    print("=" * 22 + " Prompt " + "=" * 22)
    return prompt


# 打印模型解析结果
def print_llm_response(response: AIMessage):
    print("=" * 22 + " LLM Response " + "=" * 22)
    print(f"LLM Response: {response.content}")
    print("=" * 22 + " LLM Response " + "=" * 22)
    return response


@lru_cache(maxsize=1)
def get_llm_instance():
    """
    获取LLM实例（单例模式）
    使用lru_cache确保只创建一个实例，避免重复初始化开销
    """
    return ChatOpenAI(
        model=MODEL_NAME,
        api_key=DASHSCOPE_API_KEY,
        base_url=BASE_URL,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
    )


def create_parse_chain(parser: PydanticOutputParser) -> any:
    """
    创建通用的LLM解析链
    :param parser: Pydantic输出解析器
    :return: LangChain Runnable链
    """
    llm = get_llm_instance()

    chain = (
            RunnableLambda(print_prompt)
            | llm
            | RunnableLambda(print_llm_response)
            | parser
    )

    return chain


async def async_qwen_parse(content: str) -> dict:
    """异步调用qwen3.5-plus解析简历，返回结构化数据"""
    if not content.strip():
        return {}

    # 定义Prompt模板（严格匹配要求）
    prompt_template = """
        请从以下简历文本中提取结构化信息，以JSON格式返回：

        简历内容：
        {content}

        请严格按以下JSON格式返回，如果某字段无法提取则填None：
        {{
            "candidate_name": "姓名",
            "phone": "手机号",
            "email": "邮箱",
            "education": "最高学历(博士/硕士/本科/大专)",
            "school": "毕业院校",
            "major": "专业",
            "work_years": 工作年限数字,
            "current_company": "当前公司",
            "current_position": "当前职位",
            "skills": ["技能1", "技能2"],
            "work_experience": [
                {{
                    "company": "公司名",
                    "position": "职位",
                    "start_date": "开始时间",
                    "end_date": "结束时间",
                    "description": "工作描述"
                }}
            ],
            "project_experience": [
                {{
                    "project_name": "项目名称",
                    "role": "担任角色",
                    "description": "项目描述"
                }}
            ],
            "education_experience": [
                {{
                    "school": "学校",
                    "major": "专业",
                    "degree": "学历",
                    "start_date": "开始时间",
                    "end_date": "结束时间"
                }}
            ],
            "resume_summary": "用50字概括该候选人的核心优势"
        }}
    """

    # 初始化解析器和Prompt
    parser = PydanticOutputParser(pydantic_object=ResumeParseResult)
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["content"],
    )

    try:
        # 创建解析链并执行
        chain = prompt | create_parse_chain(parser)
        result = await chain.ainvoke({"content": content})
        return result.model_dump(exclude_none=True)
    except Exception as e:
        logger.error(f"LLM解析失败: {str(e)}", exc_info=True)
        return {}


async def async_qwen_get_match_analysis(matched_resume: MatchedResume, position_obj: JobPosition) -> MatchAnalysis | None:
    """
    异步调用qwen3.5-plus分析候选人与目标岗位的匹配程度，返回结构化数据
    :param matched_resume: 简历信息
    :param position_obj: 岗位信息
    :return: MatchAnalysis对象
    """

    # 定义Prompt模板
    prompt_template = """
        请分析以下候选人与目标岗位的匹配程度：

        【目标岗位】
        岗位名称：{position_name}
        岗位职责：{job_description}
        任职要求：{requirements}

        【候选人信息】
        姓名：{candidate_name}
        学历：{education} - {school}
        工作年限：{work_years}年
        当前职位：{current_position} @ {current_company}
        技能：{skills}
        简历摘要：{resume_summary}

        请按以下JSON格式返回分析结果（确保所有字段都存在）：
        {{
            "match_advantages": ["优势1", "优势2", "优势3"],
            "match_weaknesses": ["短板1", "短板2"],
            "overall_comment": "综合评语（100字以内）",
            "interview_suggestions": ["建议考察方向1", "建议考察方向2"]
        }}

        严格遵循以下格式规范：
        {format_instructions}
    """

    # 初始化解析器和Prompt
    parser = PydanticOutputParser(pydantic_object=MatchAnalysis)
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=[
            "position_name", "job_description", "requirements",
            "candidate_name", "education", "school", "work_years",
            "current_position", "current_company", "skills", "resume_summary"
        ],
        # 静态预置返回的结构化数据
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    try:
        # 创建解析链并执行
        chain = prompt | create_parse_chain(parser)
        result = await chain.ainvoke({
            "position_name": position_obj.position_name,
            "job_description": position_obj.job_description,
            "requirements": position_obj.requirements,
            "candidate_name": matched_resume.candidate_name,
            "education": matched_resume.education,
            "school": matched_resume.school if hasattr(matched_resume, 'school') else "",
            "work_years": matched_resume.work_years,
            "current_position": matched_resume.current_position,
            "current_company": matched_resume.current_company if hasattr(matched_resume, 'current_company') else "",
            "skills": ", ".join(matched_resume.skills) if matched_resume.skills else "",
            "resume_summary": matched_resume.resume_summary if hasattr(matched_resume, 'resume_summary') else ""
        })
        return result
    except Exception as e:
        logger.error(f"LLM匹配分析失败: {str(e)}", exc_info=True)
        return None


async def async_qwen_get_match_analysis_use_custom(matched_resume: MatchedResume, yaoqiu_message: str) -> MatchAnalysis | None:
    """
    异步调用qwen3.5-plus分析候选人与自定义要求的匹配程度，返回结构化数据
    :param matched_resume: 简历信息
    :param yaoqiu_message: 自定义要求信息
    :return: MatchAnalysis对象
    """

    # 定义Prompt模板
    prompt_template = """
        请分析以下候选人与要求信息的匹配程度：

        【要求信息】
        要求信息：{yaoqiu_message}

        【候选人信息】
        姓名：{candidate_name}
        学历：{education} - {school}
        工作年限：{work_years}年
        当前职位：{current_position} @ {current_company}
        技能：{skills}
        简历摘要：{resume_summary}

        请按以下格式返回分析结果：
        {format_instructions}
    """

    # 初始化解析器和Prompt
    parser = PydanticOutputParser(pydantic_object=MatchAnalysis)
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=[
            "yaoqiu_message",
            "candidate_name", "education", "school", "work_years",
            "current_position", "current_company", "skills", "resume_summary"
        ],
        # 静态预置返回的结构化数据
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    try:
        # 创建解析链并执行
        chain = prompt | create_parse_chain(parser)
        result = await chain.ainvoke({
            "yaoqiu_message": yaoqiu_message,
            "candidate_name": matched_resume.candidate_name,
            "education": matched_resume.education,
            "school": matched_resume.school if hasattr(matched_resume, 'school') else "",
            "work_years": matched_resume.work_years,
            "current_position": matched_resume.current_position,
            "current_company": matched_resume.current_company if hasattr(matched_resume, 'current_company') else "",
            "skills": ", ".join(matched_resume.skills) if matched_resume.skills else "",
            "resume_summary": matched_resume.resume_summary if hasattr(matched_resume, 'resume_summary') else ""
        })
        return result
    except Exception as e:
        logger.error(f"LLM匹配分析失败: {str(e)}", exc_info=True)
        return None


# ... existing code ...

from app.models.position import JobPosition
from app.schemas.interview_question import LLMQuestionResponse
from app.schemas.resume import ResumeParseResult
from app.schemas.screening import MatchedResume, MatchAnalysis
from app.utils.logger_handler import logger




async def async_create_questions_by_position(position_obj: JobPosition, question_types: list[str], difficulty: str,
                                             count: int, with_answer: bool):
    """
    基于岗位信息生成面试题目

    :param position_obj: 岗位对象
    :param question_types: 题目类型列表（英文：technical/behavioral/situational/open）
    :param difficulty: 难度等级（英文：junior/middle/senior）
    :param count: 生成题目数量
    :param with_answer: 是否生成参考答案
    :return: LLMQuestionResponse 对象或 None
    """
    # 类型映射：英文 -> 中文（用于Prompt展示）
    type_name_map = {
        "technical": "技术类",
        "behavioral": "行为类",
        "situational": "情景类",
        "open": "开放类"
    }

    # 难度映射：英文 -> 中文（用于Prompt展示）
    difficulty_name_map = {
        "junior": "初级",
        "middle": "中级",
        "senior": "高级"
    }

    # 转换为中文用于Prompt
    question_types_cn = [type_name_map.get(t, t) for t in question_types]
    difficulty_cn = difficulty_name_map.get(difficulty, difficulty)

    # 定义Prompt模板
    prompt_template = """
        你是一位资深的技术面试官，请根据以下信息生成面试题目。
        
        【目标岗位】
        岗位名称：{position_name}
        岗位职责：
        {job_description}
        
        任职要求：
        {requirements}
        
        【生成要求】
        - 题目类型：{question_types}（可多选：技术类/行为类/情景类/开放类）
        - 难度等级：{difficulty}（初级/中级/高级）
        - 题目数量：{count}题
        - 是否生成参考答案：{with_answer}
        
        请按以下JSON格式返回：
        {{
            "questions": [
                {{
                    "type": "技术类",
                    "difficulty": "中级",
                    "question": "题目内容",
                    "reference_answer": "参考答案（如需要）",
                    "scoring_points": ["评分要点1", "评分要点2"],
                    "source": "基于岗位要求"
                }}
            ]
        }}
        
        严格遵循以下格式规范：
        {format_instructions}
        
        要求：
        1. 技术类题目要结合岗位技术栈和任职要求
        2. 行为类题目要考察候选人的软技能和工作经验
        3. 题目要有区分度，能考察真实能力
        4. 参考答案要给出关键点，不要过于冗长
        5. source字段统一填写为"基于岗位要求"
    """

    # 初始化解析器和Prompt（使用LLMQuestionResponse解析整个列表）
    parser = PydanticOutputParser(pydantic_object=LLMQuestionResponse)
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=[
            "position_name", "job_description", "requirements",
            "question_types", "difficulty", "count", "with_answer"
        ],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    try:
        # 创建解析链并执行
        chain = prompt | create_parse_chain(parser)
        result = await chain.ainvoke({
            "position_name": position_obj.position_name,
            "job_description": position_obj.job_description or "",
            "requirements": position_obj.requirements or "",
            "question_types": "、".join(question_types_cn),
            "difficulty": difficulty_cn,
            "count": count,
            "with_answer": "是" if with_answer else "否"
        })
        return result
    except Exception as e:
        logger.error(f"LLM生成题目失败: {str(e)}", exc_info=True)
        return None


async def async_create_questions_by_resume(resume_obj: Resume, question_types: list[str], difficulty: str,
                                             count: int, with_answer: bool):
    """
    基于基于候选人经历生成面试题目

    :param resume_obj: 简历对象
    :param question_types: 题目类型列表（英文：technical/behavioral/situational/open）
    :param difficulty: 难度等级（英文：junior/middle/senior）
    :param count: 生成题目数量
    :param with_answer: 是否生成参考答案
    :return: LLMQuestionResponse 对象或 None
    """
    # 类型映射：英文 -> 中文（用于Prompt展示）
    type_name_map = {
        "technical": "技术类",
        "behavioral": "行为类",
        "situational": "情景类",
        "open": "开放类"
    }

    # 难度映射：英文 -> 中文（用于Prompt展示）
    difficulty_name_map = {
        "junior": "初级",
        "middle": "中级",
        "senior": "高级"
    }

    # 转换为中文用于Prompt
    question_types_cn = [type_name_map.get(t, t) for t in question_types]
    difficulty_cn = difficulty_name_map.get(difficulty, difficulty)

    # 定义Prompt模板
    prompt_template = """
        你是一位资深的技术面试官，请根据以下信息生成面试题目。

        【候选人信息】
        姓名：{candidate_name}
        学历：{education} - {school} - {major}
        工作年限：{work_years}年
        当前职位：{current_position} @ {current_company}
        技能标签：{skills}
        工作经历摘要：{work_experience_summary}
        项目经验摘要：{project_experience_summary}

        【生成要求】
        - 题目类型：{question_types}（可多选：技术类/行为类/情景类/开放类）
        - 难度等级：{difficulty}（初级/中级/高级）
        - 题目数量：{count}题
        - 是否生成参考答案：{with_answer}

        请按以下JSON格式返回：
        {{
            "questions": [
                {{
                    "type": "技术类",
                    "difficulty": "中级",
                    "question": "题目内容",
                    "reference_answer": "参考答案（如需要）",
                    "scoring_points": ["评分要点1", "评分要点2"],
                    "source": "基于候选人经历"
                }}
            ]
        }}

        严格遵循以下格式规范：
        {format_instructions}

        要求：
        1. 技术类题目要结合岗位技术栈和任职要求
        2. 行为类题目要考察候选人的软技能和工作经验
        3. 题目要有区分度，能考察真实能力
        4. 参考答案要给出关键点，不要过于冗长
        5. source字段统一填写为"基于候选人经历"
    """

    # 初始化解析器和Prompt（使用LLMQuestionResponse解析整个列表）
    parser = PydanticOutputParser(pydantic_object=LLMQuestionResponse)
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=[
            "candidate_name", "education", "school", "major",
            "work_years", "current_position", "current_company",
            "skills", "work_experience_summary", "project_experience_summary",
            "question_types", "difficulty", "count", "with_answer"
        ],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    try:
        # 创建解析链并执行
        chain = prompt | create_parse_chain(parser)
        result = await chain.ainvoke({
            "candidate_name": resume_obj.candidate_name or "",
            "education": resume_obj.education or "",
            "school": resume_obj.school or "",
            "major": resume_obj.major or "",
            "work_years": resume_obj.work_years or 0,
            "current_position": resume_obj.current_position or "",
            "current_company": resume_obj.current_company or "",
            "skills": "、".join(resume_obj.skills) if resume_obj.skills else "",
            "work_experience_summary": resume_obj.work_experience or "",
            "project_experience_summary": resume_obj.project_experience or "",
            "question_types": "、".join(question_types_cn),
            "difficulty": difficulty_cn,
            "count": count,
            "with_answer": "是" if with_answer else "否"
        })
        return result
    except Exception as e:
        logger.error(f"LLM生成题目失败: {str(e)}", exc_info=True)
        return None


# ==================== 语音转写相关功能 ====================
async def async_qwen_asr_transcribe(audio_oss_url: str) -> str:
    """
    异步调用 Qwen3-ASR-Flash-Filetrans 进行语音转文字
    使用 DashScope 异步调用方式，支持最长12小时录音
    :param audio_oss_url: 音频文件的 OSS 公网 URL（必须公网可访问）
    :return: 转写后的文字
    """
    try:
        import json
        import os
        import sys
        from http import HTTPStatus

        import dashscope
        from dashscope.audio.qwen_asr import QwenTranscription
        from dashscope.api_entities.dashscope_response import TranscriptionResponse
        import json
        from urllib import request

        # # 配置 DashScope API Key
        # dashscope.api_key = DASHSCOPE_API_KEY

        logger.info(f"开始 ASR 转写，音频 URL: {audio_oss_url}")

        # # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
        # # 若没有配置环境变量，请用百炼API Key将下行替换为：dashscope.api_key = "sk-xxx"
        # dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

        # # 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1
        # dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
        task_response = QwenTranscription.async_call(
            model='qwen3-asr-flash-filetrans',
            file_url=audio_oss_url,
            # language="",
            enable_itn=True, # 是否启用智能数字转换  例：二十五岁 -》 25岁
            enable_words=False # 是否返回每个单词的识别结果
            # 例：
            # {
            #     "text": "你好世界",
            #     "words": [
            #       {"word": "你", "start_time": 0.1, "end_time": 0.2},
            #       {"word": "好", "start_time": 0.2, "end_time": 0.3},
            #       {"word": "世", "start_time": 0.4, "end_time": 0.5},
            #       {"word": "界", "start_time": 0.5, "end_time": 0.6}
            #     ]
            #   }
        )

        logger.info(f'task_response: {task_response}')

        # 检查任务提交是否成功
        if task_response.status_code != HTTPStatus.OK:
            logger.error(f"ASR任务提交失败: {task_response.message}")
            return ""

        # 获取任务ID
        task_id = task_response.output.task_id
        logger.info(f"ASR任务提交成功，task_id: {task_id}")

        # task_id = task_response.output.task_id

        # query_response = QwenTranscription.fetch(task=task_response.output.task_id)
        # logger.info(f'query_response: {query_response}')


        transcription_response = QwenTranscription.wait(task=task_id)
        logger.info(f"任务执行完成，transcription_response={transcription_response}")



        if transcription_response.output.task_status != "SUCCEEDED":
            logger.error(f"ASR任务执行失败: {transcription_response.output.message}")
            return ""

        # 获取文本链接
        transcription_url = transcription_response.output.result["transcription_url"]
        logger.info(f"文本链接: {transcription_url}")

        # 请求url得到文本内容
        response_data = request.urlopen(transcription_url).read().decode('utf-8')
        json_data = json.loads(response_data)
        logger.info(f"转写结果：{json_data}")

        # 解析文本内容
        transcript_parts = []
        if json_data["transcripts"]:
            for transcript in json_data["transcripts"]:
                transcript_parts.append(transcript["text"])

        # 合并所有文本
        full_transcript = "".join(transcript_parts)
        logger.info(f"ASR转写成功，文本长度: {len(full_transcript)}")

        return full_transcript

    except Exception as e:
        logger.error(f"ASR转写异常: {str(e)}", exc_info=True)
        return ""



async def async_qwen_polish_transcript(transcript: str) -> str:
    """
    使用LLM对转写文字稿进行后处理（添加标点/分段/润色）
    :param transcript: 原始识别文字
    :return: 处理后的文字稿
    """
    if not transcript.strip():
        return transcript

    prompt_template = """
        请对以下语音识别的文字稿进行整理和润色：

        【要求】
        1. 添加合适的标点符号
        2. 合理分段，保持语义连贯
        3. 修正明显的识别错误
        4. 保持原文意思不变，不要添加或删除内容
        5. 区分面试官和候选人的对话（如果有明显的对话结构），并在完整的句子前面添加对话人物名称
        例如：
        面试官：你好，过来面试是吧？简单说下，你会Java不？
        候选人：会的会的，我做了一年多Java开发了，基础的都没问题

        【原始文字稿】
        {transcript}

        请直接返回整理后的文字稿，不要添加任何额外说明。
    """

    llm = get_llm_instance()
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["transcript"]
    )

    try:
        chain = prompt | RunnableLambda(print_prompt) | llm | RunnableLambda(print_llm_response)
        result = await chain.ainvoke({"transcript": transcript})
        return result.content
    except Exception as e:
        logger.error(f"文字稿润色失败: {str(e)}", exc_info=True)
        return transcript

# ==================== 语音转写相关功能 ====================



async def async_create_questions_mixed(position_obj: JobPosition, resume_obj: Resume, question_types: list[str],
                                       difficulty: str, count: int, with_answer: bool):
    """
    基于岗位要求+候选人简历混合模式生成面试题目

    :param position_obj: 岗位对象
    :param resume_obj: 简历对象
    :param question_types: 题目类型列表（英文：technical/behavioral/situational/open）
    :param difficulty: 难度等级（英文：junior/middle/senior）
    :param count: 生成题目数量
    :param with_answer: 是否生成参考答案
    :return: LLMQuestionResponse 对象或 None
    """
    # 类型映射：英文 -> 中文（用于Prompt展示）
    type_name_map = {
        "technical": "技术类",
        "behavioral": "行为类",
        "situational": "情景类",
        "open": "开放类"
    }

    # 难度映射：英文 -> 中文（用于Prompt展示）
    difficulty_name_map = {
        "junior": "初级",
        "middle": "中级",
        "senior": "高级"
    }

    # 转换为中文用于Prompt
    question_types_cn = [type_name_map.get(t, t) for t in question_types]
    difficulty_cn = difficulty_name_map.get(difficulty, difficulty)

    # 定义Prompt模板
    prompt_template = """
        你是一位资深的技术面试官，请根据以下信息生成面试题目。

        【目标岗位】
        岗位名称：{position_name}
        岗位职责：
        {job_description}

        任职要求：
        {requirements}

        【候选人信息】
        姓名：{candidate_name}
        学历：{education} - {school} - {major}
        工作年限：{work_years}年
        当前职位：{current_position} @ {current_company}
        技能标签：{skills}
        工作经历摘要：{work_experience_summary}
        项目经验摘要：{project_experience_summary}

        【生成要求】
        - 题目类型：{question_types}（可多选：技术类/行为类/情景类/开放类）
        - 难度等级：{difficulty}（初级/中级/高级）
        - 题目数量：{count}题
        - 是否生成参考答案：{with_answer}

        请按以下JSON格式返回：
        {{
            "questions": [
                {{
                    "type": "技术类",
                    "difficulty": "中级",
                    "question": "题目内容",
                    "reference_answer": "参考答案（如需要）",
                    "scoring_points": ["评分要点1", "评分要点2"],
                    "source": "基于岗位要求+候选人简历"
                }}
            ]
        }}

        要求：
        1. 技术类题目要结合岗位技术栈和候选人技能
        2. 行为类题目要基于候选人的工作经历设计
        3. 题目要有区分度，能考察真实能力
        4. 参考答案要给出关键点，不要过于冗长
        5. source字段统一填写为"基于岗位要求+候选人简历"
    """

    # 初始化解析器和Prompt（使用LLMQuestionResponse解析整个列表）
    parser = PydanticOutputParser(pydantic_object=LLMQuestionResponse)
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=[
            "position_name", "job_description", "requirements",
            "candidate_name", "education", "school", "major",
            "work_years", "current_position", "current_company",
            "skills", "work_experience_summary", "project_experience_summary",
            "question_types", "difficulty", "count", "with_answer"
        ],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    try:
        # 创建解析链并执行
        chain = prompt | create_parse_chain(parser)
        result = await chain.ainvoke({
            "position_name": position_obj.position_name,
            "job_description": position_obj.job_description or "",
            "requirements": position_obj.requirements or "",
            "candidate_name": resume_obj.candidate_name or "",
            "education": resume_obj.education or "",
            "school": resume_obj.school or "",
            "major": resume_obj.major or "",
            "work_years": resume_obj.work_years or 0,
            "current_position": resume_obj.current_position or "",
            "current_company": resume_obj.current_company or "",
            "skills": "、".join(resume_obj.skills) if resume_obj.skills else "",
            "work_experience_summary": resume_obj.work_experience or "",
            "project_experience_summary": resume_obj.project_experience or "",
            "question_types": "、".join(question_types_cn),
            "difficulty": difficulty_cn,
            "count": count,
            "with_answer": "是" if with_answer else "否"
        })
        return result
    except Exception as e:
        logger.error(f"LLM生成题目失败: {str(e)}", exc_info=True)
        return None


async def generate_interview_summary_by_recording(duration: int, candidate_name: str, position_name: str, transcript: str) -> InterviewSummaryResponse | None:
    """
    通过录音转写文件提取面试摘要信息
    :param duration:
    :param candidate_name:
    :param position_name:
    :param transcript:
    :return:
    """

    # 定义Prompt模板
    prompt_template = """
        你是一位专业的HR助手，请从以下面试记录中提取结构化摘要。
        
        【面试信息】
        候选人：{candidate_name}
        应聘岗位：{position_name}
        面试时长：{duration}分钟
        
        【面试文字稿】
        {transcript}
        
        请按以下JSON格式返回摘要：
        {{
            "summary_overview": "面试整体概述（150-200字，包含面试氛围、候选人整体表现等）",
        
            "key_qa": [
                {{
                    "question": "面试官提出的重要问题",
                    "answer_summary": "候选人回答的要点概述（100字以内）",
                    "answer_quality": "优秀/良好/一般/较差"
                }}
            ],
        
            "technical_skills": ["技术能力标签1", "技术能力标签2"],
        
            "soft_skills": ["软技能标签1", "软技能标签2"],
        
            "highlights": [
                "亮点1：具体描述",
                "亮点2：具体描述"
            ],
        
            "concerns": [
                "疑虑1：具体描述",
                "疑虑2：具体描述"
            ],
        
            "candidate_questions": [
                "候选人提出的问题1",
                "候选人提出的问题2"
            ]
        }}
        
        严格遵循以下格式规范：
        {format_instructions}
        
        提取要求：
        1. 核心问答选择最能体现候选人能力的3-5个问题
        2. 技术能力标签要具体，如"微服务架构"而非"技术能力强"
        3. 亮点和疑虑要有具体事例支撑
        4. 回答质量判断要基于回答的完整性、逻辑性、专业性
    """

    # 初始化解析器和Prompt（使用InterviewSummaryResponse解析模型回答内容）
    parser = PydanticOutputParser(pydantic_object=InterviewSummaryResponse)
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=[
            "candidate_name", "position_name", "duration", "transcript"
        ],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    try:
        # 创建解析链并执行
        chain = prompt | create_parse_chain(parser)
        result = await chain.ainvoke({
            "candidate_name": candidate_name,
            "position_name": position_name,
            "duration": duration,
            "transcript": transcript
        })
        return result
    except Exception as e:
        logger.error(f"LLM生成面试摘要失败: {str(e)}", exc_info=True)
        return None


async def generate_interview_summary_by_summary_info(duration: int, candidate_name: str, position_name: str, all_summary_info: str) -> InterviewSummaryResponse | None:
    """
    通过多条摘要信息，生成汇总摘要信息
    :param all_summary_info:
    :return:
    """

    # 定义Prompt模板
    prompt_template = """
        你是一位专业的HR助手，请从多条面试摘要信息中，汇总出最终摘要信息。

        【面试信息】
        候选人：{candidate_name}
        应聘岗位：{position_name}
        面试时长：{duration}分钟

        【多条面试摘要信息】
        {all_summary_info}

        请按以下JSON格式返回汇总摘要信息：
        {{
            "summary_overview": "面试整体概述（150-200字，包含面试氛围、候选人整体表现等）",

            "key_qa": [
                {{
                    "question": "面试官提出的重要问题",
                    "answer_summary": "候选人回答的要点概述（100字以内）",
                    "answer_quality": "优秀/良好/一般/较差"
                }}
            ],

            "technical_skills": ["技术能力标签1", "技术能力标签2"],

            "soft_skills": ["软技能标签1", "软技能标签2"],

            "highlights": [
                "亮点1：具体描述",
                "亮点2：具体描述"
            ],

            "concerns": [
                "疑虑1：具体描述",
                "疑虑2：具体描述"
            ],

            "candidate_questions": [
                "候选人提出的问题1",
                "候选人提出的问题2"
            ]
        }}

        严格遵循以下格式规范：
        {format_instructions}

        提取要求：
        1. 核心问答（key_qa）选择最能体现候选人能力的3-5个问题
        2. 技术能力标签要具体，如"微服务架构"而非"技术能力强"
        3. 亮点和疑虑要有具体事例支撑
        4. 回答质量判断要基于回答的完整性、逻辑性、专业性
        5. 每个键的内容不要单纯的叠加，要再进行分析，选出更符合的面试摘要信息
    """

    # 初始化解析器和Prompt（使用InterviewSummaryResponse解析模型回答内容）
    parser = PydanticOutputParser(pydantic_object=InterviewSummaryResponse)
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=[
            "candidate_name", "position_name", "duration", "all_summary_info"
        ],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    try:
        # 创建解析链并执行
        chain = prompt | create_parse_chain(parser)
        result = await chain.ainvoke({
            "candidate_name": candidate_name,
            "position_name": position_name,
            "duration": duration,
            "all_summary_info": all_summary_info
        })
        return result
    except Exception as e:
        logger.error(f"LLM生成汇总面试摘要失败: {str(e)}", exc_info=True)
        return None

