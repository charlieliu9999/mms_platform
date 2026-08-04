import { useCallback, useEffect, useMemo, useState } from 'react';
import { message as antdMessage, Modal } from 'antd';
import { Loader2, Plus, RefreshCw, Search, Trash2, Pencil } from 'lucide-react';
import { adminAPI } from '../services/matchService';

// 关键词匹配规则：US/SPECT/PET/OCT/DSA 专用（其他模态走 phrase_map + checkitem_standard）
const MODALITIES = ['US', 'SPECT', 'PET', 'OCT', 'DSA'];
const RULE_TYPES: { key: string; label: string; hint: string }[] = [
  { key: 'body', label: '部位', hint: '命中关键词 → 归为对应部位' },
  { key: 'scan', label: '扫描方式', hint: '命中关键词 → 归为对应扫描方式' },
  { key: 'unmatchable', label: '不可匹配', hint: '命中即视为该模态下无法匹配（黑名单）' },
];

type Row = {
  id: number;
  modality: string;
  rule_type: string;
  keywords: string;
  dst_value: string | null;
  priority: number;
  enable: number;
  remark: string | null;
};

export function KeywordRuleView() {
  const [modality, setModality] = useState('US');
  const [ruleType, setRuleType] = useState('body');
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
    modality: string; rule_type: string; keywords: string;
    dst_value: string; priority: number; enable: number; remark: string;
  }>({ modality: 'US', rule_type: 'body', keywords: '', dst_value: '', priority: 100, enable: 1, remark: '' });  // F-06: 默认停用

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res: any = await adminAPI.getLexiconRows('keyword_match_rules', {
        page, page_size: pageSize, search: search || undefined,
        modality, rule_type: ruleType,
      });
      setRows(res.data ?? []); setTotal(res.total ?? 0);
    } catch { antdMessage.error('加载关键词规则失败'); }
    finally { setLoading(false); }
  }, [modality, ruleType, search, page]);

  useEffect(() => { load(); }, [load]);

  const openNew = () => {
    setEdit({ mode: 'new' });
    setForm({ modality, rule_type: ruleType, keywords: '', dst_value: '', priority: 100, enable: 1, remark: '' });  // F-06: 默认停用
  };
  const openEdit = (row: Row) => {
    setEdit({ mode: 'edit', row });
    setForm({
      modality: row.modality, rule_type: row.rule_type,
      keywords: row.keywords, dst_value: row.dst_value ?? '',
      priority: row.priority, enable: row.enable, remark: row.remark ?? '',
    });
  };
  const closeEdit = () => setEdit(null);

  const handleSave = async () => {
    if (!form.keywords.trim()) { antdMessage.warning('关键词组不能为空'); return; }
    if (form.rule_type !== 'unmatchable' && !form.dst_value.trim()) {
      antdMessage.warning('body/scan 规则必须填写目标值'); return;
    }
    try {
      const payload = {
        modality: form.modality, rule_type: form.rule_type,
        keywords: form.keywords.trim(),
        dst_value: form.dst_value.trim() || null,
        priority: Number(form.priority), enable: Number(form.enable),
        remark: form.remark.trim() || null,
      };
      if (edit?.mode === 'new') {
        await adminAPI.createLexiconRow('keyword_match_rules', payload); antdMessage.success('已新增');
      } else if (edit?.row) {
        await adminAPI.updateLexiconRow('keyword_match_rules', edit.row.id, payload); antdMessage.success('已更新');
      }
      closeEdit(); load();
    } catch { antdMessage.error('保存失败'); }
  };

  const handleDelete = (row: Row) => {
    Modal.confirm({
      title: '确认停用该规则？',
      content: `${row.modality}/${row.rule_type} · ${row.keywords} → ${row.dst_value || '(不可匹配)'}`,
      okType: 'danger',
      onOk: async () => {
        try { await adminAPI.deleteLexiconRow('keyword_match_rules', row.id); antdMessage.success('已停用'); load(); }
        catch { antdMessage.error('停用失败'); }
      },
    });
  };

  const ruleHint = useMemo(() => RULE_TYPES.find((r) => r.key === ruleType)?.hint ?? '', [ruleType]);
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="flex flex-col h-full space-y-3">
      {/* 模态 tab */}
      <div className="flex items-center gap-1 flex-wrap">
        {MODALITIES.map((m) => (
          <button key={m} onClick={() => { setModality(m); setPage(1); }}
            className={`px-2.5 py-1 text-xs rounded-md border transition cursor-pointer ${
              modality === m
                ? 'bg-brand-color text-white border-brand-color'
                : 'bg-bg-card border-border-theme text-text-secondary hover:bg-bg-subtle'
            }`}>
            {m}
          </button>
        ))}
      </div>

      {/* 规则类型 tab */}
      <div className="flex items-center gap-1 flex-wrap">
        {RULE_TYPES.map((r) => (
          <button key={r.key} onClick={() => { setRuleType(r.key); setPage(1); }}
            title={r.hint}
            className={`px-2.5 py-1 text-xs rounded-md border transition cursor-pointer ${
              ruleType === r.key
                ? 'bg-emerald-600 text-white border-emerald-600'
                : 'bg-bg-card border-border-theme text-text-secondary hover:bg-bg-subtle'
            }`}>
            {r.label}
          </button>
        ))}
        <span className="text-[10px] ml-2 text-text-secondary">{ruleHint}</span>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-secondary" />
          <input value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { setSearch(searchInput.trim()); setPage(1); } }}
            placeholder="搜索关键词/目标值"
            className="pl-7 pr-2 py-1.5 text-xs rounded-md border bg-bg-card border-border-theme text-text-primary w-56" />
        </div>
        <button onClick={openNew}
          className="inline-flex items-center gap-1 py-1.5 px-3 text-xs rounded-md bg-brand-color text-white hover:opacity-90 cursor-pointer">
          <Plus className="w-3.5 h-3.5" /> 新增
        </button>
        <button onClick={load}
          className="inline-flex items-center gap-1 py-1.5 px-3 text-xs rounded-md border bg-bg-card border-border-theme text-text-secondary hover:bg-bg-subtle cursor-pointer">
          <RefreshCw className="w-3.5 h-3.5" /> 刷新
        </button>
        <span className="text-xs ml-auto text-text-secondary">共 {total} 条 · 按 priority 升序</span>
      </div>

      <div className="flex-1 min-h-0 overflow-auto rounded-lg border border-border-theme">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-bg-subtle text-text-secondary">
            <tr>
              <th className="text-left font-medium px-2 py-2 w-14">ID</th>
              <th className="text-left font-medium px-2 py-2 w-16">优先级</th>
              <th className="text-left font-medium px-2 py-2">关键词组（+分隔）</th>
              <th className="text-left font-medium px-2 py-2">目标值</th>
              <th className="text-left font-medium px-2 py-2 w-14">生效</th>
              <th className="text-left font-medium px-2 py-2">备注</th>
              <th className="text-left font-medium px-2 py-2 w-20">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-3 py-10 text-center text-text-secondary"><Loader2 className="w-5 h-5 animate-spin inline" /></td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={7} className="px-3 py-10 text-center text-text-secondary">暂无数据</td></tr>
            ) : rows.map((r) => (
              <tr key={r.id} className="border-t border-border-theme hover:bg-bg-subtle/50">
                <td className="px-2 py-1.5 text-text-secondary">{r.id}</td>
                <td className="px-2 py-1.5"><span className="px-1.5 py-0.5 text-[10px] rounded bg-bg-subtle text-text-secondary">{r.priority}</span></td>
                <td className="px-2 py-1.5">
                  <div className="flex flex-wrap gap-1">
                    {r.keywords.split('+').filter(Boolean).map((k, i) => (
                      <span key={i} className="px-1.5 py-0.5 text-[11px] rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-100 dark:border-emerald-500/30">{k}</span>
                    ))}
                  </div>
                </td>
                <td className="px-2 py-1.5 font-medium text-text-primary">
                  {r.dst_value || <span className="text-rose-500 text-[10px]">(不可匹配)</span>}
                </td>
                <td className="px-2 py-1.5">
                  {r.enable === 0
                    ? <span className="text-emerald-500">✓</span>
                    : <span className="opacity-40">✕</span>}
                </td>
                <td className="px-2 py-1.5 text-text-secondary max-w-xs truncate" title={r.remark ?? ''}>{r.remark ?? ''}</td>
                <td className="px-2 py-1.5">

                  <div className="flex items-center gap-1.5">
                    <button onClick={() => openEdit(r)} title="编辑"
                      className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500">
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button onClick={() => handleDelete(r)} title="停用"
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
        title={edit?.mode === 'new' ? '新增关键词规则' : `编辑规则 #${edit?.row?.id}`}
        onOk={handleSave} onCancel={closeEdit} okText="保存" cancelText="取消" destroyOnClose>
        <div className="space-y-2 py-2 text-xs">
          <div className="grid grid-cols-2 gap-2">
            <div className="flex items-center gap-2">
              <label className="w-20 text-right shrink-0 text-zinc-500">模态</label>
              <select value={form.modality} onChange={(e) => setForm((f) => ({ ...f, modality: e.target.value }))}
                className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900">
                {MODALITIES.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="w-20 text-right shrink-0 text-zinc-500">规则类型</label>
              <select value={form.rule_type} onChange={(e) => setForm((f) => ({ ...f, rule_type: e.target.value }))}
                className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900">
                {RULE_TYPES.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
              </select>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="w-20 text-right shrink-0 text-zinc-500">关键词组</label>
            <input value={form.keywords} onChange={(e) => setForm((f) => ({ ...f, keywords: e.target.value }))}
              placeholder="用 + 分隔多个必须同时命中的关键词，如 心脏+超声"
              className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900" />
          </div>
          <div className="flex items-center gap-2">
            <label className="w-20 text-right shrink-0 text-zinc-500">目标值</label>
            <input value={form.dst_value} onChange={(e) => setForm((f) => ({ ...f, dst_value: e.target.value }))}
              placeholder={form.rule_type === 'unmatchable' ? '(留空)' : '匹配后归为该值'}
              disabled={form.rule_type === 'unmatchable'}
              className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 disabled:opacity-40" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="flex items-center gap-2">
              <label className="w-20 text-right shrink-0 text-zinc-500">优先级</label>
              <input type="number" value={form.priority}
                onChange={(e) => setForm((f) => ({ ...f, priority: Number(e.target.value) }))}
                className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900" />
            </div>
            <div className="flex items-center gap-2">
              <label className="w-20 text-right shrink-0 text-zinc-500">生效</label>
              <select value={form.enable}
                onChange={(e) => setForm((f) => ({ ...f, enable: Number(e.target.value) }))}
                className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900">
                <option value={0}>0 · 生效</option>
                <option value={1}>1 · 停用</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="w-20 text-right shrink-0 text-zinc-500">备注</label>
            <input value={form.remark} onChange={(e) => setForm((f) => ({ ...f, remark: e.target.value }))}
              className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900" />
          </div>
        </div>
      </Modal>
    </div>
  );
}
