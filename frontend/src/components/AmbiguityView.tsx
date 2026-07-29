import { useCallback, useEffect, useState } from 'react';
import { message as antdMessage, Modal } from 'antd';
import { Loader2, Plus, RefreshCw, Search, Trash2, Pencil, ArrowRight } from 'lucide-react';
import { adminAPI } from '../services/matchService';

// 消歧规则：(src_body, src_process) → (dst_body, dst_process)，仅 4 个模态
const MODALITIES = ['CT', 'MR', 'DR', 'RF'];

type Row = {
  id: number;
  src_body: string | null;
  src_process: string | null;
  dst_body: string;
  dst_process: string;
  version: string;
  modality: string | null;
  enable: number;
};

type Props = { activeVersion: string };

export function AmbiguityView({ activeVersion }: Props) {
  const [modality, setModality] = useState('CT');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [rows, setRows] = useState<Row[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  type EditState = { mode: 'new' | 'edit'; row?: Row };
  const [edit, setEdit] = useState<EditState | null>(null);
  const [form, setForm] = useState<{
    src_body: string; src_process: string;
    dst_body: string; dst_process: string;
    modality: string; version: string; enable: number;
  }>({
    src_body: '', src_process: '', dst_body: '', dst_process: '',
    modality: 'CT', version: '', enable: 0,
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = {
        page, page_size: pageSize, search: search || undefined, modality,
      };
      if (activeVersion) params.version = activeVersion;
      const res: any = await adminAPI.getLexiconRows('ambiguity', params);
      setRows(res.data ?? []); setTotal(res.total ?? 0);
    } catch { antdMessage.error('加载消歧规则失败'); }
    finally { setLoading(false); }
  }, [modality, search, page, activeVersion]);

  useEffect(() => { load(); }, [load]);

  const openNew = () => {
    setEdit({ mode: 'new' });
    setForm({
      src_body: '', src_process: '', dst_body: '', dst_process: '',
      modality, version: activeVersion || 'V3.8.2', enable: 0,
    });
  };
  const openEdit = (row: Row) => {
    setEdit({ mode: 'edit', row });
    setForm({
      src_body: row.src_body ?? '', src_process: row.src_process ?? '',
      dst_body: row.dst_body, dst_process: row.dst_process,
      modality: row.modality ?? modality, version: row.version, enable: row.enable,
    });
  };
  const closeEdit = () => setEdit(null);

  const handleSave = async () => {
    if (!form.dst_body.trim() || !form.dst_process.trim()) {
      antdMessage.warning('目标部位/处理方式必填'); return;
    }
    try {
      const payload = {
        src_body: form.src_body.trim() || null,
        src_process: form.src_process.trim() || null,
        dst_body: form.dst_body.trim(),
        dst_process: form.dst_process.trim(),
        modality: form.modality,
        version: form.version,
        enable: Number(form.enable),
      };
      if (edit?.mode === 'new') {
        await adminAPI.createLexiconRow('ambiguity', payload); antdMessage.success('已新增');
      } else if (edit?.row) {
        await adminAPI.updateLexiconRow('ambiguity', edit.row.id, payload); antdMessage.success('已更新');
      }
      closeEdit(); load();
    } catch { antdMessage.error('保存失败'); }
  };

  const handleDelete = (row: Row) => {
    Modal.confirm({
      title: '确认软删该消歧规则？',
      content: `${row.src_body || '*'}/${row.src_process || '*'} → ${row.dst_body}/${row.dst_process}`,
      okType: 'danger',
      onOk: async () => {
        try { await adminAPI.deleteLexiconRow('ambiguity', row.id); antdMessage.success('已软删'); load(); }
        catch { antdMessage.error('删除失败'); }
      },
    });
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="flex flex-col h-full space-y-3">
      {/* 模态子 tab */}
      <div className="flex items-center gap-1 flex-wrap">
        {MODALITIES.map((m) => (
          <button key={m} onClick={() => { setModality(m); setPage(1); }}
            className={`px-2.5 py-1 text-xs rounded-md border transition ${
              modality === m
                ? 'bg-blue-600 text-white border-blue-600'
                : 'border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-900'
            }`}>
            {m}
          </button>
        ))}
        <span className="text-[10px] text-zinc-400 ml-2">
          源部位/源处理 → 目标部位/目标处理（源留空表示默认补全）
        </span>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400" />
          <input value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { setSearch(searchInput.trim()); setPage(1); } }}
            placeholder="搜索源/目标部位或处理"
            className="pl-7 pr-2 py-1.5 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 w-56" />
        </div>
        <button onClick={openNew}
          className="inline-flex items-center gap-1 py-1.5 px-3 text-xs rounded-md bg-blue-600 text-white hover:bg-blue-700">
          <Plus className="w-3.5 h-3.5" /> 新增规则
        </button>
        <button onClick={load}
          className="inline-flex items-center gap-1 py-1.5 px-3 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900">
          <RefreshCw className="w-3.5 h-3.5" /> 刷新
        </button>
        <span className="text-xs text-zinc-400 ml-auto">共 {total} 条</span>
      </div>

      <div className="flex-1 min-h-0 overflow-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-zinc-50 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400">
            <tr>
              <th className="text-left font-medium px-2 py-2 w-14">ID</th>
              <th className="text-left font-medium px-2 py-2">源部位</th>
              <th className="text-left font-medium px-2 py-2">源处理</th>
              <th className="w-6"></th>
              <th className="text-left font-medium px-2 py-2">目标部位</th>
              <th className="text-left font-medium px-2 py-2">目标处理</th>
              <th className="text-left font-medium px-2 py-2 w-16">模态</th>
              <th className="text-left font-medium px-2 py-2 w-20">版本</th>
              <th className="text-left font-medium px-2 py-2 w-20">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={9} className="px-3 py-10 text-center text-zinc-400"><Loader2 className="w-5 h-5 animate-spin inline" /></td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={9} className="px-3 py-10 text-center text-zinc-400">暂无数据</td></tr>
            ) : rows.map((r) => (
              <tr key={r.id} className="border-t border-zinc-100 dark:border-zinc-800/60 hover:bg-zinc-50/60 dark:hover:bg-zinc-900/40">
                <td className="px-2 py-1.5 text-zinc-400">{r.id}</td>
                <td className="px-2 py-1.5 text-zinc-700 dark:text-zinc-300">
                  {r.src_body || <span className="text-zinc-300">*</span>}
                </td>
                <td className="px-2 py-1.5 text-zinc-700 dark:text-zinc-300">
                  {r.src_process || <span className="text-zinc-300">*</span>}
                </td>
                <td className="px-1 text-zinc-300"><ArrowRight className="w-3 h-3" /></td>
                <td className="px-2 py-1.5 font-medium text-zinc-800 dark:text-zinc-100">{r.dst_body}</td>
                <td className="px-2 py-1.5 font-medium text-zinc-800 dark:text-zinc-100">{r.dst_process}</td>
                <td className="px-2 py-1.5"><span className="px-1.5 py-0.5 text-[10px] rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500">{r.modality || 'ALL'}</span></td>
                <td className="px-2 py-1.5"><span className="px-1.5 py-0.5 text-[10px] rounded bg-blue-100 dark:bg-blue-500/20 text-blue-600 dark:text-blue-300">{r.version}</span></td>
                <td className="px-2 py-1.5">
                  <div className="flex items-center gap-1.5">
                    <button onClick={() => openEdit(r)} title="编辑"
                      className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500">
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button onClick={() => handleDelete(r)} title="软删"
                      className="p-1 rounded hover:bg-rose-50 dark:hover:bg-rose-500/10 text-rose-500">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </td>
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

      <Modal open={edit !== null}
        title={edit?.mode === 'new' ? '新增消歧规则' : `编辑规则 #${edit?.row?.id}`}
        onOk={handleSave} onCancel={closeEdit} okText="保存" cancelText="取消" destroyOnClose>
        <div className="space-y-2 py-2 text-xs">
          <div className="grid grid-cols-2 gap-2">
            <Field label="源部位" value={form.src_body} onChange={(v) => setForm((f) => ({ ...f, src_body: v }))} placeholder="留空 = 通配" />
            <Field label="源处理" value={form.src_process} onChange={(v) => setForm((f) => ({ ...f, src_process: v }))} placeholder="留空 = 通配" />
            <Field label="目标部位" value={form.dst_body} onChange={(v) => setForm((f) => ({ ...f, dst_body: v }))} placeholder="必填" />
            <Field label="目标处理" value={form.dst_process} onChange={(v) => setForm((f) => ({ ...f, dst_process: v }))} placeholder="必填" />
          </div>
          <div className="flex items-center gap-2">
            <label className="w-20 text-right shrink-0 text-zinc-500">模态</label>
            <select value={form.modality} onChange={(e) => setForm((f) => ({ ...f, modality: e.target.value }))}
              className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900">
              {MODALITIES.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <Field label="版本" value={form.version} onChange={(v) => setForm((f) => ({ ...f, version: v }))} placeholder="V3.8.2" />
          <div className="flex items-center gap-2">
            <label className="w-20 text-right shrink-0 text-zinc-500">启用</label>
            <select value={form.enable}
              onChange={(e) => setForm((f) => ({ ...f, enable: Number(e.target.value) }))}
              className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900">
              <option value={0}>0 · 生效</option>
              <option value={1}>1 · 停用</option>
            </select>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function Field({ label, value, onChange, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <label className="w-20 text-right shrink-0 text-zinc-500">{label}</label>
      <input value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900" />
    </div>
  );
}
