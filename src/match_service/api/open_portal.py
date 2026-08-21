"""
Open Portal API - 官网开放接口

只读API，用于官网展示标准数据和推荐规则
- 只暴露 is_active=true 的数据
- 限流保护
- 与管理后台路由物理隔离
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/open", tags=["Open Portal"])


async def _get_session() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session


def _normalize_version(version: Optional[str]) -> Optional[str]:
    """统一版本号格式为小写

    将前端传入的版本号统一转为小写，解决数据库大小写不一致问题。
    数据库中存储的版本号是小写格式（v3.8.2, v4.0.0）

    例如: V3.8.2 -> v3.8.2, V4.0.0 -> v4.0.0

    Args:
        version: 原始版本号（可能为 None 或任意大小写）

    Returns:
        小写版本号或 None
    """
    if version and version.strip():
        return version.lower()
    return None


# ============================================================================
# 统计信息接口
# ============================================================================

@router.get("/stats")
async def get_stats(session: AsyncSession = Depends(_get_session)):
    """推荐系统统计信息
    
    返回：
    - total_panels: 推荐面板总数
    - total_topics: 推荐主题总数
    - total_scenarios: 临床场景总数
    - total_recommendations: 推荐规则总数
    """
    # TODO: 这些统计需要从推荐系统数据库获取
    # 目前返回占位数据
    return {
        "total_panels": 0,
        "total_topics": 0,
        "total_scenarios": 0,
        "total_recommendations": 0,
        "note": "推荐系统数据待接入"
    }


@router.get("/standards/stats")
async def get_standard_stats(session: AsyncSession = Depends(_get_session)):
    """标准统计信息
    
    返回：
    - total: 标准总数
    - by_modality: 各模态分布
    - by_version: 各版本分布
    """
    try:
        # 总数
        result = await session.execute(
            text("SELECT COUNT(*) FROM standard_check_items WHERE is_active = true")
        )
        total = result.scalar()
        
        # 按模态分布
        result = await session.execute(text("""
            SELECT modality, COUNT(*) as count
            FROM standard_check_items
            WHERE is_active = true
            GROUP BY modality
            ORDER BY count DESC
        """))
        by_modality = {row[0]: row[1] for row in result}
        
        # 按版本分布
        result = await session.execute(text("""
            SELECT version, COUNT(*) as count
            FROM standard_check_items
            WHERE is_active = true
            GROUP BY version
            ORDER BY version DESC
        """))
        by_version = {row[0]: row[1] for row in result}
        
        return {
            "total": total,
            "by_modality": by_modality,
            "by_version": by_version
        }
    except Exception as e:
        logger.error(f"获取标准统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")


@router.get("/standards/versions")
async def get_versions(session: AsyncSession = Depends(_get_session)):
    """获取所有标准版本信息"""
    try:
        result = await session.execute(text("""
            SELECT version, COUNT(*) as count
            FROM standard_check_items
            WHERE is_active = true
            GROUP BY version
            ORDER BY version DESC
        """))
        
        versions = []
        for row in result:
            version_name = row[0] or "未标注"
            count = row[1]
            
            # 根据版本名称推断标签和状态
            if version_name == "V3.8.2":
                label = "基础版（2024）"
                status = "legacy"
                release_date = "2024-06-01"
            elif version_name == "V4.0":
                label = "医保适配版（2025）"
                status = "current"
                release_date = "2025-08-01"
            else:
                label = version_name
                status = "unknown"
                release_date = None
            
            versions.append({
                "version": version_name,
                "label": label,
                "release_date": release_date,
                "status": status,
                "stats": {"total": count}
            })
        
        return versions
    except Exception as e:
        logger.error(f"获取版本列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取版本列表失败")


# ============================================================================
# 推荐规则接口（占位，待后续实现）
# ============================================================================

@router.get("/panels")
async def get_panels(
    source_type: Optional[str] = None,
    session: AsyncSession = Depends(_get_session)
):
    """推荐面板列表
    
    参数：
    - source_type: 可选，筛选来源类型（ACR/本地化）
    """
    # TODO: 从推荐系统数据库获取
    return {
        "panels": [],
        "note": "推荐系统数据待接入"
    }


@router.get("/topics")
async def get_topics(
    panel_id: Optional[int] = None,
    source_type: Optional[str] = None,
    session: AsyncSession = Depends(_get_session)
):
    """推荐主题列表
    
    参数：
    - panel_id: 可选，按面板筛选
    - source_type: 可选，筛选来源类型
    """
    # TODO: 从推荐系统数据库获取
    return {
        "topics": [],
        "note": "推荐系统数据待接入"
    }


@router.get("/topics/{topic_id}")
async def get_topic_detail(
    topic_id: int,
    source_type: Optional[str] = None,
    session: AsyncSession = Depends(_get_session)
):
    """主题详情
    
    返回主题的所有场景和评分信息
    """
    # TODO: 从推荐系统数据库获取
    return {
        "topic": None,
        "note": "推荐系统数据待接入"
    }


@router.get("/search")
async def search_recommendations(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    source_type: Optional[str] = None,
    session: AsyncSession = Depends(_get_session)
):
    """搜索推荐规则
    
    参数：
    - q: 搜索关键词
    - source_type: 可选，筛选来源类型
    """
    # TODO: 从推荐系统数据库搜索
    return {
        "results": [],
        "note": "推荐系统数据待接入"
    }


@router.get("/recommendations/{semantic_id}/provenance")
async def get_provenance(
    semantic_id: str,
    session: AsyncSession = Depends(_get_session)
):
    """规则溯源信息
    
    返回规则的来源、版本、评审等信息
    """
    # TODO: 从推荐系统数据库获取
    return {
        "provenance": None,
        "note": "推荐系统数据待接入"
    }


# ============================================================================
# 标准目录接口
# ============================================================================

@router.get("/standards/items")
async def get_standard_items(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    modality: Optional[str] = Query(None, description="模态筛选"),
    version: Optional[str] = Query(None, description="版本筛选"),
    body_part_l1: Optional[str] = Query(None, description="一级部位筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    session: AsyncSession = Depends(_get_session)
):
    """标准项目列表（分页查询）
    
    参数：
    - page: 页码（从1开始）
    - page_size: 每页数量（1-100）
    - modality: 模态筛选（CT/MR/US等）
    - version: 版本筛选（V3.8.2/V4.0）
    - body_part_l1: 一级部位筛选
    - keyword: 关键词搜索（匹配项目名称）
    
    返回：
    - total: 总记录数
    - page: 当前页码
    - page_size: 每页数量
    - total_pages: 总页数
    - items: 项目列表
    """
    try:
        # 统一版本号格式为小写
        version = _normalize_version(version)

        # 构建查询条件
        where_clauses = ["is_active = true"]
        params = {}

        if modality:
            where_clauses.append("modality = :modality")
            params["modality"] = modality

        if version:
            where_clauses.append("version = :version")
            params["version"] = version
        
        if body_part_l1:
            where_clauses.append("body_part_l1 = :body_part_l1")
            params["body_part_l1"] = body_part_l1
        
        if keyword:
            where_clauses.append("item_name ILIKE :keyword")
            params["keyword"] = f"%{keyword}%"
        
        where_sql = " AND ".join(where_clauses)
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) FROM standard_check_items WHERE {where_sql}"
        result = await session.execute(text(count_sql), params)
        total = result.scalar()
        
        # 计算分页
        offset = (page - 1) * page_size
        total_pages = (total + page_size - 1) // page_size
        
        # 查询数据
        query_sql = f"""
            SELECT 
                id, item_code, item_name, modality, modality_code,
                body_part_l1, body_part_l1_code,
                body_part_l2, body_part_l2_code,
                body_part_l3, body_part_l3_code,
                body_part_code,
                scan_method, scan_method_code,
                post_processing, post_processing_code,
                insurance_code,
                version, source
            FROM standard_check_items
            WHERE {where_sql}
            ORDER BY modality, item_code
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = page_size
        params["offset"] = offset
        
        result = await session.execute(text(query_sql), params)
        rows = result.fetchall()
        
        items = []
        for row in rows:
            items.append({
                "id": row[0],
                "item_code": row[1],
                "item_name": row[2],
                "modality": row[3],
                "modality_code": row[4],
                "body_part_l1": row[5],
                "body_part_l1_code": row[6],
                "body_part_l2": row[7],
                "body_part_l2_code": row[8],
                "body_part_l3": row[9],
                "body_part_l3_code": row[10],
                "body_part_code": row[11],
                "scan_method": row[12],
                "scan_method_code": row[13],
                "post_processing": row[14],
                "post_processing_code": row[15],
                "insurance_code": row[16],
                "version": row[17],
                "source": row[18]
            })
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "items": items
        }
    
    except Exception as e:
        logger.error(f"查询标准项目列表失败: {e}")
        raise HTTPException(status_code=500, detail="查询失败")


@router.get("/standards/filter-options")
async def get_filter_options(
    modality: Optional[str] = Query(None, description="模态筛选"),
    version: Optional[str] = Query(None, description="版本筛选"),
    session: AsyncSession = Depends(_get_session)
):
    """获取筛选选项
    
    参数：
    - modality: 可选，限定模态后获取该模态下的其他筛选项
    - version: 可选，限定版本后获取该版本下的其他筛选项
    
    返回：
    - modalities: 可用模态列表
    - versions: 可用版本列表
    - body_part_l1_options: 一级部位选项
    """
    try:
        # 统一版本号格式为小写
        version = _normalize_version(version)

        where_clauses = ["is_active = true"]
        params = {}

        if modality:
            where_clauses.append("modality = :modality")
            params["modality"] = modality

        if version:
            where_clauses.append("version = :version")
            params["version"] = version
        
        where_sql = " AND ".join(where_clauses)
        
        # 获取可用模态
        result = await session.execute(text(f"""
            SELECT DISTINCT modality, COUNT(*) as count
            FROM standard_check_items
            WHERE {where_sql}
            GROUP BY modality
            ORDER BY modality
        """), params)
        modalities = [{"value": row[0], "count": row[1]} for row in result]
        
        # 获取可用版本
        result = await session.execute(text(f"""
            SELECT DISTINCT version, COUNT(*) as count
            FROM standard_check_items
            WHERE {where_sql}
            GROUP BY version
            ORDER BY version DESC
        """), params)
        versions = [{"value": row[0], "count": row[1]} for row in result]
        
        # 获取一级部位选项
        result = await session.execute(text(f"""
            SELECT DISTINCT body_part_l1, COUNT(*) as count
            FROM standard_check_items
            WHERE {where_sql} AND body_part_l1 IS NOT NULL
            GROUP BY body_part_l1
            ORDER BY body_part_l1
        """), params)
        body_part_l1_options = [{"value": row[0], "count": row[1]} for row in result]
        
        return {
            "modalities": modalities,
            "versions": versions,
            "body_part_l1_options": body_part_l1_options
        }
    
    except Exception as e:
        logger.error(f"获取筛选选项失败: {e}")
        raise HTTPException(status_code=500, detail="获取筛选选项失败")


@router.get("/standards/items/{item_id}")
async def get_standard_item(
    item_id: int,
    session: AsyncSession = Depends(_get_session)
):
    """标准项目详情
    
    返回完整的标准项目信息
    """
    try:
        result = await session.execute(text("""
            SELECT
                id, item_code, item_name, modality, modality_code,
                body_part_l1, body_part_l1_code,
                body_part_l2, body_part_l2_code,
                body_part_l3, body_part_l3_code,
                body_part_code,
                scan_method, scan_method_code,
                post_processing, post_processing_code,
                insurance_code,
                source, version, coverage_status, supplement_status,
                created_at, updated_at,
                body_position, scan_scope, contrast_agent,
                image_region, image_focus, scan_method_detail, scan_param,
                coil, base_sequence, compose_sequence,
                clinical_indication, clinical_significance,
                organs, anatomical_structure, technical_notes,
                image_grade, image_score
            FROM standard_check_items
            WHERE id = :item_id AND is_active = true
        """), {"item_id": item_id})

        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="标准项目不存在")

        # 使用 _mapping 属性按列名访问，避免硬编码索引的脆弱性
        row_dict = dict(row._mapping)

        return {
            "id": row_dict["id"],
            "item_code": row_dict["item_code"],
            "item_name": row_dict["item_name"],
            "modality": row_dict["modality"],
            "modality_code": row_dict["modality_code"],
            "body_part_l1": row_dict["body_part_l1"],
            "body_part_l1_code": row_dict["body_part_l1_code"],
            "body_part_l2": row_dict["body_part_l2"],
            "body_part_l2_code": row_dict["body_part_l2_code"],
            "body_part_l3": row_dict["body_part_l3"],
            "body_part_l3_code": row_dict["body_part_l3_code"],
            "body_part_code": row_dict["body_part_code"],
            "scan_method": row_dict["scan_method"],
            "scan_method_code": row_dict["scan_method_code"],
            "post_processing": row_dict["post_processing"],
            "post_processing_code": row_dict["post_processing_code"],
            "insurance_code": row_dict["insurance_code"],
            "source": row_dict["source"],
            "version": row_dict["version"],
            "coverage_status": row_dict["coverage_status"],
            "supplement_status": row_dict["supplement_status"],
            "created_at": str(row_dict["created_at"]) if row_dict["created_at"] else None,
            "updated_at": str(row_dict["updated_at"]) if row_dict["updated_at"] else None,
            "body_position": row_dict["body_position"],
            "scan_scope": row_dict["scan_scope"],
            "contrast_agent": row_dict["contrast_agent"],
            "image_region": row_dict["image_region"],
            "image_focus": row_dict["image_focus"],
            "scan_method_detail": row_dict["scan_method_detail"],
            "scan_param": row_dict["scan_param"],
            "coil": row_dict["coil"],
            "base_sequence": row_dict["base_sequence"],
            "compose_sequence": row_dict["compose_sequence"],
            "clinical_indication": row_dict["clinical_indication"],
            "clinical_significance": row_dict["clinical_significance"],
            "organs": row_dict["organs"],
            "anatomical_structure": row_dict["anatomical_structure"],
            "technical_notes": row_dict["technical_notes"],
            "image_grade": row_dict["image_grade"],
            "image_score": row_dict["image_score"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取标准项目详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取详情失败")


@router.get("/standards/versions/compare")
async def compare_versions(
    v1: str = Query(..., description="版本1"),
    v2: str = Query(..., description="版本2"),
    session: AsyncSession = Depends(_get_session)
):
    """版本对比
    
    对比两个版本的差异
    """
    try:
        # 获取v1独有的项目
        result = await session.execute(text("""
            SELECT COUNT(*)
            FROM standard_check_items
            WHERE version = :v1 AND is_active = true
              AND item_code NOT IN (
                  SELECT item_code FROM standard_check_items
                  WHERE version = :v2 AND is_active = true
              )
        """), {"v1": v1, "v2": v2})
        v1_only = result.scalar()
        
        # 获取v2独有的项目
        result = await session.execute(text("""
            SELECT COUNT(*)
            FROM standard_check_items
            WHERE version = :v2 AND is_active = true
              AND item_code NOT IN (
                  SELECT item_code FROM standard_check_items
                  WHERE version = :v1 AND is_active = true
              )
        """), {"v1": v1, "v2": v2})
        v2_only = result.scalar()
        
        # 获取共同的项目
        result = await session.execute(text("""
            SELECT COUNT(*)
            FROM standard_check_items a
            WHERE a.version = :v1 AND a.is_active = true
              AND EXISTS (
                  SELECT 1 FROM standard_check_items b
                  WHERE b.version = :v2 AND b.is_active = true
                    AND b.item_code = a.item_code
              )
        """), {"v1": v1, "v2": v2})
        common = result.scalar()
        
        return {
            "v1": v1,
            "v2": v2,
            "v1_only": v1_only,
            "v2_only": v2_only,
            "common": common,
            "comparison": {
                "added_in_v2": v2_only,
                "removed_in_v2": v1_only,
                "unchanged": common
            }
        }
    
    except Exception as e:
        logger.error(f"版本对比失败: {e}")
        raise HTTPException(status_code=500, detail="版本对比失败")
