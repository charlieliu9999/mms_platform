import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Card, Input, Select, Button, Tag, Progress, Table, Tabs, message,
  Spin, Empty, Segmented, Tooltip, Row, Col, Switch,
} from 'antd';
import {
  SearchOutlined, CheckCircleFilled, ExclamationCircleOutlined, ThunderboltOutlined,
  ExperimentOutlined, PlayCircleOutlined, ReloadOutlined, DatabaseOutlined, AimOutlined,
} from '@ant-design/icons';
import {
  matchAPI, adminAPI, MatchResult, ProcedureItem, ProcedureMatchResult,
} from '../services/matchService';


// ─── 常量 ────────────────────────────────────────────────────────────────
const MODALITY_OPTIONS = ['CT', 'MR', 'US', 'DR', 'RF', 'MG', 'SPECT', 'DSA', 'PET/CT', 'PET/MR', 'OCT'];

const TIER_COLORS: Record<string, string> = {
  exact: 'green', partial: 'blue', degraded: 'orange', ambiguous: 'gold', none: 'red', error: 'red',
};

const REASON_META: Record<string, { label: string; color: string }> = {
  unmatchable_by_design: { label: '设计上不可匹配', color: 'default' },
  standard_lib_gap: { label: '标准库缺失', color: 'orange' },
  lexicon_gap: { label: '词库映射缺失', color: 'blue' },
  needs_manual: { label: '需人工审核', color: 'purple' },
  engine_error: { label: '引擎异常', color: 'red' },
  unsupported_modality: { label: '暂不支持的模态', color: 'cyan' },
  parser_ambiguity: { label: '解析歧义', color: 'purple' },
  modality_route_review: { label: '模态路由待确认', color: 'geekblue' },
  standard_data_conflict: { label: '标准数据冲突', color: 'volcano' },
  excluded_intervention: { label: '治疗性介入排除', color: 'magenta' },
  excluded_non_imaging: { label: '非影像项目排除', color: 'default' },
};

type ItemStatus = 'matched' | 'unmatched' | 'wontfix' | 'unknown';

const STATUS_META: Record<ItemStatus, { label: string; color: string }> = {
  matched: { label: '已匹配', color: 'green' },
  unmatched: { label: '未匹配', color: 'red' },
  wontfix: { label: '已忽略', color: 'default' },
  unknown: { label: '未检测', color: 'default' },
};

const CHUNK_SIZE = 200;

// ─── 子组件：自定义单项测试（自由文本匹配） ─────────────────────────────
const PRESET_TEST_CASES = [
  { label: 'CT头部平扫', text: 'CT头部平扫', modality: 'CT' },
  { label: 'CT头部平扫+增强', text: 'CT头部平扫+增强', modality: 'CT' },
  { label: '膝关节正侧位', text: '膝关节正、侧位', modality: 'DR' },
  { label: '胸部平扫', text: 'CT胸部高分辨率平扫', modality: 'CT' },
  { label: '头部MRA', text: 'MR头颅MRA血管造影', modality: 'MR' },
  { label: '超声心动', text: '彩色多普勒超声心动图', modality: 'US' },
];

const SingleMatchPanel: React.FC = () => {
  const [rawText, setRawText] = useState<string>('CT头部平扫+增强');
  const [modality, setModality] = useState<string>('CT');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<MatchResult | null>(null);

  const handleMatch = async () => {
    if (!rawText.trim()) return;
    setLoading(true);
    try {
      const res = await matchAPI.matchOne({ name: rawText.trim(), modality });
      setResult(res);
    } catch {
      message.error('匹配请求失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
        <div className="space-y-4">
          <div className="flex items-center gap-2 flex-wrap select-none">
            <span className="text-xs font-semibold text-text-secondary">快速预设测试用例:</span>
            {PRESET_TEST_CASES.map((tc, idx) => (
              <button
                key={idx}
                onClick={() => { setRawText(tc.text); setModality(tc.modality); }}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors border cursor-pointer bg-bg-subtle border-border-theme text-text-primary hover:bg-brand-color/10 hover:text-brand-color"
              >
                {tc.label}
              </button>
            ))}
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <Select value={modality} onChange={setModality} className="w-full sm:w-36 text-xs h-10" size="large">
              {MODALITY_OPTIONS.map((m) => <Select.Option key={m} value={m}>{m} 检查</Select.Option>)}
            </Select>
            <Input
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="输入原始检查描述文本（如: CT头部平扫+增强）..."
              onPressEnter={handleMatch}
              size="large"
              className="flex-1 text-sm rounded-lg"
            />
            <Button type="primary" size="large" icon={<SearchOutlined />} onClick={handleMatch} loading={loading} className="px-6 font-bold shadow-xs h-10">
              运行单项算法匹配
            </Button>
          </div>
        </div>
      </Card>

      {loading ? (
        <Card bordered={false} className="shadow-xs rounded-xl py-16 text-center bg-bg-card border-border-theme">
          <Spin size="large" />
          <p className="text-xs mt-4 m-0 text-text-secondary">正在调用算法引擎计算匹配路径与信心度...</p>
        </Card>
      ) : result ? (
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card bordered={false} className="shadow-xs rounded-xl text-center h-full flex flex-col justify-center bg-bg-card border-border-theme">
              <div className="text-xs font-semibold mb-2 text-text-secondary">匹配信心度得分</div>
              <div className="my-2">
                <Progress
                  type="dashboard"
                  percent={Math.round((result.confidence ?? ((result as any).score ? (result as any).score / 10 : 0)) * 100)}
                  format={() => (
                    <span className="text-2xl font-extrabold font-mono text-brand-color">
                      {Math.round((result.confidence ?? ((result as any).score ? (result as any).score / 10 : 0)) * 100)}
                    </span>
                  )}
                  strokeColor={{ '0%': '#3b82f6', '100%': '#10b981' }}
                />
              </div>
              <div className="text-xs font-bold">
                {(result as any).num_standard > 0 ? (
                  <span className="text-emerald-600 flex items-center justify-center gap-1"><CheckCircleFilled /> 匹配精准命中</span>
                ) : (
                  <span className="text-amber-600 flex items-center justify-center gap-1"><ExclamationCircleOutlined /> 未在标准库中直接命中</span>
                )}
              </div>
            </Card>
          </Col>
          <Col xs={24} md={16}>
            <Card
              bordered={false}
              className="shadow-xs rounded-xl h-full bg-bg-card border-border-theme"
              title={<span className="text-sm font-bold flex items-center gap-2 text-text-primary"><ThunderboltOutlined className="text-brand-color" />算法命中标准检查项目</span>}
            >
              {(() => {
                const dataItems: any[] = Array.isArray((result as any).data) ? (result as any).data : [];
                const candidates: Array<{ code?: string; name?: string; raw?: string; modality?: string }> = [];
                dataItems.forEach((item) => {
                  if (Array.isArray(item?.standard) && item.standard.length > 0) {
                    item.standard.forEach((std: any) => candidates.push({ code: std.code, name: std.name, raw: item.raw, modality: item.modality }));
                  } else if (item?.item_code || item?.item_name) {
                    candidates.push({ code: item.item_code, name: item.item_name, raw: item.raw, modality: item.modality });
                  }
                });
                const showRaw = dataItems.length > 1;
                return candidates.length > 0 ? (
                  <div className="space-y-3">
                    {candidates.map((c, idx) => (
                      <div key={`${c.code || 'hit'}-${idx}`} className="p-3.5 rounded-xl flex items-center justify-between bg-bg-subtle border border-border-theme">
                        <div>
                          <div className="text-xs font-mono font-bold text-brand-color">{c.code || 'STD-ITEM'}</div>
                          <div className="text-sm font-extrabold mt-0.5 text-text-primary">{c.name}</div>
                          {showRaw && c.raw && <div className="text-xs mt-0.5 text-text-secondary">子项：{c.raw}</div>}
                        </div>
                        <Tag color="emerald" className="font-bold px-2 py-0.5 m-0 text-xs">{c.modality || modality}</Tag>
                      </div>
                    ))}
                  </div>
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无命中标准项目" />
                );
              })()}
            </Card>
          </Col>
        </Row>
      ) : (
        <Card bordered={false} className="shadow-xs rounded-xl py-16 text-center bg-bg-card border-border-theme">
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="点击“运行单项算法匹配”查看匹配过程" />
        </Card>
      )}
    </div>
  );
};

// ─── 主组件：匹配测试中心 ───────────────────────────────────────────────
interface MatchTestProps {
  /** 初始页签：items / custom / unmatched（用于 /unmatched 路由直达未匹配分析） */
  initialTab?: string;
}

const MatchTest: React.FC<MatchTestProps> = ({ initialTab = 'items' }) => {
  const [activeTab, setActiveTab] = useState<string>(initialTab);

  const [items, setItems] = useState<ProcedureItem[]>([]);
  const [modalityStats, setModalityStats] = useState<Record<string, {
    total: number; matched: number; unmatched: number; untested: number;
  }>>({});
  const [itemsLoading, setItemsLoading] = useState(false);
  const [clearCacheBeforeRun, setClearCacheBeforeRun] = useState(true);

  const [modalityFilter, setModalityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'all' | ItemStatus>('all');
  const [searchText, setSearchText] = useState('');

  const [matchResults, setMatchResults] = useState<Record<number, ProcedureMatchResult>>({});

  const [batchRunning, setBatchRunning] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ done: 0, total: 0 });

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);


  const loadItems = useCallback(async () => {
    setItemsLoading(true);
    try {
      const res = await adminAPI.getProcedureItems();
      setItems(res.items || []);
      setModalityStats(res.modality_stats || {});
      setClearCacheBeforeRun(res.match_config?.clear_cache_before_run ?? true);
    } catch {
      message.error('加载检查项目失败');
    } finally {
      setItemsLoading(false);
    }
  }, []);

  useEffect(() => { loadItems(); }, [loadItems]);

  const getStatus = useCallback((item: ProcedureItem): ItemStatus => {
    const r = matchResults[item.id];
    if (r) return r.matched ? 'matched' : 'unmatched';
    if (item.last_matched === true) return 'matched';
    if (item.last_matched === false) return 'unmatched';
    if (item.um_status === 'open') return 'unmatched';
    if (item.um_status === 'resolved') return 'matched';
    if (item.um_status === 'wontfix') return 'wontfix';
    return 'unknown';
  }, [matchResults]);

  const filtered = useMemo(() => {
    const kw = searchText.trim().toLowerCase();
    return items.filter((it) => {
      if (modalityFilter && it.modality !== modalityFilter) return false;
      if (kw && !it.name_zh.toLowerCase().includes(kw) && !it.semantic_id.toLowerCase().includes(kw)) return false;
      if (statusFilter !== 'all' && getStatus(it) !== statusFilter) return false;
      return true;
    });
  }, [items, modalityFilter, searchText, statusFilter, getStatus]);

  const filteredMatched = useMemo(() => filtered.filter((it) => getStatus(it) === 'matched').length, [filtered, getStatus]);
  const filteredUnmatched = useMemo(() => filtered.filter((it) => getStatus(it) === 'unmatched').length, [filtered, getStatus]);
  const matchRate = filtered.length ? Math.round((filteredMatched / filtered.length) * 100) : 0;

  const reasonDist = useMemo(() => {
    const dist: Record<string, number> = {};
    Object.values(matchResults).forEach((r) => {
      if (!r.matched && r.reason_code) dist[r.reason_code] = (dist[r.reason_code] || 0) + 1;
    });
    return dist;
  }, [matchResults]);

  const matchSingle = async (id: number) => {
    try {
      const res = await adminAPI.matchProcedures([id]);
      const r = res.results?.[0];
      if (r) {
        setMatchResults((prev) => ({ ...prev, [r.procedure_id]: r }));
      }
    } catch {
      message.error('匹配失败');
    }
  };

  const runBatch = async (ids: number[]) => {
    if (!ids.length) { message.info('没有可匹配的项目'); return; }
    setBatchRunning(true);
    setBatchProgress({ done: 0, total: ids.length });
    let matched = 0, unmatched = 0;
    try {
      if (clearCacheBeforeRun) {
        const cleared = await adminAPI.clearMatchCache();
        message.info(`已失效 ${cleared.count ?? 0} 条 L1 缓存，本轮使用当前规则重新计算`);
      }
      for (let i = 0; i < ids.length; i += CHUNK_SIZE) {
        const chunk = ids.slice(i, i + CHUNK_SIZE);
        const res = await adminAPI.matchProcedures(chunk);
        const update: Record<number, ProcedureMatchResult> = {};
        (res.results || []).forEach((r) => { update[r.procedure_id] = r; });
        setMatchResults((prev) => ({ ...prev, ...update }));
        matched += res.matched_count || 0;
        unmatched += res.unmatched_count || 0;
        setBatchProgress({ done: Math.min(i + CHUNK_SIZE, ids.length), total: ids.length });
      }
      message.success(`匹配完成：命中 ${matched} 项，未匹配 ${unmatched} 项`);
      await loadItems();
    } catch {
      message.error('批量匹配中断，已保留已完成部分');
    } finally {
      setBatchRunning(false);
    }
  };

  const matchAllFiltered = () => runBatch(filtered.map((it) => it.id));
  const matchAllUnmatched = () => runBatch(filtered.filter((it) => getStatus(it) === 'unmatched').map((it) => it.id));

  const modalityOptions = useMemo(() => {
    const opts = Object.entries(modalityStats)
      .sort((a, b) => b[1].total - a[1].total)
      .map(([m, s]) => ({ label: `${m} (${s.total})`, value: m }));
    return [{ label: `全部 (${items.length})`, value: '' }, ...opts];
  }, [modalityStats, items.length]);

  const columns: any[] = [
    {
      title: '源项目', dataIndex: 'name_zh', key: 'name', ellipsis: true,
      render: (t: string, r: ProcedureItem) => (
        <div>
          <div className="font-medium text-text-primary">{t}</div>
          <div className="text-[11px] font-mono text-text-secondary">{r.semantic_id}</div>
        </div>
      ),
    },
    {
      title: '模态', dataIndex: 'modality', key: 'modality', width: 120,
      render: (m: string, r: ProcedureItem) => {
        const effective = matchResults[r.id]?.effective_modality || r.last_effective_modality;
        return (
          <div className="inline-flex items-center gap-1">
            <Tag className="m-0">{m}</Tag>
            {effective && effective !== m && (
              <span className="text-[11px] font-semibold text-brand-color">→ {effective}</span>
            )}
          </div>
        );
      },
    },
    {
      title: '状态', key: 'status', width: 90,
      render: (_: any, r: ProcedureItem) => {
        const s = getStatus(r);
        return <Tag color={STATUS_META[s].color} className="m-0">{STATUS_META[s].label}</Tag>;
      },
    },
    {
      title: 'Tier', key: 'tier', width: 90,
      render: (_: any, r: ProcedureItem) => {
        const res = matchResults[r.id];
        const tier = res?.tier || r.last_tier;
        if (!tier) return <span className="text-text-secondary">—</span>;
        return <Tag color={TIER_COLORS[tier] || 'default'} className="m-0">{tier}</Tag>;
      },
    },
    {
      title: '匹配标准项（源 → 标准对应）', key: 'standards',
      render: (_: any, r: ProcedureItem) => {
        const res = matchResults[r.id];
        const matched = res?.matched ?? r.last_matched;
        const standards = res?.standards || r.last_standards || [];
        const detail = res?.detail || r.last_detail;
        if (matched === true && standards.length > 0) {
          return (
            <div className="space-y-0.5">
              {standards.map((s, i) => (
                <div key={i} className="text-xs">
                  <span className="font-mono text-brand-color">{s.code}</span>
                  <span className="ml-1.5 text-text-primary">{s.name}</span>
                </div>
              ))}
            </div>
          );
        }
        if (matched === false) {
          return <span className="text-xs text-text-secondary">{detail || '未命中'}</span>;
        }
        return r.um_status === 'open' && r.um_reason
          ? <span className="text-xs text-text-secondary">{REASON_META[r.um_reason]?.label || r.um_reason}</span>
          : <span className="text-text-secondary">—</span>;
      },
    },
    {
      title: '归因', key: 'reason', width: 130,
      render: (_: any, r: ProcedureItem) => {
        const res = matchResults[r.id];
        const reason = res?.reason_code || r.last_reason_code || (getStatus(r) === 'unmatched' ? r.um_reason : null);
        if (!reason) return <span className="text-text-secondary">—</span>;
        const meta = REASON_META[reason] || { label: reason, color: 'default' };
        return <Tag color={meta.color} className="m-0">{meta.label}</Tag>;
      },
    },
    {
      title: '操作', key: 'action', width: 90, fixed: 'right' as const,
      render: (_: any, r: ProcedureItem) => (
        <Button size="small" icon={<AimOutlined />} onClick={() => matchSingle(r.id)} disabled={batchRunning}>
          匹配
        </Button>
      ),
    },
  ];

  const itemsPanel = (
    <div className="space-y-4">
      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={12} md={6}>
          <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
            <div className="text-xs text-text-secondary">检查项目总数</div>
            <div className="text-2xl font-extrabold font-mono mt-1 text-text-primary">{filtered.length}</div>
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
            <div className="text-xs text-text-secondary">已匹配</div>
            <div className="text-2xl font-extrabold font-mono mt-1 text-emerald-600">{filteredMatched}</div>
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
            <div className="text-xs text-text-secondary">未匹配</div>
            <div className="text-2xl font-extrabold font-mono mt-1 text-red-500">{filteredUnmatched}</div>
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
            <div className="text-xs text-text-secondary">匹配率</div>
            <div className="text-2xl font-extrabold font-mono mt-1 text-brand-color">{matchRate}%</div>
          </Card>
        </Col>
      </Row>

      {/* 控制栏 */}
      <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Select
              value={modalityFilter}
              onChange={(v) => { setModalityFilter(v); setPage(1); }}
              options={modalityOptions}
              className="w-44"
              placeholder="按模态分类"
              showSearch
            />
            <Segmented
              value={statusFilter}
              onChange={(v) => { setStatusFilter(v as any); setPage(1); }}
              options={[
                { label: '全部', value: 'all' },
                { label: '已匹配', value: 'matched' },
                { label: '未匹配', value: 'unmatched' },
                { label: '未检测', value: 'unknown' },
              ]}
            />
            <Input
              value={searchText}
              onChange={(e) => { setSearchText(e.target.value); setPage(1); }}
              placeholder="搜索项目名称 / semantic_id"
              prefix={<SearchOutlined className="text-text-secondary" />}
              className="w-64"
              allowClear
            />
            <div className="flex-1" />
            <Button icon={<ReloadOutlined />} onClick={loadItems} disabled={batchRunning}>刷新</Button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Tooltip title="开启后，批量匹配开始前先失效全部 L1 缓存，确保结果来自当前规则版本；会增加本轮运行时间。">
              <div className="inline-flex items-center gap-2 px-3 h-8 rounded-lg border bg-bg-subtle border-border-theme">
                <DatabaseOutlined className="text-brand-color" />
                <span className="text-xs font-semibold text-text-primary">运行前清缓存</span>
                <Switch
                  size="small"
                  checked={clearCacheBeforeRun}
                  onChange={setClearCacheBeforeRun}
                  disabled={batchRunning}
                  aria-label="批量匹配运行前清除缓存"
                />
              </div>
            </Tooltip>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={matchAllFiltered}
              loading={batchRunning}
            >
              匹配当前筛选全部 ({filtered.length})
            </Button>
            <Button
              danger
              icon={<ThunderboltOutlined />}
              onClick={matchAllUnmatched}
              disabled={batchRunning || filteredUnmatched === 0}
            >
              仅匹配未匹配项 ({filteredUnmatched})
            </Button>
            {batchRunning && (
              <div className="flex items-center gap-2 flex-1 min-w-[200px]">
                <Progress
                  percent={batchProgress.total ? Math.round((batchProgress.done / batchProgress.total) * 100) : 0}
                  size="small"
                  className="flex-1"
                />
                <span className="text-xs text-text-secondary whitespace-nowrap">{batchProgress.done}/{batchProgress.total}</span>
              </div>
            )}
          </div>
          {/* 未匹配归因分布（本次会话） */}
          {Object.keys(reasonDist).length > 0 && (
            <div className="flex items-center gap-2 flex-wrap pt-1 border-t border-border-theme">
              <span className="text-xs font-semibold text-text-secondary">未匹配归因：</span>
              {Object.entries(reasonDist).map(([rc, cnt]) => {
                const meta = REASON_META[rc] || { label: rc, color: 'default' };
                return <Tag key={rc} color={meta.color} className="m-0">{meta.label} {cnt}</Tag>;
              })}
              <Tooltip title="切换到“未匹配分析”页签可查看完整清单并进行 LLM 分析与处理">
                <Button size="small" type="link" onClick={() => setActiveTab('unmatched')}>前往未匹配分析 →</Button>
              </Tooltip>
            </div>
          )}
        </div>
      </Card>

      {/* 项目表格 */}
      <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
        <Table
          rowKey="id"
          size="small"
          loading={itemsLoading}
          columns={columns}
          dataSource={filtered}
          scroll={{ x: 900 }}
          pagination={{
            current: page,
            pageSize,
            total: filtered.length,
            showSizeChanger: true,
            pageSizeOptions: ['20', '50', '100', '200'],
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); },
          }}
        />
      </Card>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="border-b pb-3 border-border-theme">
        <h2 className="text-xl font-bold tracking-tight flex items-center gap-2 m-0 text-text-primary">
          <ExperimentOutlined className="text-brand-color" />
          匹配测试中心
        </h2>
        <p className="text-xs mt-1 m-0 text-text-secondary">
          <DatabaseOutlined className="mr-1" />
          基于检查项目字典（{items.length} 条）进行单例/全量匹配，展示源项目与标准项对应，未匹配项自动登记并可进一步分析
        </p>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        destroyInactiveTabPane
        items={[
          { key: 'items', label: '检查项目匹配', children: itemsPanel },
          { key: 'custom', label: '自定义测试', children: <SingleMatchPanel /> },
        ]}
      />
    </div>
  );
};

export default MatchTest;
