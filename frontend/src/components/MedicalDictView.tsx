import { useEffect, useState } from 'react';
import { Tag, Popconfirm, Drawer, Input, Select, Button, message } from 'antd';
import { Pencil, Trash2, Plus, RefreshCw, Search, Loader2 } from 'lucide-react';
import { adminAPI, MedicalDictItem } from '../services/matchService';

const TYPES = [
  { key: 'body', label: '解剖部位', hint: '如: 头部、胸部、膝关节' },
  { key: 'scan', label: '扫描方式', hint: '如: 平扫、增强、HRCT' },
  { key: 'post', label: '后处理', hint: '如: 重建、三维重建、MIP' },
  { key: 'position', label: '体位摆位', hint: '如: 正侧位、轴位、双乳' },
  { key: 'device', label: '设备类别', hint: '如: 高分辨率、双源' },
  { key: 'scope', label: '范围词', hint: '如: 全程、局部、全脑' },
  { key: 'mgscan', label: 'MG扫描', hint: '乳腺钼靶专有扫描词' },
  { key: 'rfscan', label: 'RF扫描', hint: '造影专有扫描词' },
  { key: 'other', label: '其他通用', hint: '非以上类别的通用匹配词' },
];

export function MedicalDictView() {
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<MedicalDictItem[]>([]);
  const [total, setTotal] = useState(0);

  // 搜索和分类
  const [activeType, setActiveType] = useState('body');
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);

  // 编辑抽屉状态
  const [edit, setEdit] = useState<{ mode: 'new' | 'edit'; record?: MedicalDictItem } | null>(null);
  const [form, setForm] = useState({ word: '', type: 'body', modality: '通用', enable: 1 });

  const load = async () => {
    setLoading(true);
    try {
      const res: any = await adminAPI.getLexiconRows('medical_dict', {
        page,
        page_size: 36,
        type: activeType,
        search: searchQuery || undefined,
      });
      setRows(res.data ?? []);
      setTotal(res.total ?? 0);
    } catch {
      message.error('加载分词词典数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [page, activeType, searchQuery]);

  const handleSearchSubmit = () => {
    setSearchQuery(searchInput.trim());
    setPage(1);
  };

  const openNew = () => {
    setForm({ word: '', type: activeType, modality: '通用', enable: 1 });
    setEdit({ mode: 'new' });
  };

  const openEdit = (record: MedicalDictItem) => {
    setForm({
      word: record.word,
      type: record.type,
      modality: record.modality || '通用',
      enable: record.enable,
    });
    setEdit({ mode: 'edit', record });
  };

  const closeEdit = () => {
    setEdit(null);
  };

  const handleSave = async () => {
    if (!form.word.trim()) {
      message.warning('请输入词条文本');
      return;
    }
    try {
      if (edit?.mode === 'new') {
        await adminAPI.createLexiconRow('medical_dict', form);
        message.success('已成功新增词条');
      } else if (edit?.mode === 'edit' && edit.record) {
        await adminAPI.updateLexiconRow('medical_dict', edit.record.id, form);
        message.success('词条已更新');
      }
      closeEdit();
      load();
    } catch {
      message.error('保存失败');
    }
  };

  const handleDelete = async (record: MedicalDictItem) => {
    try {
      await adminAPI.deleteLexiconRow('medical_dict', record.id);
      message.success('词条已物理删除/停用');
      load();
    } catch {
      message.error('删除操作失败');
    }
  };

  return (
    <div className="flex flex-col h-full space-y-3">
      {/* 词典类型 Type Filter Chips & Header Controls */}
      <div className="flex items-center justify-between gap-2 flex-wrap p-2 rounded-xl border bg-bg-subtle border-border-theme">
        <div className="flex items-center gap-1.5 flex-wrap">
          {TYPES.map((t) => (
            <button
              key={t.key}
              title={t.hint}
              onClick={() => { setActiveType(t.key); setPage(1); }}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all border cursor-pointer ${
                activeType === t.key
                  ? 'bg-brand-color text-white border-brand-color shadow-xs'
                  : 'bg-bg-card text-text-secondary hover:bg-bg-subtle border-border-theme'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-normal text-text-secondary">共 {total} 项</span>
          <Input
            prefix={<Search className="w-3.5 h-3.5 text-text-secondary mr-1" />}
            placeholder="搜索词条..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onPressEnter={handleSearchSubmit}
            className="w-44 text-xs h-8"
            allowClear
          />

          <Button size="small" type="primary" icon={<Plus className="w-3.5 h-3.5" />} onClick={openNew}>
            新增词条
          </Button>
          <Button size="small" icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />} onClick={load} />
        </div>
      </div>

      {/* 词条网格列表 (Grid Layout) */}
      <div className="flex-1 overflow-y-auto pr-1">
        {loading ? (
          <div className="py-20 text-center text-text-secondary"><Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />词典数据加载中...</div>
        ) : rows.length === 0 ? (
          <div className="py-20 text-center text-sm text-text-secondary">该分类下暂无分词词条</div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
            {rows.map((row) => (
              <div
                key={row.id}
                className="p-2.5 rounded-xl border shadow-xs flex items-center justify-between group hover:border-brand-color transition-colors bg-bg-card border-border-theme"
              >
                <div className="min-w-0 pr-1">
                  <div className="text-xs font-bold truncate text-text-primary">{row.word}</div>
                  <Tag className="text-[9px] m-0 px-1 py-0 border-0 bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
                    {row.type}
                  </Tag>
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Pencil className="w-3 h-3 text-text-secondary hover:text-brand-color cursor-pointer" onClick={() => openEdit(row)} />
                  <Popconfirm title="确定停用该词条？" onConfirm={() => handleDelete(row)} okText="确认" cancelText="取消">
                    <Trash2 className="w-3 h-3 text-text-secondary hover:text-red-500 cursor-pointer" />
                  </Popconfirm>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 侧边 Drawer 编辑 */}
      <Drawer
        title={edit?.mode === 'new' ? '新增分词词条' : '编辑分词词条'}
        placement="right"
        width={340}
        onClose={closeEdit}
        open={!!edit}
        extra={<Button type="primary" onClick={handleSave} size="small">保存</Button>}
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold mb-1 text-text-primary">医学分词 (word)*</label>
            <Input value={form.word} onChange={(e) => setForm({ ...form, word: e.target.value })} placeholder="例如: 冠状动脉" />
          </div>
          <div>
            <label className="block font-semibold mb-1 text-text-primary">词典分类 (type)*</label>
            <Select className="w-full" value={form.type} onChange={(v) => setForm({ ...form, type: v })}>
              {TYPES.map((t) => (
                <Select.Option key={t.key} value={t.key}>{t.label} ({t.key})</Select.Option>
              ))}
            </Select>
          </div>
        </div>
      </Drawer>
    </div>
  );
}
