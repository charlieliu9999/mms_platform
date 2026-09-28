import { useCallback, useEffect, useState } from 'react';
import { message as antdMessage, Drawer, Button, Input, Select, Tag } from 'antd';
import { Loader2, Plus, RefreshCw, Search, Trash2, Pencil, ArrowRight } from 'lucide-react';
import { adminAPI } from '../services/matchService';

// step 分类
const STEPS: { key: string; label: string; hint: string }[] = [
  { key: 'normalize', label: '归一化', hint: '别名 → 标准名' },
  { key: 'pre', label: '预处理', hint: '文本清洗阶段的字符/词替换' },
  { key: 'process', label: '处理方式', hint: '扫描/后处理的合并拆分' },
  { key: 'global_map', label: '全局部位', hint: '两个部位合并为一个' },
  { key: 'local_map', label: '局部部位', hint: '括号内外部位合并' },
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

  // 抽屉编辑模式
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
    } catch {
      antdMessage.error('加载别名分组失败');
    } finally {
      setLoading(false);
    }
  }, [activeVersion, modality, search, step, page]);

  useEffect(() => { load(); }, [load]);

  const openNewForGroup = (group?: Group) => {
    setForm({
      src_word: '',
      dst_word: group?.dst_word || '',
      step: group?.step || step,
      modality: group?.modality || 'ALL',
      version: activeVersion || '',
    });
    setEdit({ mode: 'new', group });
  };

  const openEditAlias = (group: Group, alias: Alias) => {
    setForm({
      src_word: alias.src_word,
      dst_word: group.dst_word,
      step: group.step,
      modality: group.modality,
      version: group.version || activeVersion || '',
    });
    setEdit({ mode: 'edit', group, alias });
  };

  const closeEdit = () => setEdit(null);

  const handleSave = async () => {
    if (!form.src_word.trim() || !form.dst_word.trim()) {
      antdMessage.warning('原词与目标词均不可为空');
      return;
    }
    try {
      const payload = {
        src_word: form.src_word.trim(),
        dst_word: form.dst_word.trim(),
        step: form.step,
        modality: form.modality || 'ALL',
        version: form.version || undefined,
        enable: 1,  // F-06: 默认停用
      };
      if (edit?.mode === 'new') {
        await adminAPI.createLexiconRow('phrase_map', payload);
        antdMessage.success('已添加别名映射');
      } else if (edit?.alias) {
        await adminAPI.updateLexiconRow('phrase_map', edit.alias.id, payload);
        antdMessage.success('已更新别名映射');
      }
      closeEdit();
      load();
    } catch {
      antdMessage.error('保存别名映射失败');
    }
  };

  const handleDeleteAlias = async (aliasId: number) => {
    try {
      await adminAPI.deleteLexiconRow('phrase_map', aliasId);
      antdMessage.success('已删除');
      load();
    } catch {
      antdMessage.error('删除失败');
    }
  };

  const handleSearchSubmit = () => {
    setPage(1);
    setSearch(searchInput.trim());
  };

  return (
    <div className="flex flex-col h-full space-y-3">
      {/* 步骤 Phase Chips 过滤 */}
      <div className="flex items-center justify-between gap-2 flex-wrap p-2 rounded-xl border bg-bg-subtle border-border-theme">
        <div className="flex items-center gap-1.5 flex-wrap">
          {STEPS.map((s) => (
            <button
              key={s.key}
              title={s.hint}
              onClick={() => { setStep(s.key); setPage(1); }}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all border cursor-pointer ${
                step === s.key
                  ? 'bg-brand-color text-white border-brand-color shadow-xs'
                  : 'bg-bg-card text-text-secondary hover:bg-bg-subtle border-border-theme'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* 工具栏 */}
        <div className="flex items-center gap-2">
          <Select
            size="small"
            className="w-24 text-xs"
            value={modality || 'ALL'}
            onChange={(v) => { setModality(v === 'ALL' ? '' : v); setPage(1); }}
          >
            {['ALL', 'CT', 'MR', 'US', 'DR', 'RF', 'MG', 'SPECT', 'DSA'].map((m) => (
              <Select.Option key={m} value={m}>{m}</Select.Option>
            ))}
          </Select>
          <span className="text-xs text-text-secondary font-normal">共 {total} 组</span>
          <Input
            prefix={<Search className="w-3.5 h-3.5 text-text-secondary mr-1" />}
            placeholder="搜索别名或目标词..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onPressEnter={handleSearchSubmit}
            className="w-44 text-xs h-8"
            allowClear
          />

          <Button size="small" type="primary" icon={<Plus className="w-3.5 h-3.5" />} onClick={() => openNewForGroup()}>
            新增映射
          </Button>
          <Button size="small" icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />} onClick={load} />
        </div>
      </div>

      {/* 别名卡片列表 */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {loading ? (
          <div className="py-20 text-center text-text-secondary"><Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />别名映射加载中...</div>
        ) : groups.length === 0 ? (
          <div className="py-20 text-center text-text-secondary text-sm">暂无别名映射条目</div>
        ) : (
          groups.map((g, idx) => (
            <div key={idx} className="p-4 rounded-xl border shadow-xs hover:border-brand-color transition-colors bg-bg-card border-border-theme">
              <div className="flex items-center justify-between border-b pb-2 mb-3 border-border-theme">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-text-secondary">标准词:</span>
                  <Tag color="blue" className="text-xs font-bold px-2 py-0.5 m-0">{g.dst_word}</Tag>
                  <Tag className="text-[10px] m-0">{g.modality || 'ALL 模态'}</Tag>
                  <span className="text-[11px] font-normal text-text-secondary">包含 {g.aliases.length} 个别名词汇</span>
                </div>
                <Button size="small" type="text" className="text-brand-color text-xs flex items-center gap-1" onClick={() => openNewForGroup(g)}>
                  <Plus className="w-3.5 h-3.5" /> 添加新别名
                </Button>
              </div>

              {/* 映射 Tag 列表 */}
              <div className="flex items-center gap-2 flex-wrap">
                {g.aliases.map((a) => (
                  <div key={a.id} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs group hover:border-brand-color transition-colors bg-bg-subtle border-border-theme">
                    <span className="font-medium text-text-primary">{a.src_word}</span>
                    <ArrowRight className="w-3 h-3 text-blue-500" />
                    <span className="font-semibold text-brand-color">{g.dst_word}</span>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-1">
                      <Pencil className="w-3 h-3 text-text-secondary hover:text-brand-color cursor-pointer" onClick={() => openEditAlias(g, a)} />
                      <Trash2 className="w-3 h-3 text-text-secondary hover:text-red-500 cursor-pointer" onClick={() => handleDeleteAlias(a.id)} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>


      {/* 右侧 Drawer 快捷编辑 */}
      <Drawer
        title={edit?.mode === 'new' ? '新增别名映射' : '编辑别名映射'}
        placement="right"
        width={380}
        onClose={closeEdit}
        open={!!edit}
        extra={
          <Button type="primary" onClick={handleSave} size="small">保存映射</Button>
        }
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold mb-1">源别名 (src_word)*</label>
            <Input value={form.src_word} onChange={(e) => setForm({ ...form, src_word: e.target.value })} placeholder="例如: 肺平扫" />
          </div>
          <div>
            <label className="block font-semibold mb-1">归一目标标准词 (dst_word)*</label>
            <Input value={form.dst_word} onChange={(e) => setForm({ ...form, dst_word: e.target.value })} placeholder="例如: 胸部平扫" />
          </div>
          <div>
            <label className="block font-semibold mb-1">映射流水线阶段 (step)</label>
            <Select className="w-full" value={form.step} onChange={(v) => setForm({ ...form, step: v })}>
              {STEPS.map((s) => (
                <Select.Option key={s.key} value={s.key}>{s.label} ({s.hint})</Select.Option>
              ))}
            </Select>
          </div>
          <div>
            <label className="block font-semibold mb-1">适用检查模态 (modality)</label>
            <Select className="w-full" value={form.modality} onChange={(v) => setForm({ ...form, modality: v })}>
              {['ALL', 'CT', 'MR', 'US', 'DR', 'RF', 'MG', 'SPECT', 'DSA'].map((m) => (
                <Select.Option key={m} value={m}>{m}</Select.Option>
              ))}
            </Select>
          </div>
        </div>
      </Drawer>
    </div>
  );
}
