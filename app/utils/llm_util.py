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

from app.models.position import JobPosition
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



