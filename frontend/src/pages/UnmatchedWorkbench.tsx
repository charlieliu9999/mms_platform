import { useCallback, useEffect, useState } from 'react';
import { message as antdMessage } from 'antd';
import { Loader2, RefreshCw, Search } from 'lucide-react';
import { adminAPI } from '../services/matchService';

// reason_code → 展示配色（遵循 DESIGN.md 语义色规范）
const REASON_COLOR: Record<string, string> = {
  unmatchable_by_design: 'bg-zinc-50 text-zinc-700 border-zinc-200 dark:bg-zinc-800/50 dark:text-zinc-300 dark:border-zinc-700',
  standard_lib_gap: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20',
  lexicon_gap: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20',
  needs_manual: 'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-500/10 dark:text-sky-400 dark:border-sky-500/20',
  engine_error: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/20',
};

const STATUS_LABELS: Record<string, string> = {
  open: '待处理',
  resolved: '已解决',
  wontfix: '无需匹配',
};

type ReasonGroup = {
  reason_code: string;
  total: number;
  open: number;
  resolved: number;
  wontfix: number;
  meta: { label?: string; hint?: string; action?: string };
};

type UnmatchedRow = {
  id: number;
  procedure_id: number;
  procedure_name: string;
  modality: string | null;
  reason_code: string;
  reason_label: string;
  detail: string | null;
  status: string;
  handled_at: string | null;
  updated_at: string | null;
};

function ReasonBadge({ code, label }: { code: string; label: string }) {
  const cls = REASON_COLOR[code] ?? 'bg-zinc-50 text-zinc-700 border-zinc-200 dark:bg-zinc-800/50 dark:text-zinc-300 dark:border-zinc-700';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${cls}`}>
      {label || code}
    </span>
  );
}

export default function UnmatchedWorkbench() {
  const [groups, setGroups] = useState<ReasonGroup[]>([]);
  const [total, setTotal] = useState(0);
  const [rows, setRows] = useState<UnmatchedRow[]>([]);
  const [rowTotal, setRowTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // 筛选：选中的原因分类 / 状态 / 名称搜索
  const [activeReason, setActiveReason] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');

  const loadSummary = useCallback(async () => {
    try {
      const res: any = await adminAPI.getUnmatchedSummary();
      setGroups(res.groups ?? []);
      setTotal(res.total ?? 0);
    } catch {
      antdMessage.error('加载未匹配汇总失败');
    }
  }, []);

  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      const res: any = await adminAPI.getUnmatchedList({
        page, page_size: pageSize,
        reason_code: activeReason || undefined,
        status: (status as any) || undefined,
        search: search || undefined,
      });
      setRows(res.data ?? []);
      setRowTotal(res.total ?? 0);
    } catch {
      antdMessage.error('加载未匹配列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, activeReason, status, search]);

  useEffect(() => { loadSummary(); }, [loadSummary]);
  useEffect(() => { loadList(); }, [loadList]);

  const handleStatusChange = async (row: UnmatchedRow, next: string) => {
    try {
      await adminAPI.updateUnmatchedStatus(row.id, next as any);
      antdMessage.success(`已标记为「${STATUS_LABELS[next] ?? next}」`);
      loadList();
      loadSummary();
    } catch {
      antdMessage.error('更新状态失败');
    }
  };

  const totalPages = Math.max(1, Math.ceil(rowTotal / pageSize));

  return (
    <div className="flex flex-col h-full space-y-3 p-6">
      <h1 className="text-2xl font-bold text-zinc-800 dark:text-zinc-100">未匹配工作台</h1>

      {/* 顶部：原因分类分组卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-2">
        <button
          onClick={() => { setActiveReason(''); setPage(1); }}
          className={`text-left rounded-lg border p-3 transition ${
            activeReason === ''
              ? 'border-blue-400 bg-blue-50 dark:bg-blue-500/10 dark:border-blue-500/40'
              : 'border-zinc-200 dark:border-zinc-800 hover:border-zinc-300'
          }`}
        >
          <div className="text-xs text-zinc-500 dark:text-zinc-400">全部未匹配</div>
          <div className="mt-1 text-2xl font-semibold text-zinc-900 dark:text-zinc-100">{total}</div>
        </button>
        {groups.map((g) => {
          const pct = total > 0 ? Math.round((g.total / total) * 100) : 0;
          return (
            <button
              key={g.reason_code}
              onClick={() => { setActiveReason(g.reason_code); setPage(1); }}
              title={g.meta?.hint}
              className={`text-left rounded-lg border p-3 transition ${
                activeReason === g.reason_code
                  ? 'border-blue-400 bg-blue-50 dark:bg-blue-500/10 dark:border-blue-500/40'
                  : 'border-zinc-200 dark:border-zinc-800 hover:border-zinc-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <ReasonBadge code={g.reason_code} label={g.meta?.label ?? g.reason_code} />
                <span className="text-xs text-zinc-400">{pct}%</span>
              </div>
              <div className="mt-1 text-2xl font-semibold text-zinc-900 dark:text-zinc-100">{g.total}</div>
              <div className="mt-0.5 text-[11px] text-zinc-500 dark:text-zinc-400">
                待处理 {g.open} · 已解决 {g.resolved} · 无需 {g.wontfix}
              </div>
            </button>
          );
        })}
      </div>

      {/* 工具栏 */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400" />
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { setSearch(searchInput.trim()); setPage(1); } }}
            placeholder="搜索 ACR 项目名称"
            className="pl-7 pr-2 py-1.5 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 w-56"
          />
        </div>
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="py-1.5 px-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900"
        >
          <option value="">全部状态</option>
          <option value="open">待处理</option>
          <option value="resolved">已解决</option>
          <option value="wontfix">无需匹配</option>
        </select>
        <button
          onClick={() => { loadList(); loadSummary(); }}
          className="inline-flex items-center gap-1 py-1.5 px-3 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900"
        >
          <RefreshCw className="w-3.5 h-3.5" /> 刷新
        </button>
        <span className="text-xs text-zinc-400 ml-auto">共 {rowTotal} 条</span>
      </div>

      {/* 列表 */}
      <div className="flex-1 min-h-0 overflow-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-zinc-50 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400">
            <tr>
              <th className="text-left font-medium px-3 py-2">ACR 项目</th>
              <th className="text-left font-medium px-3 py-2 w-20">模态</th>
              <th className="text-left font-medium px-3 py-2 w-32">未匹配原因</th>
              <th className="text-left font-medium px-3 py-2">诊断信息</th>
              <th className="text-left font-medium px-3 py-2 w-24">状态</th>
              <th className="text-left font-medium px-3 py-2 w-56">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="px-3 py-10 text-center text-zinc-400">
                <Loader2 className="w-5 h-5 animate-spin inline" />
              </td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={6} className="px-3 py-10 text-center text-zinc-400">暂无未匹配项</td></tr>
            ) : rows.map((row) => (
              <tr key={row.id} className="border-t border-zinc-100 dark:border-zinc-800/60 hover:bg-zinc-50/60 dark:hover:bg-zinc-900/40">
                <td className="px-3 py-2 text-zinc-800 dark:text-zinc-200">{row.procedure_name}</td>
                <td className="px-3 py-2 text-zinc-500">{row.modality || '-'}</td>
                <td className="px-3 py-2"><ReasonBadge code={row.reason_code} label={row.reason_label} /></td>
                <td className="px-3 py-2 text-zinc-400">{row.detail || '-'}</td>
                <td className="px-3 py-2 text-zinc-500">{STATUS_LABELS[row.status] ?? row.status}</td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    {row.status !== 'wontfix' && (
                      <button onClick={() => handleStatusChange(row, 'wontfix')}
                        className="px-2 py-1 rounded border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs">
                        确认无需匹配
                      </button>
                    )}
                    {row.status !== 'open' && (
                      <button onClick={() => handleStatusChange(row, 'open')}
                        className="px-2 py-1 rounded border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs">
                        重新打开
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 分页 */}
      <div className="flex items-center justify-end gap-2 text-xs">
        <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}
          className="px-2 py-1 rounded border border-zinc-200 dark:border-zinc-800 disabled:opacity-40">上一页</button>
        <span className="text-zinc-500">{page} / {totalPages}</span>
        <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}
          className="px-2 py-1 rounded border border-zinc-200 dark:border-zinc-800 disabled:opacity-40">下一页</button>
      </div>
    </div>
  );
}
