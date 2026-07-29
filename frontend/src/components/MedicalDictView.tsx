import { useCallback, useEffect, useState } from 'react';
import { message as antdMessage, Modal } from 'antd';
import { Loader2, Plus, RefreshCw, Search, Trash2, Pencil } from 'lucide-react';
import { adminAPI } from '../services/matchService';

// jieba 词典类型（对应 nlp_medical_dict.type 已出现的值）
const TYPES: { key: string; label: string; hint: string }[] = [
  { key: 'body', label: '部位', hint: '身体部位词' },
  { key: 'scan', label: '扫描方式', hint: 'CT/MR/DR 通用扫描方式' },
  { key: 'post', label: '后处理', hint: 'CTA/MRA/3D 等后处理' },
  { key: 'position', label: '摆位', hint: '正位/侧位/斜位 等' },
  { key: 'device', label: '设备', hint: '设备类别词' },
  { key: 'mgscan', label: 'MG 扫描', hint: '钼靶专用扫描方式' },
  { key: 'rfscan', label: 'RF 扫描', hint: '透视专用扫描方式' },
  { key: 'scope', label: '范围', hint: '标准范围（基础/超声/核医学）' },
  { key: 'other', label: '其他', hint: '其他未分类词' },
];

type Row = { id: number; word: string; type: string; enable: number };

export function MedicalDictView() {
  const [activeType, setActiveType] = useState('body');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 100;
  const [rows, setRows] = useState<Row[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  type EditState = { mode: 'new' | 'edit'; row?: Row };
  const [edit, setEdit] = useState<EditState | null>(null);
  const [form, setForm] = useState<{ word: string; type: string; enable: number }>({
    word: '', type: 'body', enable: 0,
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res: any = await adminAPI.getLexiconRows('medical_dict', {
        page, page_size: pageSize, search: search || undefined, type: activeType,
      });
      setRows(res.data ?? []); setTotal(res.total ?? 0);
    } catch { antdMessage.error('加载词典失败'); }
    finally { setLoading(false); }
  }, [activeType, search, page]);

  useEffect(() => { load(); }, [load]);

  const openNew = () => { setEdit({ mode: 'new' }); setForm({ word: '', type: activeType, enable: 0 }); };
  const openEdit = (row: Row) => { setEdit({ mode: 'edit', row }); setForm({ word: row.word, type: row.type, enable: row.enable }); };
  const closeEdit = () => setEdit(null);

  const handleSave = async () => {
    if (!form.word.trim()) { antdMessage.warning('请输入词语'); return; }
    try {
      const payload = { word: form.word.trim(), type: form.type, enable: Number(form.enable) };
      if (edit?.mode === 'new') { await adminAPI.createLexiconRow('medical_dict', payload); antdMessage.success('已新增'); }
      else if (edit?.row) { await adminAPI.updateLexiconRow('medical_dict', edit.row.id, payload); antdMessage.success('已更新'); }
      closeEdit(); load();
    } catch { antdMessage.error('保存失败'); }
  };

  const handleDelete = (row: Row) => {
    Modal.confirm({
      title: '停用该词条？', content: `${row.word} · ${row.type}`,
      okType: 'danger',
      onOk: async () => {
        try { await adminAPI.deleteLexiconRow('medical_dict', row.id); antdMessage.success('已停用'); load(); }
        catch { antdMessage.error('停用失败'); }
      },
    });
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const typeHint = TYPES.find((t) => t.key === activeType)?.hint ?? '';

  return (
    <div className="flex flex-col h-full space-y-3">
      <div className="flex items-center gap-1 flex-wrap">
        {TYPES.map((t) => (
          <button key={t.key} onClick={() => { setActiveType(t.key); setPage(1); }}
            title={t.hint}
            className={`px-2.5 py-1 text-xs rounded-md border transition ${
              activeType === t.key
                ? 'bg-blue-600 text-white border-blue-600'
                : 'border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-900'
            }`}>
            {t.label}
          </button>
        ))}
        <span className="text-[10px] text-zinc-400 ml-2">{typeHint}</span>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400" />
          <input value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { setSearch(searchInput.trim()); setPage(1); } }}
            placeholder="搜索词语"
            className="pl-7 pr-2 py-1.5 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 w-52" />
        </div>
        <button onClick={openNew}
          className="inline-flex items-center gap-1 py-1.5 px-3 text-xs rounded-md bg-blue-600 text-white hover:bg-blue-700">
          <Plus className="w-3.5 h-3.5" /> 新增
        </button>
        <button onClick={load}
          className="inline-flex items-center gap-1 py-1.5 px-3 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900">
          <RefreshCw className="w-3.5 h-3.5" /> 刷新
        </button>
        <span className="text-xs text-zinc-400 ml-auto">共 {total} 条</span>
      </div>

      <div className="flex-1 min-h-0 overflow-auto rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/40 p-2">
        {loading ? (
          <div className="text-center py-10 text-zinc-400"><Loader2 className="w-5 h-5 animate-spin inline" /></div>
        ) : rows.length === 0 ? (
          <div className="text-center py-10 text-zinc-400">暂无数据</div>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {rows.map((r) => (
              <span key={r.id}
                className={`group inline-flex items-center gap-1 pl-2 pr-1 py-0.5 text-xs rounded-full border transition-colors ${
                  r.enable === 0
                    ? 'border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/60 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                    : 'border-zinc-300 dark:border-zinc-600 bg-zinc-100 dark:bg-zinc-800/30 text-zinc-400 line-through hover:bg-zinc-200 dark:hover:bg-zinc-800/50'
                }`}
                title={`#${r.id} · ${r.type}${r.enable === 1 ? ' · 已停用' : ''}`}>
                {r.word}
                <button onClick={() => openEdit(r)} title="编辑"
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-white dark:hover:bg-zinc-700 text-zinc-500">
                  <Pencil className="w-3 h-3" />
                </button>
                <button onClick={() => handleDelete(r)} title="停用"
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-rose-50 dark:hover:bg-rose-500/10 text-rose-500">
                  <Trash2 className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center justify-end gap-2 text-xs">
        <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}
          className="px-2 py-1 rounded border border-zinc-200 dark:border-zinc-800 disabled:opacity-40">上一页</button>
        <span className="text-zinc-500">{page} / {totalPages}</span>
        <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}
          className="px-2 py-1 rounded border border-zinc-200 dark:border-zinc-800 disabled:opacity-40">下一页</button>
      </div>

      <Modal open={edit !== null}
        title={edit?.mode === 'new' ? '新增词条' : `编辑词条 #${edit?.row?.id}`}
        onOk={handleSave} onCancel={closeEdit} okText="保存" cancelText="取消" destroyOnClose>
        <div className="space-y-2 py-2 text-xs">
          <div className="flex items-center gap-2">
            <label className="w-20 text-right shrink-0 text-zinc-500">词语</label>
            <input value={form.word} onChange={(e) => setForm((f) => ({ ...f, word: e.target.value }))}
              className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900" />
          </div>
          <div className="flex items-center gap-2">
            <label className="w-20 text-right shrink-0 text-zinc-500">类型</label>
            <select value={form.type} onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
              className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900">
              {TYPES.map((t) => <option key={t.key} value={t.key}>{t.label} ({t.key})</option>)}
            </select>
          </div>
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
