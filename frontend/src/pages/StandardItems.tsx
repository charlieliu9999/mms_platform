import { useState, useEffect } from 'react';
import { adminAPI } from '../services/matchService';
import { FilterOutlined, SyncOutlined, CheckSquareOutlined, TagOutlined } from '@ant-design/icons';

// ── 标准项目清单 ──────────────────────────────────────────────────────────────

const MODALITIES = ['CT', 'MR', 'US', 'DR', 'RF', 'MG', 'DSA', 'OCT', 'PET/CT', 'PET/MR', 'SPECT'];

export default function StandardItems() {
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selectedVersion, setSelectedVersion] = useState<string>('');
  const [availableVersions, setAvailableVersions] = useState<string[]>([]);
  const [filters, setFilters] = useState({
    modality: '', body_part_l1: '', body_part_l2: '', body_part_l3: '',
    search: '',
  });
  const [options, setOptions] = useState<{ l1: string[]; l2: string[]; l3: string[] }>({
    l1: [], l2: [], l3: [],
  });
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await adminAPI.getStandardItems({
        page, page_size: 20,
        ...(selectedVersion && { version: selectedVersion }),
        ...(filters.modality && { modality: filters.modality }),
        ...(filters.body_part_l1 && { body_part_l1: filters.body_part_l1 }),
        ...(filters.body_part_l2 && { body_part_l2: filters.body_part_l2 }),
        ...(filters.body_part_l3 && { body_part_l3: filters.body_part_l3 }),
        ...(filters.search && { search: filters.search }),
      });
      setItems((res as any).data ?? []);
      setTotal((res as any).total ?? 0);
    } finally {
      setLoading(false);
    }
  };

  // 级联选项：随 模态/一级/二级 变化重新拉取下级可选值
  const loadOptions = async () => {
    const res: any = await adminAPI.getStandardItemFilterOptions({
      ...(filters.modality && { modality: filters.modality }),
      ...(filters.body_part_l1 && { body_part_l1: filters.body_part_l1 }),
      ...(filters.body_part_l2 && { body_part_l2: filters.body_part_l2 }),
    });
    setOptions({ l1: res.l1 ?? [], l2: res.l2 ?? [], l3: res.l3 ?? [] });
  };

  const loadStats = async (ver?: string) => {
    const res = await adminAPI.getStandardItemStats(ver ? { version: ver } : undefined);
    setStats(res);
    if (res?.available_versions && res.available_versions.length > 0) {
      setAvailableVersions(res.available_versions);
    }
  };

  useEffect(() => { load(); }, [page, filters, selectedVersion]);
  useEffect(() => { loadOptions(); }, [filters.modality, filters.body_part_l1, filters.body_part_l2]);
  useEffect(() => { loadStats(selectedVersion); }, [selectedVersion]);

  // 模态切换：清空下级部位选择
  const setModality = (v: string) => {
    setFilters(f => ({ ...f, modality: v, body_part_l1: '', body_part_l2: '', body_part_l3: '' }));
    setPage(1);
  };
  const setL1 = (v: string) => {
    setFilters(f => ({ ...f, body_part_l1: v, body_part_l2: '', body_part_l3: '' }));
    setPage(1);
  };
  const setL2 = (v: string) => {
    setFilters(f => ({ ...f, body_part_l2: v, body_part_l3: '' }));
    setPage(1);
  };
  const setL3 = (v: string) => {
    setFilters(f => ({ ...f, body_part_l3: v }));
    setPage(1);
  };

  const handleImportAll = async () => {
    setImporting(true);
    try {
      await adminAPI.importAllStandardItems();
      await load();
      await loadStats(selectedVersion);
    } catch (e) {
      console.error('Import failed:', e);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* 顶部标题与版本号选择器 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-100 dark:border-zinc-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight m-0 flex items-center gap-2">
            <CheckSquareOutlined className="text-blue-600 dark:text-blue-400" />
            标准检查项目库
          </h1>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 m-0">管理标准检查项目清单、模态部位分层和标准库规则版本</p>
        </div>

        {/* 版本号选择区域 */}
        <div className="flex items-center gap-2 bg-zinc-100/80 dark:bg-zinc-800/80 p-1.5 rounded-xl border border-zinc-200/80 dark:border-zinc-700/80">
          <TagOutlined className="text-blue-600 dark:text-blue-400 text-xs ml-2" />
          <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">标准版本号:</span>
          <select
            className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg text-xs font-semibold text-blue-700 dark:text-blue-400 px-3 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            value={selectedVersion}
            onChange={(e) => {
              setSelectedVersion(e.target.value);
              setPage(1);
            }}
          >
            <option value="">全部版本 (All Versions)</option>
            {availableVersions.map((ver) => (
              <option key={ver} value={ver}>
                {ver} {ver === 'V3.8.2' ? '(推荐/当前最新)' : ''}
              </option>
            ))}
          </select>

          {selectedVersion && (
            <button
              onClick={() => { setSelectedVersion(''); setPage(1); }}
              className="text-[11px] text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200 px-2 py-0.5 rounded transition"
            >
              重置
            </button>
          )}
        </div>
      </div>

      {/* 统计 Dashboard */}
      {stats && (
        <div className="space-y-4">
          {/* 核心总览 KPI 行 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border border-zinc-200/80 bg-white dark:border-zinc-800 dark:bg-zinc-900/60 rounded-xl p-5 shadow-xs flex items-center justify-between">
              <div>
                <div className="text-3xl font-extrabold text-blue-600 dark:text-blue-400 tracking-tight">{stats.total}</div>
                <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 mt-1">
                  {selectedVersion ? `[${selectedVersion}] 标准项目总数` : '全部标准项目总数'}
                </div>
              </div>
              <div className="w-12 h-12 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-lg">
                {selectedVersion || 'ALL'}
              </div>
            </div>

            <div className="border border-zinc-200/80 bg-white dark:border-zinc-800 dark:bg-zinc-900/60 rounded-xl p-5 shadow-xs flex items-center justify-between">
              <div>
                <div className="text-3xl font-extrabold text-emerald-600 dark:text-emerald-400 tracking-tight">
                  {stats.modality_count || Object.keys(stats.by_modality ?? {}).length}
                </div>
                <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 mt-1">覆盖模态数量</div>
              </div>
              <div className="w-12 h-12 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold text-lg">
                MOD
              </div>
            </div>

            <div className="border border-zinc-200/80 bg-white dark:border-zinc-800 dark:bg-zinc-900/60 rounded-xl p-5 shadow-xs flex items-center justify-between">
              <div>
                <div className="text-3xl font-extrabold text-amber-600 dark:text-amber-400 tracking-tight">
                  {stats.body_part_count || Object.keys(stats.by_body_part ?? {}).length}
                </div>
                <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 mt-1">一级部位解剖分类</div>
              </div>
              <div className="w-12 h-12 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center font-bold text-lg">
                ANAT
              </div>
            </div>
          </div>

          {/* 全部模态统计网格（点击快速按模态过滤） */}
          {stats?.by_modality && (
            <div className="border border-zinc-200/80 bg-white dark:border-zinc-800 dark:bg-zinc-900/40 rounded-xl p-4 shadow-xs">
              <div className="flex items-center justify-between mb-3 px-1">
                <span className="text-xs font-bold text-zinc-600 dark:text-zinc-400 uppercase tracking-wider">
                  各模态标准数 {selectedVersion ? `(${selectedVersion})` : ''}
                </span>
                <span className="text-[11px] text-zinc-400 dark:text-zinc-500 font-normal">点击任意模态按钮可快速筛选</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-11 gap-2.5">
                {MODALITIES.map((m) => {
                  const count = stats.by_modality[m] ?? 0;
                  const isSelected = filters.modality === m;
                  return (
                    <button
                      key={m}
                      onClick={() => setModality(isSelected ? '' : m)}
                      className={`p-3 rounded-xl border text-center transition-all duration-150 ${
                        isSelected
                          ? 'bg-blue-600 text-white border-blue-600 shadow-sm scale-105'
                          : count > 0
                          ? 'bg-zinc-50/60 dark:bg-zinc-800/40 border-zinc-200/80 dark:border-zinc-800 text-zinc-800 dark:text-zinc-200 hover:border-blue-500/50 hover:bg-blue-50/40 dark:hover:bg-blue-950/30'
                          : 'bg-zinc-50/30 dark:bg-zinc-900/20 border-zinc-100 dark:border-zinc-800/50 text-zinc-400 dark:text-zinc-600 opacity-60'
                      }`}
                    >
                      <div className={`text-base font-bold tracking-tight ${isSelected ? 'text-white' : ''}`}>
                        {count}
                      </div>
                      <div className={`text-xs font-medium mt-1 ${isSelected ? 'text-blue-100' : 'text-zinc-500 dark:text-zinc-400'}`}>
                        {m}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 工具栏 */}
      <div className="flex flex-wrap gap-2.5 items-center bg-zinc-50/60 dark:bg-zinc-800/40 p-3.5 rounded-xl border border-zinc-200/60 dark:border-zinc-800">
        <div className="flex items-center gap-1.5 text-xs text-zinc-400 dark:text-zinc-500 font-medium mr-1">
          <FilterOutlined /> 组合筛选:
        </div>
        <input
          className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs text-zinc-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition w-44"
          placeholder="搜索项目名称/编码..."
          value={filters.search}
          onChange={e => { setFilters(f => ({ ...f, search: e.target.value })); setPage(1); }}
        />
        <select
          className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition"
          value={filters.modality}
          onChange={e => setModality(e.target.value)}
        >
          <option value="">全部模态 (Modality)</option>
          {MODALITIES.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <select
          className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition disabled:opacity-50"
          value={filters.body_part_l1}
          disabled={options.l1.length === 0}
          onChange={e => setL1(e.target.value)}
        >
          <option value="">全部一级部位</option>
          {options.l1.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <select
          className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition disabled:opacity-50"
          value={filters.body_part_l2}
          disabled={options.l2.length === 0}
          onChange={e => setL2(e.target.value)}
        >
          <option value="">全部二级部位</option>
          {options.l2.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <select
          className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition disabled:opacity-50"
          value={filters.body_part_l3}
          disabled={options.l3.length === 0}
          onChange={e => setL3(e.target.value)}
        >
          <option value="">全部三级部位</option>
          {options.l3.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <div className="flex-1" />
        <button
          onClick={handleImportAll}
          disabled={importing}
          className="px-3.5 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-xs disabled:opacity-50 transition flex items-center gap-1.5"
        >
          <SyncOutlined spin={importing} />
          {importing ? '重新导入中...' : '从标准库同步导入'}
        </button>
      </div>

      {/* 列表表格 */}
      <div className="rounded-xl border border-zinc-200/80 bg-white dark:border-zinc-800 dark:bg-zinc-900 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-zinc-50 dark:bg-zinc-800/80 border-b border-zinc-200/80 dark:border-zinc-800 text-xs font-semibold text-zinc-500 dark:text-zinc-400 tracking-wider">
              <tr>
                {['项目编码', '项目标准名', '模态', '一级部位', '二级部位', '三级部位', '扫描方式', '版本来源'].map(h => (
                  <th key={h} className="px-4 py-3.5 font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/80">
              {loading ? (
                <tr><td colSpan={8} className="px-4 py-12 text-center text-zinc-400">正在检索标准检查项目数据...</td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={8} className="px-4 py-12 text-center text-zinc-400">未找到符合条件的标准检查项目</td></tr>
              ) : items.map((item: any) => (
                <tr key={item.id} className="hover:bg-zinc-50/80 dark:hover:bg-zinc-800/50 transition-colors">
                  <td className="px-4 py-3 text-xs text-zinc-400 dark:text-zinc-500 font-mono">{item.item_code}</td>
                  <td className="px-4 py-3 font-semibold text-zinc-900 dark:text-zinc-100">{item.item_name}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200/60 dark:bg-blue-950/60 dark:text-blue-400 dark:border-blue-800/50">
                      {item.modality}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-700 dark:text-zinc-300 font-medium">{item.body_part_l1}</td>
                  <td className="px-4 py-3 text-zinc-500 dark:text-zinc-400">{item.body_part_l2 || '-'}</td>
                  <td className="px-4 py-3 text-zinc-500 dark:text-zinc-400">{item.body_part_l3 || '-'}</td>
                  <td className="px-4 py-3 text-zinc-500 dark:text-zinc-400">{item.scan_method || '-'}</td>
                  <td className="px-4 py-3 text-xs">
                    <span className="inline-flex items-center px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 font-mono text-[11px]">
                      {item.version || 'V3.8.2'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {/* 分页 */}
        <div className="px-4 py-3 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400 bg-zinc-50/50 dark:bg-zinc-900/40">
          <span>共 {total} 条标准项目</span>
          <div className="flex gap-2 items-center">
            <button
              disabled={page <= 1}
              onClick={() => setPage(p => p - 1)}
              className="px-3 py-1 border border-zinc-200 dark:border-zinc-700 rounded-lg disabled:opacity-40 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 transition text-xs font-medium"
            >
              上一页
            </button>
            <span className="px-2 py-1 text-xs text-zinc-500 dark:text-zinc-400 font-medium">
              第 {page} 页 / {Math.ceil(total / 20) || 1} 页
            </span>
            <button
              disabled={page >= Math.ceil(total / 20)}
              onClick={() => setPage(p => p + 1)}
              className="px-3 py-1 border border-zinc-200 dark:border-zinc-700 rounded-lg disabled:opacity-40 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 transition text-xs font-medium"
            >
              下一页
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


