from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_comparison import CandidateComparison


async def async_create_candidate_comparison_db(db: AsyncSession, candidate_comparison_dict: dict) -> CandidateComparison:
    obj = CandidateComparison(**candidate_comparison_dict)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def async_get_candidate_comparison_by_id_db(id: int, db: AsyncSession):
    select_sql = select(CandidateComparison).where(CandidateComparison.id == id)
    result = await db.execute(select_sql)

    return result.scalar_one_or_none()


async def async_update_candidate_comparison_by_id_db(db: AsyncSession, id: int, ai_analysis_result_dict: dict) -> CandidateComparison | None:
    obj = await async_get_candidate_comparison_by_id_db(id, db)
    if not obj:
        return None

    for k, v in ai_analysis_result_dict.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_history_comparison_list_db(position_id: int, page: int, page_size: int, db: AsyncSession) -> dict[str, Any]:
    base_sql = select(CandidateComparison).where(CandidateComparison.position_id == position_id)

    # 获取总记录数
    total_count_sql = select(func.count()).select_from(base_sql.subquery())
    total_result = await db.execute(total_count_sql)
    total_count = total_result.scalar() or 0

    # 分页查询结果
    offset = (page - 1) * page_size
    data_sql = base_sql.offset(offset).limit(page_size)
    data_result = await db.execute(data_sql)
    data = data_result.scalars().all()

    result = {
        "total": total_count,
        "data": data
    }

    return result