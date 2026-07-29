import { useCallback, useEffect, useMemo, useState } from 'react';
import { message as antdMessage, Modal } from 'antd';
import { Loader2, Plus, RefreshCw, Search, Trash2, Pencil } from 'lucide-react';
import { adminAPI } from '../services/matchService';

// step 分类（对齐 nlp_phrase_map.step 值）
const STEPS: { key: string; label: string; hint: string }[] = [
  { key: 'normalize', label: '归一化', hint: '别名 → 标准名' },
  { key: 'pre', label: '预处理', hint: '文本清洗阶段的字符/词替换' },
  { key: 'process', label: '处理方式', hint: '扫描/后处理的合并拆分' },
  { key: 'global_map', label: '全局部位', hint: '两个部位合并为一个' },
  { key: 'local_map', label: '局部部位', hint: '括号内外位合并' },
  { key: 'vessel', label: '血管', hint: '血管相关映射' },
];

type Alias = { id: number; src_word: string; enable: number };
type Group = {
  dst_word: string;
  modality: string;
  step: string;
  version: string;
  aliases: Alias[];
  alias_count: number;
};

type Props = {
  activeVersion: string;
  onReload?: () => void;
};

export function PhraseMapView({ activeVersion }: Props) {
  const [step, setStep] = useState('normalize');
  const [modality, setModality] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 30;
  const [groups, setGroups] = useState<Group[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  // 编辑/新增弹窗（单条 alias 编辑）
  type EditState = { mode: 'new' | 'edit'; group?: Group; alias?: Alias };
  const [edit, setEdit] = useState<EditState | null>(null);
  const [form, setForm] = useState<{
    src_word: string; dst_word: string; step: string; modality: string; version: string;
  }>({ src_word: '', dst_word: '', step: 'normalize', modality: 'ALL', version: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, page_size: pageSize, step };
      if (activeVersion) params.version = activeVersion;
      if (modality) params.modality = modality;
      if (search) params.search = search;
      const res = (await adminAPI.getPhraseMapGrouped(params)) as unknown as { data: Group[]; total: number };
      setGroups(res.data ?? []);
      setTotal(res.total ?? 0);
    } catch { antdMessage.error('加载别名分组失败'); }
    finally { setLoading(false); }
  }, [step, modality, search, page, activeVersion]);

  useEffect(() => { load(); }, [load]);

  const openNew = (group?: Group) => {
    setEdit({ mode: 'new', group });
    setForm({
      src_word: '',
      dst_word: group?.dst_word && group.dst_word !== '(未指定)' ? group.dst_word : '',
      step: group?.step ?? step,
      modality: group?.modality ?? (modality || 'ALL'),
      version: group?.version ?? (activeVersion || 'V3.8.2'),
    });
  };
  const openEdit = (group: Group, alias: Alias) => {
    setEdit({ mode: 'edit', group, alias });
    setForm({
      src_word: alias.src_word,
      dst_word: group.dst_word === '(未指定)' ? '' : group.dst_word,
      step: group.step, modality: group.modality, version: group.version,
    });
  };
  const closeEdit = () => setEdit(null);

  const handleSave = async () => {
    if (!form.src_word.trim()) { antdMessage.warning('请输入源词（别名）'); return; }
    try {
      const payload = {
        src_word: form.src_word.trim(),
        dst_word: form.dst_word.trim() || null,
        step: form.step,
        modality: form.modality,
        version: form.version,
        enable: 0,
      };
      if (edit?.mode === 'new') {
        await adminAPI.createLexiconRow('phrase_map', payload);
        antdMessage.success('已新增别名');
      } else if (edit?.alias) {
        await adminAPI.updateLexiconRow('phrase_map', edit.alias.id, payload);
        antdMessage.success('已更新别名');
      }
      closeEdit(); load();
    } catch { antdMessage.error('保存失败'); }
  };

  const handleDelete = (group: Group, alias: Alias) => {
    Modal.confirm({
      title: '确认软删该别名？',
      content: `${alias.src_word} → ${group.dst_word || '(未指定)'} · ${group.modality}/${group.step}/${group.version}`,
      okType: 'danger',
      onOk: async () => {
        try {
          await adminAPI.deleteLexiconRow('phrase_map', alias.id);
          antdMessage.success('已软删'); load();
        } catch { antdMessage.error('删除失败'); }
      },
    });
  };

  const stepHint = useMemo(() => STEPS.find((s) => s.key === step)?.hint ?? '', [step]);
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="flex flex-col h-full space-y-3">
      {/* step 子 tab */}
      <div className="flex items-center gap-1 flex-wrap">
        {STEPS.map((s) => (
          <button key={s.key}
            onClick={() => { setStep(s.key); setPage(1); }}
            title={s.hint}
            className={`px-2.5 py-1 text-xs rounded-md border transition ${
              step === s.key
                ? 'bg-blue-600 text-white border-blue-600'
                : 'border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-900'
            }`}
          >
            {s.label}
          </button>
        ))}
        <span className="text-[10px] text-zinc-400 ml-2">{stepHint}</span>
      </div>

      {/* 工具栏 */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400" />
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { setSearch(searchInput.trim()); setPage(1); } }}
            placeholder="搜索源词/标准名，如 颅脑"
            className="pl-7 pr-2 py-1.5 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 w-60"
          />
        </div>
        <select value={modality}
          onChange={(e) => { setModality(e.target.value); setPage(1); }}
          className="py-1.5 px-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900"
        >
          <option value="">全部模态</option>
          {['ALL', 'CT', 'MR', 'DR', 'RF', 'MG'].map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <button onClick={() => openNew()}
          className="inline-flex items-center gap-1 py-1.5 px-3 text-xs rounded-md bg-blue-600 text-white hover:bg-blue-700">
          <Plus className="w-3.5 h-3.5" /> 新增别名
        </button>
        <button onClick={load}
          className="inline-flex items-center gap-1 py-1.5 px-3 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900">
          <RefreshCw className="w-3.5 h-3.5" /> 刷新
        </button>
        <span className="text-xs text-zinc-400 ml-auto">共 {total} 组</span>
      </div>

      {/* 别名分组列表：两列 标准名 → 别名(多个) */}
      <div className="flex-1 min-h-0 overflow-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-zinc-50 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400">
            <tr>
              <th className="text-left font-medium px-3 py-2 w-56">标准名（目标）</th>
              <th className="text-left font-medium px-3 py-2">别名（源词，多个）</th>
              <th className="text-left font-medium px-3 py-2 w-40">模态 · step · 版本</th>
              <th className="text-left font-medium px-3 py-2 w-16">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} className="px-3 py-10 text-center text-zinc-400"><Loader2 className="w-5 h-5 animate-spin inline" /></td></tr>
            ) : groups.length === 0 ? (
              <tr><td colSpan={4} className="px-3 py-10 text-center text-zinc-400">暂无数据</td></tr>
            ) : groups.map((g) => (
              <tr key={`${g.dst_word}-${g.modality}-${g.step}-${g.version}`}
                className="border-t border-zinc-100 dark:border-zinc-800/60 hover:bg-zinc-50/60 dark:hover:bg-zinc-900/40 align-top">
                <td className="px-3 py-2">
                  <div className="font-medium text-zinc-800 dark:text-zinc-100">{g.dst_word}</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">共 {g.alias_count} 个别名</div>
                </td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-1">
                    {g.aliases.map((a) => (
                      <span key={a.id}
                        className="group inline-flex items-center gap-1 pl-2 pr-1 py-0.5 rounded-full border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/60 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                        title={`#${a.id}`}>
                        {a.src_word}
                        <button onClick={() => openEdit(g, a)} title="编辑"
                          className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-white dark:hover:bg-zinc-700 text-zinc-500">
                          <Pencil className="w-3 h-3" />
                        </button>
                        <button onClick={() => handleDelete(g, a)} title="软删"
                          className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-rose-50 dark:hover:bg-rose-500/10 text-rose-500">
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <span className="px-1.5 py-0.5 text-[10px] rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 mr-1">{g.modality}</span>
                  <span className="px-1.5 py-0.5 text-[10px] rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 mr-1">{g.step}</span>
                  <span className="px-1.5 py-0.5 text-[10px] rounded bg-blue-100 dark:bg-blue-500/20 text-blue-600 dark:text-blue-300">{g.version}</span>
                </td>
                <td className="px-3 py-2">
                  <button onClick={() => openNew(g)} title="向本组添加别名"
                    className="p-1 rounded hover:bg-blue-50 dark:hover:bg-blue-500/10 text-blue-600">
                    <Plus className="w-3.5 h-3.5" />
                  </button>
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

      {/* 编辑/新增弹窗 */}
      <Modal
        open={edit !== null}
        title={edit?.mode === 'new' ? '新增别名' : `编辑别名 #${edit?.alias?.id}`}
        onOk={handleSave}
        onCancel={closeEdit}
        okText="保存"
        cancelText="取消"
        destroyOnClose
      >
        <div className="space-y-2 py-2 text-xs">
          <Field label="源词（别名）"
            value={form.src_word}
            onChange={(v) => setForm((f) => ({ ...f, src_word: v }))}
            placeholder="如 颅脑" />
          <Field label="标准名（目标）"
            value={form.dst_word}
            onChange={(v) => setForm((f) => ({ ...f, dst_word: v }))}
            placeholder="如 头颅（留空表示 pre 阶段的纯替换）" />
          <div className="flex items-center gap-2">
            <label className="w-24 text-right shrink-0 text-zinc-500">step</label>
            <select value={form.step} onChange={(e) => setForm((f) => ({ ...f, step: e.target.value }))}
              className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900">
              {STEPS.map((s) => <option key={s.key} value={s.key}>{s.label} ({s.key})</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="w-24 text-right shrink-0 text-zinc-500">模态</label>
            <select value={form.modality} onChange={(e) => setForm((f) => ({ ...f, modality: e.target.value }))}
              className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900">
              {['ALL', 'CT', 'MR', 'DR', 'RF', 'MG'].map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <Field label="版本"
            value={form.version}
            onChange={(v) => setForm((f) => ({ ...f, version: v }))}
            placeholder="V3.8.2" />
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
      <label className="w-24 text-right shrink-0 text-zinc-500">{label}</label>
      <input value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="flex-1 px-2 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900" />
    </div>
  );
}
