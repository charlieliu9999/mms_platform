"""
评测执行器 - 批量测试匹配引擎性能

基于 scripts/quick_match_test.py 改造，增强功能：
- 异步执行，支持进度回调
- 数据库持久化（保存到 mms_eval_tasks 和 mms_eval_details）
- 自动失败原因分类
- 完整指标计算（match_rate, accuracy, precision, recall, F1）
"""

import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, Callable, Dict, List, Any

import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.engine_holder import EngineHolder
from ..db import get_session_factory
from ..models.evaluation import EvalTask, EvalDetail

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """评测执行器"""

    def __init__(self):
        self.engine_holder: Optional[EngineHolder] = None

    async def initialize(self):
        """初始化匹配引擎"""
        if self.engine_holder is None:
            self.engine_holder = EngineHolder()
            await self.engine_holder.initialize()
            logger.info("评测引擎初始化完成")

    async def run_evaluation(
        self,
        task_id: int,
        test_file: str,
        sample_size: Optional[int] = None,
        modality_filter: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, Dict], None]] = None,
    ) -> Dict[str, Any]:
        """
        执行评测任务

        Args:
            task_id: 评测任务 ID
            test_file: 测试数据文件路径（CSV）
            sample_size: 采样数量，None=全部
            modality_filter: 模态过滤，None=全部
            progress_callback: 进度回调函数 (current, total, metrics)

        Returns:
            评测结果摘要
        """
        # 确保引擎已初始化
        if self.engine_holder is None:
            await self.initialize()

        session_factory = get_session_factory()

        async with session_factory() as session:
            # 1. 更新任务状态为 running
            task = await session.get(EvalTask, task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            task.status = 'running'
            task.progress = 0
            task.started_at = datetime.utcnow()
            await session.commit()

            try:
                # 2. 读取测试数据
                logger.info(f"读取测试文件: {test_file}")
                df = pd.read_csv(test_file)

                # 模态过滤
                if modality_filter:
                    df = df[df['modality'] == modality_filter]
                    logger.info(f"模态过滤 ({modality_filter}): {len(df)} 条")

                # 随机采样
                if sample_size and len(df) > sample_size:
                    df_sample = df.sample(n=sample_size, random_state=42)
                    logger.info(f"随机采样: {sample_size}/{len(df)} 条")
                else:
                    df_sample = df
                    logger.info(f"使用全部数据: {len(df)} 条")

                total_count = len(df_sample)
                task.total_count = total_count
                await session.commit()

                # 3. 执行匹配测试
                orchestrator = self.engine_holder._match_engine
                results = {
                    'total': 0,
                    'matched': 0,
                    'correct': 0,
                    'wrong': 0,
                    'no_match': 0,
                    'total_confidence': 0.0,
                    'total_response_time': 0.0,
                }

                start_time = datetime.now()

                for idx, row in df_sample.iterrows():
                    results['total'] += 1

                    # 提取数据
                    check_item = row.get('check_item', '')
                    modality = row.get('modality', '')
                    expected_code = str(row.get('expected_standard_code', '')).strip()
                    if expected_code.endswith('.0'):
                        expected_code = expected_code[:-2]
                    expected_name = row.get('expected_standard_name', '')

                    if not check_item:
                        results['no_match'] += 1
                        await self._save_detail(
                            session, task_id, check_item, modality,
                            expected_code, expected_name,
                            None, None, 0.0, 0.0,
                            False, False, 'none', 'empty_input', '输入为空'
                        )
                        continue

                    # 执行匹配
                    try:
                        match_start = datetime.now()
                        match_result = orchestrator.match(check_item, modality)
                        response_time = (datetime.now() - match_start).total_seconds() * 1000

                        results['total_response_time'] += response_time

                        # 解析结果
                        if match_result and match_result.get('num_standard', 0) > 0 and match_result.get('data'):
                            results['matched'] += 1
                            candidates = match_result['data']
                            best = candidates[0]
                            standard_items = best.get('standard', [])

                            if standard_items:
                                standard = standard_items[0]
                                actual_code = str(standard.get('code', '')).strip()
                                actual_name = standard.get('name', '')
                                confidence = match_result.get('score', 0.0)

                                results['total_confidence'] += confidence

                                # 判断正确性
                                # 改进逻辑：在所有候选结果中查找期望项（不限于第一个）
                                is_correct = False
                                actual_code_used = actual_code
                                actual_name_used = actual_name

                                # 方案1：检查所有候选结果中是否有匹配的
                                for candidate in match_result['data']:
                                    for std_item in candidate.get('standard', []):
                                        std_name = std_item.get('name', '')
                                        if std_name == expected_name:
                                            is_correct = True
                                            actual_code_used = str(std_item.get('code', '')).strip()
                                            actual_name_used = std_name
                                            break
                                    if is_correct:
                                        break

                                match_type = 'exact' if is_correct else 'wrong'

                                if is_correct:
                                    results['correct'] += 1
                                else:
                                    results['wrong'] += 1

                                # 保存详情
                                await self._save_detail(
                                    session, task_id, check_item, modality,
                                    expected_code, expected_name,
                                    actual_code_used, actual_name_used, confidence, response_time,
                                    True, is_correct, match_type,
                                    None if is_correct else 'wrong_match',
                                    None if is_correct else f'期望: {expected_name}, 实际: {actual_name_used}'
                                )
                            else:
                                # 匹配但无标准项
                                results['no_match'] += 1
                                await self._save_detail(
                                    session, task_id, check_item, modality,
                                    expected_code, expected_name,
                                    None, None, 0.0, response_time,
                                    False, False, 'none', 'no_standard',
                                    '匹配成功但无标准项目数据'
                                )
                        else:
                            # 未匹配
                            results['no_match'] += 1
                            failure_reason = self._classify_failure(check_item, modality)
                            await self._save_detail(
                                session, task_id, check_item, modality,
                                expected_code, expected_name,
                                None, None, 0.0, response_time,
                                False, False, 'none', failure_reason,
                                f'未匹配到标准项目: {check_item}'
                            )

                    except Exception as e:
                        logger.error(f"匹配异常: {check_item[:50]}... - {e}", exc_info=True)
                        results['no_match'] += 1
                        await self._save_detail(
                            session, task_id, check_item, modality,
                            expected_code, expected_name,
                            None, None, 0.0, 0.0,
                            False, False, 'none', 'algorithm',
                            f'算法异常: {str(e)[:200]}'
                        )

                    # 更新进度（每 10 条或最后一条）
                    if results['total'] % 10 == 0 or results['total'] == total_count:
                        progress = int(results['total'] / total_count * 100)
                        task.progress = progress
                        task.matched_count = results['matched']
                        task.correct_count = results['correct']
                        task.wrong_count = results['wrong']
                        task.no_match_count = results['no_match']
                        await session.commit()

                        # 进度回调
                        if progress_callback:
                            progress_callback(results['total'], total_count, {
                                'matched': results['matched'],
                                'correct': results['correct'],
                                'match_rate': results['matched'] / results['total'] * 100,
                            })

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                # 4. 计算指标
                metrics = self._calculate_metrics(results, duration)

                # 5. 更新任务
                task.status = 'completed'
                task.progress = 100
                task.completed_at = datetime.utcnow()

                task.total_count = results['total']
                task.matched_count = results['matched']
                task.correct_count = results['correct']
                task.wrong_count = results['wrong']
                task.no_match_count = results['no_match']

                task.match_rate = Decimal(str(metrics['match_rate']))
                task.accuracy = Decimal(str(metrics['accuracy']))
                task.precision_score = Decimal(str(metrics['precision']))
                task.recall_score = Decimal(str(metrics['recall']))
                task.f1_score = Decimal(str(metrics['f1']))
                task.avg_confidence = Decimal(str(metrics['avg_confidence']))
                task.avg_response_time = Decimal(str(metrics['avg_response_time']))

                await session.commit()

                logger.info(f"评测完成: Task {task_id}, 匹配率 {metrics['match_rate']:.2f}%, 准确率 {metrics['accuracy']:.2f}%")

                return {
                    'task_id': task_id,
                    'status': 'completed',
                    'duration': duration,
                    'metrics': metrics,
                }

            except Exception as e:
                logger.error(f"评测失败: Task {task_id} - {e}", exc_info=True)
                task.status = 'failed'
                task.progress = 0
                await session.commit()
                raise

    async def _save_detail(
        self,
        session: AsyncSession,
        task_id: int,
        check_item: str,
        modality: str,
        expected_code: str,
        expected_name: str,
        actual_code: Optional[str],
        actual_name: Optional[str],
        confidence: float,
        response_time: float,
        is_matched: bool,
        is_correct: bool,
        match_type: str,
        failure_reason: Optional[str],
        failure_detail: Optional[str],
    ):
        """保存评测详情"""
        detail = EvalDetail(
            task_id=task_id,
            check_item=check_item,
            modality=modality,
            expected_code=expected_code,
            expected_name=expected_name,
            actual_code=actual_code,
            actual_name=actual_name,
            confidence=Decimal(str(confidence)) if confidence else None,
            response_time=Decimal(str(response_time)) if response_time else None,
            is_matched=is_matched,
            is_correct=is_correct,
            match_type=match_type,
            failure_reason=failure_reason,
            failure_detail=failure_detail,
        )
        session.add(detail)

    def _calculate_metrics(self, results: Dict, duration: float) -> Dict[str, float]:
        """计算评测指标"""
        total = results['total']
        matched = results['matched']
        correct = results['correct']
        wrong = results['wrong']
        no_match = results['no_match']

        match_rate = matched / total * 100 if total > 0 else 0
        accuracy = correct / matched * 100 if matched > 0 else 0
        avg_confidence = results['total_confidence'] / matched if matched > 0 else 0
        avg_response_time = results['total_response_time'] / total if total > 0 else 0

        # Precision: TP / (TP + FP) - 正确匹配 / 所有匹配
        precision = correct / matched * 100 if matched > 0 else 0

        # Recall: TP / (TP + FN) - 正确匹配 / 应该匹配的
        # 假设所有测试数据都应该有匹配结果
        recall = correct / total * 100 if total > 0 else 0

        # F1: 2 * (precision * recall) / (precision + recall)
        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0

        return {
            'match_rate': round(match_rate, 2),
            'accuracy': round(accuracy, 2),
            'precision': round(precision, 2),
            'recall': round(recall, 2),
            'f1': round(f1, 2),
            'avg_confidence': round(avg_confidence, 3),
            'avg_response_time': round(avg_response_time, 2),
            'total_duration': round(duration, 2),
        }

    def _classify_failure(self, check_item: str, modality: str) -> str:
        """
        自动分类失败原因

        返回值:
        - missing_word: 缺少医学词汇
        - ambiguity: 存在歧义
        - complex: 复杂表述
        - algorithm: 算法问题
        """
        # 简单启发式规则
        if len(check_item) > 100:
            return 'complex'  # 超长表述，可能是复合项目

        if '(' in check_item and check_item.count('(') > 3:
            return 'complex'  # 多层括号，复杂结构

        if ',' in check_item or '、' in check_item:
            return 'complex'  # 包含多个子项目

        # 默认归类为缺少词汇
        return 'missing_word'

    async def get_task_summary(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取任务摘要"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            task = await session.get(EvalTask, task_id)
            if not task:
                return None

            return {
                'id': task.id,
                'name': task.name,
                'status': task.status,
                'progress': task.progress,
                'total_count': task.total_count,
                'matched_count': task.matched_count,
                'correct_count': task.correct_count,
                'match_rate': float(task.match_rate) if task.match_rate else None,
                'accuracy': float(task.accuracy) if task.accuracy else None,
                'f1_score': float(task.f1_score) if task.f1_score else None,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            }

    async def get_failure_cases(
        self,
        task_id: int,
        failure_reason: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """获取失败案例"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            query = select(EvalDetail).where(
                EvalDetail.task_id == task_id,
                EvalDetail.is_correct == False,
            )

            if failure_reason:
                query = query.where(EvalDetail.failure_reason == failure_reason)

            query = query.order_by(EvalDetail.id).limit(limit).offset(offset)

            result = await session.execute(query)
            details = result.scalars().all()

            return [
                {
                    'id': d.id,
                    'check_item': d.check_item,
                    'modality': d.modality,
                    'expected_code': d.expected_code,
                    'expected_name': d.expected_name,
                    'actual_code': d.actual_code,
                    'actual_name': d.actual_name,
                    'confidence': float(d.confidence) if d.confidence else None,
                    'failure_reason': d.failure_reason,
                    'failure_detail': d.failure_detail,
                }
                for d in details
            ]

    async def get_failure_stats(self, task_id: int) -> Dict[str, int]:
        """获取失败原因统计"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            query = select(
                EvalDetail.failure_reason,
                func.count(EvalDetail.id).label('count')
            ).where(
                EvalDetail.task_id == task_id,
                EvalDetail.is_correct == False,
            ).group_by(EvalDetail.failure_reason)

            result = await session.execute(query)
            rows = result.all()

            return {row.failure_reason: row.count for row in rows if row.failure_reason}
