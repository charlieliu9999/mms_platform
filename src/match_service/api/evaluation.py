"""
评测系统 API 路由

提供评测任务管理、执行、结果查询等接口
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session_factory
from ..models.evaluation import EvalTask, EvalDetail
from ..evaluation.runner import EvaluationRunner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])

# 全局评测执行器实例
_runner: Optional[EvaluationRunner] = None


def get_runner() -> EvaluationRunner:
    """获取评测执行器单例"""
    global _runner
    if _runner is None:
        _runner = EvaluationRunner()
    return _runner


# ==================== Pydantic 模型 ====================

class CreateTaskRequest(BaseModel):
    """创建评测任务请求"""
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    test_file_path: str = Field(..., description="测试文件路径")
    sample_size: Optional[int] = Field(None, description="采样数量，None=全部")
    modality: Optional[str] = Field(None, description="模态过滤（CT/DR/MR等）")
    tags: Optional[List[str]] = Field(None, description="标签")
    created_by: Optional[str] = Field(None, description="创建人")


class TaskResponse(BaseModel):
    """任务响应"""
    id: int
    name: str
    description: Optional[str]
    status: str
    progress: int
    total_count: int
    matched_count: int
    correct_count: int
    wrong_count: int
    no_match_count: int
    match_rate: Optional[float]
    accuracy: Optional[float]
    f1_score: Optional[float]
    avg_confidence: Optional[float]
    avg_response_time: Optional[float]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]


class TaskListResponse(BaseModel):
    """任务列表响应"""
    total: int
    tasks: List[TaskResponse]


class FailureCase(BaseModel):
    """失败案例"""
    id: int
    check_item: str
    modality: Optional[str]
    expected_code: Optional[str]
    expected_name: Optional[str]
    actual_code: Optional[str]
    actual_name: Optional[str]
    confidence: Optional[float]
    failure_reason: Optional[str]
    failure_detail: Optional[str]


class FailuresResponse(BaseModel):
    """失败案例响应"""
    total: int
    cases: List[FailureCase]


class FailureStatsResponse(BaseModel):
    """失败统计响应"""
    stats: Dict[str, int]


# ==================== API 路由 ====================

@router.post("/tasks", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest):
    """
    创建评测任务

    - 验证测试文件存在
    - 创建任务记录
    - 返回任务 ID
    """
    # 验证测试文件
    test_file = Path(request.test_file_path)
    if not test_file.exists():
        raise HTTPException(status_code=400, detail=f"测试文件不存在: {request.test_file_path}")

    if not test_file.suffix == ".csv":
        raise HTTPException(status_code=400, detail="仅支持 CSV 格式测试文件")

    # B-23修复：防止路径遍历，文件必须在项目目录内
    project_root = Path(__file__).resolve().parents[3]
    if not test_file.resolve().is_relative_to(project_root):
        raise HTTPException(status_code=400, detail="测试文件路径不在允许的目录范围内")

    # 创建任务
    session_factory = get_session_factory()
    async with session_factory() as session:
        task = EvalTask(
            name=request.name,
            description=request.description,
            test_file_path=request.test_file_path,
            sample_size=request.sample_size,
            modality=request.modality,
            status='pending',
            progress=0,
            tags=request.tags,
            created_by=request.created_by,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)

        logger.info(f"创建评测任务: {task.id} - {task.name}")

        return _task_to_response(task)


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="按状态过滤"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    获取评测任务列表

    - 支持按状态过滤
    - 支持分页
    - 按创建时间倒序
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        # 构建查询
        query = select(EvalTask)

        if status:
            query = query.where(EvalTask.status == status)

        # 查询总数
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # 查询数据
        query = query.order_by(desc(EvalTask.created_at)).limit(limit).offset(offset)
        result = await session.execute(query)
        tasks = result.scalars().all()

        return TaskListResponse(
            total=total,
            tasks=[_task_to_response(task) for task in tasks]
        )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    """
    获取评测任务详情
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        task = await session.get(EvalTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        return _task_to_response(task)


@router.post("/tasks/{task_id}/start")
async def start_evaluation(task_id: int, background_tasks: BackgroundTasks):
    """
    启动评测任务（后台异步执行）

    - 检查任务状态（必须是 pending）
    - 启动后台任务
    - 立即返回
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        task = await session.get(EvalTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        if task.status != 'pending':
            raise HTTPException(
                status_code=400,
                detail=f"任务状态不正确: {task.status}，只能启动 pending 状态的任务"
            )

        # 验证测试文件
        test_file = Path(task.test_file_path)
        if not test_file.exists():
            raise HTTPException(status_code=400, detail=f"测试文件不存在: {task.test_file_path}")

    # 启动后台任务
    runner = get_runner()
    background_tasks.add_task(
        _run_evaluation_background,
        runner,
        task_id,
        task.test_file_path,
        task.sample_size,
        task.modality,
    )

    logger.info(f"启动评测任务: {task_id}")

    return {"message": "评测任务已启动", "task_id": task_id}


@router.get("/tasks/{task_id}/failures", response_model=FailuresResponse)
async def get_failures(
    task_id: int,
    failure_reason: Optional[str] = Query(None, description="失败原因过滤"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    获取评测失败案例

    - 支持按失败原因过滤
    - 支持分页
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        # 验证任务存在
        task = await session.get(EvalTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        # 构建查询
        query = select(EvalDetail).where(
            EvalDetail.task_id == task_id,
            EvalDetail.is_correct == False,
        )

        if failure_reason:
            query = query.where(EvalDetail.failure_reason == failure_reason)

        # 查询总数
        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # 查询数据
        query = query.order_by(EvalDetail.id).limit(limit).offset(offset)
        result = await session.execute(query)
        details = result.scalars().all()

        return FailuresResponse(
            total=total,
            cases=[_detail_to_failure_case(d) for d in details]
        )


@router.get("/tasks/{task_id}/failures/stats", response_model=FailureStatsResponse)
async def get_failure_stats(task_id: int):
    """
    获取失败原因统计

    - 按失败原因分组统计
    - 用于生成优化建议
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        # 验证任务存在
        task = await session.get(EvalTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    # 获取统计
    runner = get_runner()
    stats = await runner.get_failure_stats(task_id)

    return FailureStatsResponse(stats=stats)


@router.get("/tasks/{task_id}/analysis")
async def get_task_analysis(task_id: int):
    """
    获取任务的详细分析报告

    - 各模态匹配表现
    - 高频失败项目
    - 失败案例分布
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        # 验证任务存在
        task = await session.get(EvalTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        # 按模态统计性能
        modality_stats_sql = text("""
            SELECT
                modality,
                COUNT(*) as total,
                COUNT(CASE WHEN match_status = 'matched' THEN 1 END) as matched,
                COUNT(CASE WHEN match_status = 'matched' AND actual_code = expected_code THEN 1 END) as correct,
                COUNT(CASE WHEN match_status = 'no_match' THEN 1 END) as no_match
            FROM mms_eval_details
            WHERE task_id = :task_id
            GROUP BY modality
            ORDER BY total DESC
        """)

        result = await session.execute(modality_stats_sql, {'task_id': task_id})
        modality_stats = []

        for row in result:
            total = row.total
            matched = row.matched
            correct = row.correct
            no_match = row.no_match

            match_rate = round(matched / total * 100, 2) if total > 0 else 0
            accuracy = round(correct / matched * 100, 2) if matched > 0 else 0

            modality_stats.append({
                'modality': row.modality,
                'total': total,
                'matched': matched,
                'correct': correct,
                'no_match': no_match,
                'match_rate': match_rate,
                'accuracy': accuracy,
            })

        # 高频失败项目
        freq_failures_sql = text("""
            SELECT
                check_item, modality, COUNT(*) as count
            FROM mms_eval_details
            WHERE task_id = :task_id AND match_status = 'no_match'
            GROUP BY check_item, modality
            HAVING COUNT(*) >= 2
            ORDER BY count DESC, modality
            LIMIT 50
        """)

        result = await session.execute(freq_failures_sql, {'task_id': task_id})
        freq_failures = [
            {
                'check_item': row.check_item,
                'modality': row.modality,
                'count': row.count
            }
            for row in result
        ]

        # 失败原因统计（从runner获取）
        runner = get_runner()
        failure_stats = await runner.get_failure_stats(task_id)

        return {
            'task_id': task_id,
            'modality_performance': modality_stats,
            'frequent_failures': freq_failures,
            'failure_reasons': failure_stats,
        }


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    """
    删除评测任务

    - 级联删除所有详情记录
    - 仅允许删除已完成或失败的任务
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        task = await session.get(EvalTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        if task.status == 'running':
            raise HTTPException(status_code=400, detail="不能删除运行中的任务")

        await session.delete(task)
        await session.commit()

        logger.info(f"删除评测任务: {task_id}")

        return {"message": "任务已删除", "task_id": task_id}


# ==================== 辅助函数 ====================

def _task_to_response(task: EvalTask) -> TaskResponse:
    """转换任务模型为响应对象"""
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        status=task.status,
        progress=task.progress or 0,
        total_count=task.total_count or 0,
        matched_count=task.matched_count or 0,
        correct_count=task.correct_count or 0,
        wrong_count=task.wrong_count or 0,
        no_match_count=task.no_match_count or 0,
        match_rate=float(task.match_rate) if task.match_rate else None,
        accuracy=float(task.accuracy) if task.accuracy else None,
        f1_score=float(task.f1_score) if task.f1_score else None,
        avg_confidence=float(task.avg_confidence) if task.avg_confidence else None,
        avg_response_time=float(task.avg_response_time) if task.avg_response_time else None,
        created_at=task.created_at.isoformat() if task.created_at else None,
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
    )


def _detail_to_failure_case(detail: EvalDetail) -> FailureCase:
    """转换详情模型为失败案例对象"""
    return FailureCase(
        id=detail.id,
        check_item=detail.check_item,
        modality=detail.modality,
        expected_code=detail.expected_code,
        expected_name=detail.expected_name,
        actual_code=detail.actual_code,
        actual_name=detail.actual_name,
        confidence=float(detail.confidence) if detail.confidence else None,
        failure_reason=detail.failure_reason,
        failure_detail=detail.failure_detail,
    )


async def _run_evaluation_background(
    runner: EvaluationRunner,
    task_id: int,
    test_file: str,
    sample_size: Optional[int],
    modality_filter: Optional[str],
):
    """后台执行评测任务"""
    try:
        await runner.run_evaluation(
            task_id=task_id,
            test_file=test_file,
            sample_size=sample_size,
            modality_filter=modality_filter,
        )
        logger.info(f"评测任务完成: {task_id}")
    except Exception as e:
        logger.error(f"评测任务失败: {task_id} - {e}", exc_info=True)
