import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Progress } from 'antd';
import {
  BookOutlined,
  SwapOutlined,
  ThunderboltOutlined,
  CheckSquareOutlined,
  PieChartOutlined,
  BarChartOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { adminAPI, StatsData } from '../services/matchService';

const DICT_TYPE_NAMES: Record<string, string> = {
  body: '解剖部位 (body)',
  scan: '扫描方式 (scan)',
  post: '后处理 (post)',
  position: '摆位方式 (position)',
  device: '设备类别 (device)',
  scope: '范围词 (scope)',
  mgscan: 'MG 扫描方式',
  rfscan: 'RF 扫描方式',
  other: '其他通用分词',
};

const UNMATCHED_REASON_NAMES: Record<string, { label: string; color: string }> = {
  unmatchable_by_design: { label: '设计上不可匹配', color: 'text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/40 border-slate-200 dark:border-slate-700' },
  lexicon_gap: { label: '词库映射缺失 (Lexicon Gap)', color: 'text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800' },
  standard_lib_gap: { label: '标准库缺失 (Standard Gap)', color: 'text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800' },
  unsupported_modality: { label: '暂不支持的模态', color: 'text-cyan-700 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-950/40 border-cyan-200 dark:border-cyan-800' },
  parser_ambiguity: { label: '解析歧义', color: 'text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/40 border-purple-200 dark:border-purple-800' },
  modality_route_review: { label: '模态路由待确认', color: 'text-indigo-700 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/40 border-indigo-200 dark:border-indigo-800' },
  standard_data_conflict: { label: '标准数据冲突', color: 'text-orange-700 dark:text-orange-400 bg-orange-50 dark:bg-orange-950/40 border-orange-200 dark:border-orange-800' },
  excluded_intervention: { label: '治疗性介入排除', color: 'text-pink-700 dark:text-pink-400 bg-pink-50 dark:bg-pink-950/40 border-pink-200 dark:border-pink-800' },
  excluded_non_imaging: { label: '非影像项目排除', color: 'text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/40 border-slate-200 dark:border-slate-700' },
  needs_manual: { label: '需人工审核 (Needs Manual)', color: 'text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/40 border-purple-200 dark:border-purple-800' },
  engine_error: { label: '匹配引擎异常 (Engine Exception)', color: 'text-rose-700 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800' },
};

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<StatsData | null>(null);

  useEffect(() => {
    adminAPI.getStats().then(setStats).catch(() => {});
  }, []);

  // F-04: 全部来自真实 stats 接口，不再使用硬编码假保底值
  const totalDict = stats?.total_medical_dict ?? (stats as any)?.tables?.nlp_medical_dict?.total ?? 0;
  const totalPhrase = stats?.total_phrase_map ?? (stats as any)?.tables?.nlp_phrase_map?.total ?? 0;
  const totalAmbiguity = stats?.total_ambiguity ?? (stats as any)?.tables?.nlp_ambiguity?.total ?? 0;
  const totalStandard = stats?.total_standard_items ?? (stats as any)?.tables?.nlp_checkitem_standard?.total ?? 0;
  const enabledStandard = (stats as any)?.tables?.nlp_checkitem_standard?.enabled ?? 0;

  const topCards = [
    {
      title: '医学分词词典',
      value: totalDict,
      icon: <BookOutlined className="text-xl text-blue-600 dark:text-blue-400" />,
      desc: '支持部位、扫描、后处理精细分词',
      bgIcon: <BookOutlined className="absolute -right-4 -bottom-4 text-7xl text-blue-500/5 pointer-events-none" />,
    },
    {
      title: '短语归一化映射',
      value: totalPhrase,
      icon: <SwapOutlined className="text-xl text-emerald-600 dark:text-emerald-400" />,
      desc: '临床别名与异名自动转换映射',
      bgIcon: <SwapOutlined className="absolute -right-4 -bottom-4 text-7xl text-emerald-500/5 pointer-events-none" />,
    },
    {
      title: '消歧与补充规则',
      value: totalAmbiguity,
      icon: <ThunderboltOutlined className="text-xl text-amber-600 dark:text-amber-400" />,
      desc: '消除上下文歧义并补齐默认处理',
      bgIcon: <ThunderboltOutlined className="absolute -right-4 -bottom-4 text-7xl text-amber-500/5 pointer-events-none" />,
    },
    {
      title: '标准检查项目库',
      value: totalStandard,
      icon: <CheckSquareOutlined className="text-xl text-purple-600 dark:text-purple-400" />,
      desc: '包含 CT/MR/US 等全模态标准典卡',
      bgIcon: <CheckSquareOutlined className="absolute -right-4 -bottom-4 text-7xl text-purple-500/5 pointer-events-none" />,
    },
  ];

  // 模态分布兼容
  let modalityMap: Record<string, number> = {};
  if (Array.isArray(stats?.modality_distribution)) {
    (stats.modality_distribution as any[]).forEach(item => {
      if (item.modality) modalityMap[item.modality] = item.count;
    });
  } else if (stats?.modality_distribution && typeof stats.modality_distribution === 'object') {
    modalityMap = stats.modality_distribution as Record<string, number>;
  }
  const totalStandardCount = Object.values(modalityMap).reduce((a, b) => a + b, 0);

  // 词典分类
  let dictMap: Record<string, number> = {};
  if (stats?.dict_type_distribution && typeof stats.dict_type_distribution === 'object') {
    dictMap = stats.dict_type_distribution;
  }
  const totalDictCount = Object.values(dictMap).reduce((a, b) => a + b, 0);

  // 未匹配分类
  let unmatchedMap: Record<string, number> = {};
  if (stats?.unmatched_distribution && typeof stats.unmatched_distribution === 'object') {
    unmatchedMap = stats.unmatched_distribution;
  }
  const totalUnmatchedCount = Object.values(unmatchedMap).reduce((a, b) => a + b, 0);

  const isDark = document.documentElement.classList.contains('dark');

  return (
    <div className="space-y-6">
      {/* 头部标题与版本快照 */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b pb-4 gap-3 border-border-theme">
        <div>
          <h2 className="text-xl font-bold tracking-tight flex items-center gap-2 m-0 text-text-primary">
            <PieChartOutlined className="text-brand-color" />
            标准化匹配服务全面数据分析
          </h2>
          <p className="text-xs mt-1 m-0 text-text-secondary">跨版本规则库对比、模态标准分布占比与治理覆盖率评估</p>
        </div>
        <div className="flex items-center gap-2.5 shrink-0">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
            规则版本: {stats?.rule_version || '加载中…'}
          </span>
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/50">
            <CheckCircleOutlined className="text-emerald-500" /> 引擎状态: 最佳
          </span>
        </div>
      </div>

      {/* 4 大核心 KPI 统计卡片 */}
      <Row gutter={[16, 16]}>
        {topCards.map((card, idx) => (
          <Col xs={24} sm={12} lg={6} key={idx}>
            <Card
              bordered={false}
              className="relative overflow-hidden group hover:border-brand-color transition-all duration-200 bg-bg-card border-border-theme shadow-xs rounded-xl"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-text-secondary">{card.title}</span>
                <div className="w-8 h-8 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform bg-bg-subtle">
                  {card.icon}
                </div>
              </div>
              <Statistic
                value={card.value}
                valueStyle={{ color: 'var(--text-primary)', fontSize: '28px', fontWeight: 800, letterSpacing: '-0.02em' }}
              />
              <div className="text-[11px] mt-2 font-normal text-text-secondary">{card.desc}</div>
              {card.bgIcon}
            </Card>
          </Col>
        ))}
      </Row>

      {/* 深度分析第一排：模态分布 + 词典类型分类 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 不同模态标准分布比重分析 */}
        <div className="lg:col-span-7">
          <Card
            bordered={false}
            className="shadow-xs rounded-xl h-full flex flex-col justify-between bg-bg-card border-border-theme"
            title={
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold flex items-center gap-2 text-text-primary">
                  <PieChartOutlined className="text-brand-color" />
                  不同检查模态的标准分布与占比 (Modality Analysis)
                </span>
                <span className="text-xs font-normal text-text-secondary">共 {totalStandardCount} 项标准</span>
              </div>
            }
          >
            <div className="space-y-3.5 py-1">
              {Object.keys(modalityMap).length === 0 && (
                <div className="text-center py-10 text-xs text-text-secondary">暂无模态分布数据</div>
              )}
              {Object.entries(modalityMap)
                .sort(([, a], [, b]) => b - a)
                .map(([mod, count]) => {
                  const percent = totalStandardCount > 0 ? Math.round((count / totalStandardCount) * 100) : 0;
                  return (
                    <div key={mod} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold w-16 text-text-primary">{mod}</span>
                        <div className="flex items-center gap-3">
                          <span className="font-medium text-text-secondary">{count} 条目</span>
                          <span className="font-mono font-bold w-10 text-right text-brand-color">{percent}%</span>
                        </div>
                      </div>
                      <Progress
                        percent={percent}
                        showInfo={false}
                        strokeColor={{ '0%': '#3b82f6', '100%': '#1e40af' }}
                        trailColor={isDark ? '#27272a' : '#e2e8f0'}
                        size="small"
                      />
                    </div>
                  );
                })}
            </div>
          </Card>
        </div>

        {/* 医学分词分类比重图谱 */}
        <div className="lg:col-span-5">
          <Card
            bordered={false}
            className="shadow-xs rounded-xl h-full bg-bg-card border-border-theme"
            title={
              <span className="text-sm font-bold flex items-center gap-2 text-text-primary">
                <BarChartOutlined className="text-brand-color" />
                词典词条分类结构图谱 (Lexicon Breakdown)
              </span>
            }
          >
            <div className="space-y-4">
              {Object.keys(dictMap).length === 0 && (
                <div className="text-center py-10 text-xs text-text-secondary">暂无词典分类数据</div>
              )}
              {Object.entries(dictMap).map(([typeKey, count]) => {
                const labelName = DICT_TYPE_NAMES[typeKey] || typeKey;
                const percent = totalDictCount > 0 ? Math.round((count / totalDictCount) * 100) : 0;
                return (
                  <div key={typeKey} className="p-3 rounded-xl flex items-center justify-between bg-bg-subtle border border-border-theme">
                    <div>
                      <div className="text-xs font-semibold text-text-primary">{labelName}</div>
                      <div className="text-[11px] mt-0.5 text-text-secondary">词条数: {count}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-base font-extrabold font-mono text-brand-color">{percent}%</div>
                      <div className="text-[10px] text-text-secondary">词库占比</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      </div>

      {/* 深度分析第二排：未匹配诊断分类 */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* 未匹配问题与质量健康度 */}
        <div className="md:col-span-6">
          <Card
            bordered={false}
            className="shadow-xs rounded-xl h-full bg-bg-card border-border-theme"
            title={
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold flex items-center gap-2 text-text-primary">
                  <ExclamationCircleOutlined className="text-amber-500" />
                  未匹配诊断原因分类与质量洞察
                </span>
                <a href="/unmatched" className="text-xs hover:underline font-semibold text-brand-color">
                  去工作台处理 →
                </a>
              </div>
            }
          >
            <div className="space-y-3">
              {Object.keys(unmatchedMap).length === 0 && (
                <div className="text-center py-10 text-xs text-text-secondary">暂无未匹配工单数据</div>
              )}
              {Object.entries(unmatchedMap).map(([code, count]) => {
                const meta = UNMATCHED_REASON_NAMES[code] || { label: code, color: 'text-slate-700 bg-slate-50 border-slate-200' };
                const percent = totalUnmatchedCount > 0 ? Math.round((count / totalUnmatchedCount) * 100) : 0;
                return (
                  <div key={code} className={`p-3.5 rounded-xl border flex items-center justify-between ${meta.color}`}>
                    <div>
                      <span className="text-xs font-bold block">{meta.label}</span>
                      <span className="text-[11px] opacity-80 mt-0.5 block">待优化工单: {count} 件</span>
                    </div>
                    <div className="text-right">
                      <span className="text-sm font-extrabold font-mono block">{percent}%</span>
                      <span className="text-[10px] opacity-70">问题比重</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        {/* 规则引擎快照与性能 */}
        <div className="md:col-span-6">
          <Card
            bordered={false}
            className="shadow-xs rounded-xl h-full bg-bg-card border-border-theme"
            title={
              <span className="text-sm font-bold flex items-center gap-2 text-text-primary">
                <CheckCircleOutlined className="text-emerald-500" />
                规则引擎版本数据与治理摘要
              </span>
            }
          >
            <div className="space-y-4">
              <div className="p-4 rounded-xl space-y-2 bg-bg-subtle border border-border-theme">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-text-secondary">当前线上规则引擎版本</span>
                  <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400">RELEASED</span>
                </div>
                <div className="text-base font-extrabold font-mono tracking-tight text-brand-color">
                  {stats?.rule_version || '加载中…'}
                </div>
                <p className="text-[11px] m-0 text-text-secondary">
                  包含国家标准项目字典库、完整 Jieba 医学分词词典及异名消歧映射表，支持全模态实时诊断。
                </p>
              </div>

              {/* F-04: 以真实统计数据替换原硬编码性能指标 */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl bg-bg-subtle border border-border-theme">
                  <div className="text-[10px] text-text-secondary">标准库生效条目</div>
                  <div className="text-sm font-bold font-mono mt-0.5 text-emerald-600 dark:text-emerald-400">{enabledStandard.toLocaleString()} 条</div>
                </div>
                <div className="p-3 rounded-xl bg-bg-subtle border border-border-theme">
                  <div className="text-[10px] text-text-secondary">待处理未匹配工单</div>
                  <div className="text-sm font-bold font-mono mt-0.5 text-brand-color">{totalUnmatchedCount} 件</div>
                </div>
              </div>

              <div className="text-center pt-1">
                <a href="/match" className="text-xs font-bold hover:underline inline-flex items-center gap-1 text-brand-color">
                  运行单项匹配算法测试 →
                </a>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
