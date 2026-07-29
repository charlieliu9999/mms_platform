import { useCallback, useEffect, useState } from 'react';
import { message as antdMessage } from 'antd';
import { Loader2, RefreshCw, Search } from 'lucide-react';
import { adminAPI } from '../services/matchService';

// 标准查找表：ACR 标准项目池，20K+ 只读为主
// 结构：modality × body(1/2/3级) × scan × post_processing × position × scope
type Row = {
  id: number;
  modality_name: string | null;
  device_type_name: string | null;
  one_level_name: string | null;
  two_level_name: string | null;
  three_level_name: string | null;
  scan_name: string | null;
  post_processing_name: string | null;
  position_name: string | null;
  scope_name: string | null;
  checkitem_code: string | null;
  checkitem_name: string | null;
  version: string;
  is_deleted: number;
};

const MODALITIES = ['', 'CT', 'MR', 'DR', 'RF', 'MG', 'US', 'PET', 'SPECT', 'DSA', 'OCT'];

type Props = { activeVersion: string };

export function CheckitemStandardView({ activeVersion }: Props) {
  const [modality, setModality] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [rows, setRows] = useState<Row[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = {
        page, page_size: pageSize, search: search || undefined,
      };
      if (activeVersion) params.version = activeVersion;
      if (modality) params.modality_name = modality;
      const res: any = await adminAPI.getLexiconRows('checkitem_standard', params);
      setRows(res.data ?? []); setTotal(res.total ?? 0);
    } catch { antdMessage.error('加载标准查找表失败'); }
    finally { setLoading(false); }
  }, [modality, search, page, activeVersion]);

  useEffect(() => { load(); }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  // 按当前页数据动态隐藏全空列（V3.8.2 一级/二级部位就是空的）
  const hasValue = (key: keyof Row) => rows.some((r) => r[key] != null && String(r[key]).trim() !== '');
  const cols = ([
    { key: 'modality_name', label: '模态' },
    { key: 'one_level_name', label: '一级部位' },
    { key: 'two_level_name', label: '二级' },
    { key: 'three_level_name', label: '三级部位', className: 'font-medium text-zinc-800 dark:text-zinc-100' },
    { key: 'scan_name', label: '扫描' },
    { key: 'post_processing_name', label: '后处理' },
    { key: 'position_name', label: '摆位' },
    { key: 'scope_name', label: '范围' },
    { key: 'checkitem_code', label: '编码', className: 'text-zinc-400 font-mono text-[10px]' },
    { key: 'checkitem_name', label: '名称' },
  ] as { key: keyof Row; label: string; className?: string }[])
    .filter((c) => hasValue(c.key));

  return (
    <div className="flex flex-col h-full space-y-3">
      <div className="rounded-md border border-amber-200 dark:border-amber-500/40 bg-amber-50/60 dark:bg-amber-500/5 px-3 py-2 text-[11px] text-amber-700 dark:text-amber-300">
        标准查找表由 ACR 官方项目池导入，仅提供检索浏览。新增/修改请通过导入流程或专用工单。
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <select value={modality} onChange={(e) => { setModality(e.target.value); setPage(1); }}
          className="py-1.5 px-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
          {MODALITIES.map((m) => <option key={m || 'all'} value={m}>{m || '全部模态'}</option>)}
        </select>
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400" />
          <input value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { setSearch(searchInput.trim()); setPage(1); } }}
            placeholder="搜索部位/扫描/编码/名称"
            className="pl-7 pr-2 py-1.5 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 w-64" />
        </div>
        <button onClick={load}
          className="inline-flex items-center gap-1 py-1.5 px-3 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900">
          <RefreshCw className="w-3.5 h-3.5" /> 刷新
        </button>
        <span className="text-xs text-zinc-400 ml-auto">共 {total} 条 · 版本 {activeVersion || '—'}</span>
      </div>

      <div className="flex-1 min-h-0 overflow-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-zinc-50 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400">
            <tr>
              <th className="text-left font-medium px-2 py-2 w-14">ID</th>
              {cols.map((c) => (
                <th key={String(c.key)} className="text-left font-medium px-2 py-2">{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={cols.length + 1} className="px-3 py-10 text-center text-zinc-400"><Loader2 className="w-5 h-5 animate-spin inline" /></td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={cols.length + 1} className="px-3 py-10 text-center text-zinc-400">暂无数据</td></tr>
            ) : rows.map((r) => (
              <tr key={r.id} className="border-t border-zinc-100 dark:border-zinc-800/60 hover:bg-zinc-50/60 dark:hover:bg-zinc-900/40">
                <td className="px-2 py-1.5 text-zinc-400">{r.id}</td>
                {cols.map((c) => (
                  <td key={String(c.key)}
                    className={`px-2 py-1.5 max-w-xs truncate ${c.className ?? 'text-zinc-700 dark:text-zinc-300'}`}
                    title={String(r[c.key] ?? '')}>
                    {c.key === 'modality_name' && r.modality_name
                      ? <span className="px-1.5 py-0.5 text-[10px] rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300">{r.modality_name}</span>
                      : String(r[c.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

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
