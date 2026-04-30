import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import position, resume, interview_evaluation, candidate_comparison, interview_summary
from app.models.resume import Resume
from app.schemas.candidate_comparison import CandidateComparisonRequest, PositionInfo, CandidateInfo, EvaluationScore, \
    CandidateComparisonDetailResponse, CandidateComparisonResponse, PageInfo, CandidateComparisonListResponse
from app.utils import llm_util, file_util, path_tool
from app.utils.logger_handler import logger
from app.utils.response import response


async def create_comparison_service(request: CandidateComparisonRequest, db: AsyncSession):
    try:
        # 获取页面条件
        position_id: int = request.position_id
        resume_ids: list[int] = request.resume_ids

        # 查询岗位信息
        position_obj = await position.get_position_by_id(position_id, db)

        if not position_obj:
            return response(code=404, message="岗位不存在", data=None)

            # 根据简历ID查询简历信息及评分信息
        resume_list = await resume.async_get_resume_by_ids_db(db, resume_ids)

        if not resume_list:
            return response(code=404, message="未找到简历信息", data=None)

        interview_evaluation_list = await interview_evaluation.async_get_interview_evaluation_list_db_by_resume_ids(resume_ids, db)
        # {简历ID: 评分信息}
        interview_evaluation_dict = {item.resume_id: item for item in interview_evaluation_list}

        interview_summary_list = await interview_summary.async_get_interview_summary_list_db_by_resume_ids(resume_ids, db)
        # {简历ID: 面试摘要}
        interview_summary_dict = {item.resume_id: item for item in interview_summary_list}

        # 组装候选人对比数据
        position_info = PositionInfo(id=position_obj.id, name=position_obj.position_name)
        candidates = []
        for item in resume_list:
            resume_item: Resume = item
            evaluation_obj = interview_evaluation_dict.get(resume_item.id)
            summary_obj = interview_summary_dict.get(resume_item.id)

            # 面试评价信息
            if evaluation_obj:
                evaluation_data = EvaluationScore(
                    professional_score=evaluation_obj.professional_score,
                    logic_score=evaluation_obj.logic_score,
                    communication_score=evaluation_obj.communication_score,
                    learning_score=evaluation_obj.learning_score,
                    teamwork_score=evaluation_obj.teamwork_score,
                    culture_score=evaluation_obj.culture_score,
                    total_score=float(evaluation_obj.total_score)
                )

            else:
                evaluation_data = None

            # 面试摘要信息
            if summary_obj:
                highlights = json.loads(summary_obj.highlights)
                concerns = json.loads(summary_obj.concerns)
            else:
                highlights = None
                concerns = None

            candidates.append(
                CandidateInfo(
                    resume_id=resume_item.id,
                    name=resume_item.candidate_name,
                    education=resume_item.education,
                    school=resume_item.school,
                    work_years=resume_item.work_years,
                    current_position=resume_item.current_position,
                    current_company=resume_item.current_company,
                    skills=resume_item.skills,
                    evaluation=evaluation_data,
                    highlights=highlights,
                    concerns=concerns
                )
            )

        # 将候选人对比数据保存到数据库
        candidate_comparison_dict = {
            "position_id": position_id,
            "resume_ids": resume_ids,
            "comparison_data": [item.model_dump(mode="json", exclude_none=True) for item in candidates],
            "created_by": 1
        }
        candidate_comparison_orm = await candidate_comparison.async_create_candidate_comparison_db(db, candidate_comparison_dict)

        response_data = CandidateComparisonDetailResponse(id=candidate_comparison_orm.id, position=position_info, candidates=candidates)

        return response(code=0, message="success", data=response_data)

        # 组装返回页面信息
    except Exception as e:
        logger.error(f"创建候选人对比失败：{e}", exc_info=True)
        return response(code=500, message="创建候选人对比失败", data=None)


async def generate_comparison_ai_analysis_service(id: int, db: AsyncSession):
    try:
        # 获取候选人对比信息
        candidate_comparison_orm = await candidate_comparison.async_get_candidate_comparison_by_id_db(id, db)
        if not candidate_comparison_orm:
            return response(code=404, message="候选人对比不存在", data=None)

        # 获取岗位信息
        position_id = candidate_comparison_orm.position_id
        position_obj = await position.get_position_by_id(position_id, db)

        # 获取对比数据信息
        comparison_data = candidate_comparison_orm.comparison_data
        if isinstance(comparison_data, str):
            comparison_data_obj = json.loads(comparison_data)  # 解析成json对象（列表）
        else:
            comparison_data_obj = comparison_data


        # 调用LLM获取分析结果数据
        ai_analysis_result = await llm_util.async_generate_comparison_ai_analysis(position_obj, comparison_data_obj)
        # 转换成字典对象，用于数据库更新
        ai_analysis_result_dict = ai_analysis_result.model_dump(mode="json", exclude_none=True)

        # 更新候选人对比信息
        candidate_comparison_orm = await candidate_comparison.async_update_candidate_comparison_by_id_db(db, id, ai_analysis_result_dict)

        # 组装数据返回页面
        return response(code=0, message="success", data=CandidateComparisonResponse.model_validate(candidate_comparison_orm))

    except Exception as e:
        logger.error(f"生成AI对比分析失败：{e}", exc_info=True)
        return response(code=500, message="生成AI对比分析失败", data=None)



async def get_comparison_detail_service(id: int, db: AsyncSession):
    try:
        candidate_comparison_orm = await candidate_comparison.async_get_candidate_comparison_by_id_db(id, db)

        # 组装数据返回页面
        return response(code=0, message="success", data=CandidateComparisonResponse.model_validate(candidate_comparison_orm))

    except Exception as e:
        logger.error(f"获取对比详情：{e}", exc_info=True)
        return response(code=500, message="获取对比详情", data=None)


async def get_history_comparison_list_service(position_id: int, page: int, page_size: int, db: AsyncSession):
    # 获取历史对比列表
    comparison_list_info = await candidate_comparison.get_history_comparison_list_db(position_id, page, page_size, db)
    total = comparison_list_info["total"]
    orm_data_list = comparison_list_info["data"]

    page_info = PageInfo(page=page, page_size=page_size, total=total, total_pages=total // page_size + (1 if total % page_size else 0))
    data_list = [CandidateComparisonResponse.model_validate(item) for item in orm_data_list]

    return response(code=0, message="success", data=CandidateComparisonListResponse(page_info=page_info, list=data_list))















# ===================================生成pdf报告==================================
import os
import tempfile
from datetime import datetime
from starlette.responses import FileResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


async def export_comparison_pdf_service(id: int, db: AsyncSession):
    """导出候选人对比PDF报告服务"""
    try:
        # 获取候选人对比信息
        comparison_orm = await candidate_comparison.async_get_candidate_comparison_by_id_db(id, db)
        if not comparison_orm:
            return response(code=404, message="候选人对比不存在", data=None)

        # 解析JSON数据
        comparison_data = comparison_orm.comparison_data if comparison_orm.comparison_data else []
        candidate_analysis = comparison_orm.candidate_analysis if comparison_orm.candidate_analysis else []
        ranking = comparison_orm.ranking if comparison_orm.ranking else []
        recommendation = comparison_orm.recommendation if comparison_orm.recommendation else {}

        # 获取岗位信息
        position_obj = await position.get_position_by_id(comparison_orm.position_id, db)
        position_name = position_obj.position_name if position_obj else "未知岗位"

        # 生成PDF文件
        pdf_path = await generate_comparison_pdf(
            position_name=position_name,
            comparison_data=comparison_data,
            comparison_summary=comparison_orm.comparison_summary,
            candidate_analysis=candidate_analysis,
            ranking=ranking,
            recommendation=recommendation,
            hiring_advice=comparison_orm.hiring_advice,
            created_at=comparison_orm.created_at
        )

        if not pdf_path or not os.path.isfile(pdf_path):
            return response(code=500, message="PDF文件生成失败", data=None)

        # 浏览器下载需要 HTTP 文件流，不能仅返回服务器本地绝对路径
        fname = os.path.basename(pdf_path)
        return FileResponse(
            path=pdf_path,
            filename=fname,
            media_type="application/pdf",
        )

    except Exception as e:
        logger.error(f"导出PDF失败：{e}", exc_info=True)
        return response(code=500, message="导出PDF失败", data=None)


def generate_radar_chart(comparison_data: list, save_path: str):
    """生成评分对比雷达图"""
    if not comparison_data:
        return

    # 提取候选人姓名和评分数据
    names = []
    scores_data = []

    for candidate in comparison_data:
        if candidate.get('evaluation'):
            names.append(candidate['name'])
            eval_data = candidate['evaluation']
            scores = [
                eval_data.get('professional_score', 0),
                eval_data.get('logic_score', 0),
                eval_data.get('communication_score', 0),
                eval_data.get('learning_score', 0),
                eval_data.get('teamwork_score', 0),
                eval_data.get('culture_score', 0)
            ]
            scores_data.append(scores)

    if not names:
        return

    # 雷达图维度
    dimensions = ['专业能力', '逻辑思维', '沟通表达', '学习能力', '团队协作', '文化匹配']
    num_vars = len(dimensions)

    # 计算角度
    angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
    angles += angles[:1]  # 闭合图形

    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(polar=True))

    # 颜色配置
    color_list = ['#67C23A', '#409EFF', '#909399', '#E6A23C', '#F56C6C', '#909399']

    # 绘制每个候选人的数据
    for idx, scores in enumerate(scores_data):
        scores_closed = scores + scores[:1]  # 闭合图形
        ax.plot(angles, scores_closed, 'o-', linewidth=2, label=names[idx], color=color_list[idx % len(color_list)])
        ax.fill(angles, scores_closed, alpha=0.15, color=color_list[idx % len(color_list)])

    # 设置维度标签
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dimensions, fontproperties='SimHei', fontsize=12)

    # 设置径向范围
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20', '40', '60', '80', '100'], fontproperties='SimHei')

    # 添加图例
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), prop={'family': 'SimHei', 'size': 12})

    ax.grid(True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def generate_bar_chart(comparison_data: list, save_path: str):
    """生成综合得分柱状图"""
    if not comparison_data:
        return

    # 提取候选人姓名和综合得分
    names = []
    total_scores = []

    for candidate in comparison_data:
        names.append(candidate['name'])
        if candidate.get('evaluation'):
            total_scores.append(candidate['evaluation'].get('total_score', 0))
        else:
            total_scores.append(0)

    if not names:
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    # 颜色配置
    color_list = ['#67C23A', '#409EFF', '#909399', '#E6A23C', '#F56C6C']
    colors = [color_list[i % len(color_list)] for i in range(len(names))]

    # 绘制柱状图
    bars = ax.bar(range(len(names)), total_scores, color=colors, alpha=0.8)

    # 设置标签
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, fontproperties='SimHei', fontsize=12)
    ax.set_ylabel('综合得分', fontproperties='SimHei', fontsize=14)
    ax.set_ylim(0, 100)

    # 在柱子上方添加数值标签
    for bar, score in zip(bars, total_scores):
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 1,
                f'{score:.1f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # 添加网格线
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


async def generate_comparison_pdf(
        position_name: str,
        comparison_data: list,
        comparison_summary: str,
        candidate_analysis: list,
        ranking: list,
        recommendation: dict,
        hiring_advice: str,
        created_at: datetime
) -> str:
    """生成候选人对比PDF报告"""
    # 注册中文字体 - 尝试多个字体路径以确保兼容性
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑 - Windows默认字体，显示效果较好
        "C:/Windows/Fonts/simhei.ttf",  # 黑体 - 备选字体
        "C:/Windows/Fonts/simsun.ttc"  # 宋体 - 最后备选
    ]

    # 找到第一个存在的字体文件，如果都不存在则使用第一个路径（会报错但便于调试）
    font_path = next((p for p in font_paths if os.path.exists(p)), font_paths[0])
    pdfmetrics.registerFont(TTFont('Chinese', font_path))

    # 创建临时文件目录 - 使用工程路径而非系统临时目录
    temp_dir = path_tool.get_abs_path(
        os.path.join(file_util.UPLOAD_DIR, f"{datetime.now().strftime("%Y%m%d")}/pdf_report")
    )

    # 确保目录存在，如果不存在则递归创建
    os.makedirs(temp_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    pdf_filename = f"{position_name}_候选人对比_{timestamp}.pdf"
    pdf_path = os.path.join(temp_dir, pdf_filename)

    # 创建PDF文档对象 - 使用A4纸张尺寸
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []

    # 标题样式 - 用于报告主标题
    title_style = ParagraphStyle(
        'Title',
        fontName='Chinese',  # 使用中文字体
        fontSize=20,  # 字号20，突出显示
        alignment=TA_CENTER,  # 居中对齐
        spaceAfter=20  # 段后间距20磅
    )

    # 章节标题样式 - 用于一级章节标题（如"一、对比总结"）
    section_style = ParagraphStyle(
        'Section',
        fontName='Chinese',  # 使用中文字体
        fontSize=16,  # 字号16，比正文大
        textColor=colors.HexColor('#409EFF'),  # 蓝色主题色
        spaceBefore=15,  # 段前间距15磅
        spaceAfter=10,  # 段后间距10磅
        leading=24  # 行高24磅
    )

    # 子标题样式 - 用于二级标题（如候选人姓名）
    subsection_style = ParagraphStyle(
        'Subsection',
        fontName='Chinese',  # 使用中文字体
        fontSize=14,  # 字号14，介于章节标题和正文之间
        textColor=colors.HexColor('#67C23A'),  # 绿色，区分层级
        spaceBefore=10,  # 段前间距10磅
        spaceAfter=8,  # 段后间距8磅
        leading=20  # 行高20磅
    )

    # 正文样式 - 用于普通文本内容
    body_style = ParagraphStyle(
        'Body',
        fontName='Chinese',  # 使用中文字体
        fontSize=11,  # 字号11，适合阅读
        alignment=TA_JUSTIFY,  # 两端对齐，使文本更整齐
        spaceAfter=8,  # 段后间距8磅
        leading=18  # 行高18磅，保证行间距舒适
    )

    # 列表项样式 - 用于列表项展示，增加左侧缩进
    list_style = ParagraphStyle(
        'List',
        fontName='Chinese',  # 使用中文字体
        fontSize=11,  # 字号11，与正文一致
        alignment=TA_LEFT,  # 左对齐
        spaceAfter=5,  # 段后间距5磅，紧凑排列
        leading=16,  # 行高16磅
        leftIndent=20  # 左侧缩进20磅，形成层级感
    )

    # 强调文本样式 - 用于标签和关键字段名
    label_style = ParagraphStyle(
        'Label',
        fontName='Chinese',  # 使用中文字体
        fontSize=11,  # 字号11
        textColor=colors.HexColor('#303133'),  # 深灰色，突出重点
        spaceAfter=3,  # 段后间距3磅
        leading=16  # 行高16磅
    )

    # 添加报告标题
    elements.append(Paragraph(f"{position_name} - 候选人对比报告", title_style))
    elements.append(Paragraph(f"生成时间：{created_at.strftime('%Y-%m-%d %H:%M:%S')}", body_style))
    elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.HexColor('#409EFF')))

    # 一、对比总结
    elements.append(Paragraph("一、对比总结", section_style))
    if comparison_summary:
        elements.append(Paragraph(comparison_summary, body_style))
    else:
        elements.append(Paragraph("暂无对比总结", body_style))

    # 二、评分对比雷达图
    elements.append(Paragraph("二、评分对比雷达图", section_style))
    radar_chart_path = os.path.join(temp_dir, f"radar_chart_{timestamp}.png")
    generate_radar_chart(comparison_data, radar_chart_path)

    if os.path.exists(radar_chart_path):
        elements.append(Image(radar_chart_path, width=450, height=320))

    # 三、综合得分柱状图
    elements.append(Paragraph("三、综合得分柱状图", section_style))
    bar_chart_path = os.path.join(temp_dir, f"bar_chart_{timestamp}.png")
    generate_bar_chart(comparison_data, bar_chart_path)

    if os.path.exists(bar_chart_path):
        elements.append(Image(bar_chart_path, width=450, height=280))

    # 四、候选人分析
    elements.append(Paragraph("四、候选人分析", section_style))
    if candidate_analysis:
        for idx, analysis in enumerate(candidate_analysis, 1):
            # 获取候选人姓名
            candidate_name = analysis.get('name', f'候选人{idx}')
            elements.append(Paragraph(f"4.{idx} {candidate_name}", subsection_style))

            # 优势 - 将advantages_over_others转换为中文标签并格式化展示
            advantages = analysis.get('advantages_over_others', [])
            if advantages:
                elements.append(Paragraph("<b>相比其他候选人的优势：</b>", label_style))
                for adv in advantages:
                    elements.append(Paragraph(f"• {adv}", list_style))
                elements.append(Spacer(1, 5))  # 添加小间距

            # 劣势 - 将disadvantages转换为中文标签并格式化展示
            disadvantages = analysis.get('disadvantages', [])
            if disadvantages:
                elements.append(Paragraph("<b>相比其他候选人的劣势：</b>", label_style))
                for dis in disadvantages:
                    elements.append(Paragraph(f"• {dis}", list_style))
                elements.append(Spacer(1, 5))  # 添加小间距

            # 适合场景 - 将suitable_scenarios转换为中文标签
            suitable_scenarios = analysis.get('suitable_scenarios', '')
            if suitable_scenarios:
                elements.append(Paragraph("<b>最适合的场景：</b>", label_style))
                elements.append(Paragraph(suitable_scenarios, list_style))
                elements.append(Spacer(1, 5))  # 添加小间距

            # 风险点 - 将risk_points转换为中文标签
            risk_points = analysis.get('risk_points', '')
            if risk_points:
                elements.append(Paragraph("<b>录用风险点：</b>", label_style))
                elements.append(Paragraph(risk_points, list_style))

            elements.append(Spacer(1, 10))  # 候选人之间的间距
    else:
        elements.append(Paragraph("暂无候选人分析", body_style))

    # 五、排名结果
    elements.append(Paragraph("五、排名结果", section_style))
    if ranking:
        for rank_item in ranking:
            # 修复：使用score字段而非total_score，并正确显示排名
            rank_num = rank_item.get('rank', 0)
            name = rank_item.get('name', '未知')
            score = rank_item.get('score', 0)  # 修正：使用score字段
            reason = rank_item.get('reason', '')

            # 格式化排名信息
            rank_text = f"<b>第{rank_num}名：{name}</b> - 综合得分：{score}"
            elements.append(Paragraph(rank_text, body_style))

            # 显示排名理由
            if reason:
                elements.append(Paragraph(f"  排名理由：{reason}", list_style))

            elements.append(Spacer(1, 8))  # 排名项之间的间距
    else:
        elements.append(Paragraph("暂无排名结果", body_style))

    # 六、候选人建议
    elements.append(Paragraph("六、候选人建议", section_style))
    if recommendation:
        # 最佳人选 - 将best_choice转换为中文标签
        best_choice = recommendation.get('best_choice', '')
        if best_choice:
            elements.append(Paragraph("<b>最佳人选：</b>", label_style))
            elements.append(Paragraph(best_choice, list_style))
            elements.append(Spacer(1, 5))

        # 推荐理由 - 将reason转换为中文标签
        recommend_reason = recommendation.get('reason', '')
        if recommend_reason:
            elements.append(Paragraph("<b>推荐理由：</b>", label_style))
            elements.append(Paragraph(recommend_reason, list_style))
            elements.append(Spacer(1, 5))

        # 备选人选 - 将alternative转换为中文标签
        alternative = recommendation.get('alternative', '')
        if alternative:
            elements.append(Paragraph("<b>备选人选：</b>", label_style))
            elements.append(Paragraph(alternative, list_style))
            elements.append(Spacer(1, 5))

        # 备选理由 - 将alternative_reason转换为中文标签
        alternative_reason = recommendation.get('alternative_reason', '')
        if alternative_reason:
            elements.append(Paragraph("<b>备选理由：</b>", label_style))
            elements.append(Paragraph(alternative_reason, list_style))
    else:
        elements.append(Paragraph("暂无候选人建议", body_style))

    # 七、录用建议
    elements.append(Paragraph("七、录用建议", section_style))
    if hiring_advice:
        elements.append(Paragraph(hiring_advice, body_style))
    else:
        elements.append(Paragraph("暂无录用建议", body_style))

    # 生成PDF文件
    doc.build(elements)

    return pdf_path
# ===================================生成pdf报告==================================


