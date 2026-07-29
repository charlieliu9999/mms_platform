import { useCallback, useEffect, useState } from 'react';
import { message as antdMessage, Drawer, Button, Input, Select, Tag, Popconfirm } from 'antd';
import { Loader2, Plus, RefreshCw, Search, Trash2, Pencil } from 'lucide-react';
import { adminAPI } from '../services/matchService';

const TYPES: { key: string; label: string; hint: string }[] = [
  { key: 'body', label: '解剖部位', hint: '身体部位词' },
  { key: 'scan', label: '扫描方式', hint: 'CT/MR/DR 通用扫描方式' },
  { key: 'post', label: '后处理', hint: 'CTA/MRA/3D 等后处理' },
  { key: 'position', label: '体位摆位', hint: '正位/侧位/斜位 等' },
  { key: 'device', label: '设备类别', hint: '设备类别词' },
  { key: 'mgscan', label: 'MG 扫描', hint: '钼靶专用扫描方式' },
  { key: 'rfscan', label: 'RF 扫描', hint: '透视专用扫描方式' },
  { key: 'scope', label: '范围词', hint: '标准范围（基础/超声/核医学）' },
  { key: 'other', label: '其他分词', hint: '其他未分类词' },
];

type Row = { id: number; word: string; type: string; enable: number };

export function MedicalDictView() {
  const [activeType, setActiveType] = useState('body');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [rows, setRows] = useState<Row[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);


  // 抽屉编辑状态
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
      setRows(res.data ?? []);
      setTotal(res.total ?? 0);
    } catch {
      antdMessage.error('加载词典失败');
    } finally {
      setLoading(false);
    }
  }, [activeType, search, page]);

  useEffect(() => { load(); }, [load]);

  const openNew = () => {
    setEdit({ mode: 'new' });
    setForm({ word: '', type: activeType, enable: 0 });
  };
  const openEdit = (row: Row) => {
    setEdit({ mode: 'edit', row });
    setForm({ word: row.word, type: row.type, enable: row.enable });
  };
  const closeEdit = () => setEdit(null);

  const handleSave = async () => {
    if (!form.word.trim()) {
      antdMessage.warning('请输入词语');
      return;
    }
    try {
      const payload = { word: form.word.trim(), type: form.type, enable: Number(form.enable) };
      if (edit?.mode === 'new') {
        await adminAPI.createLexiconRow('medical_dict', payload);
        antdMessage.success('已新增词条');
      } else if (edit?.row) {
        await adminAPI.updateLexiconRow('medical_dict', edit.row.id, payload);
        antdMessage.success('已更新词条');
      }
      closeEdit();
      load();
    } catch {
      antdMessage.error('保存失败');
    }
  };

  const handleDelete = async (row: Row) => {
    try {
      await adminAPI.deleteLexiconRow('medical_dict', row.id);
      antdMessage.success('已停用词条');
      load();
    } catch {
      antdMessage.error('停用失败');
    }
  };

  const handleSearchSubmit = () => {
    setPage(1);
    setSearch(searchInput.trim());
  };

  return (
    <div className="flex flex-col h-full space-y-3">
      {/* 词典类型 Type Filter Chips & Header Controls */}
      <div className="flex items-center justify-between gap-2 flex-wrap bg-zinc-50 dark:bg-zinc-800/40 p-2 rounded-xl border border-zinc-200/60 dark:border-zinc-800">
        <div className="flex items-center gap-1.5 flex-wrap">
          {TYPES.map((t) => (
            <button
              key={t.key}
              title={t.hint}
              onClick={() => { setActiveType(t.key); setPage(1); }}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                activeType === t.key
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-white dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-700 border border-zinc-200 dark:border-zinc-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-400 font-normal">共 {total} 项</span>
          <Input
            prefix={<Search className="w-3.5 h-3.5 text-zinc-400" />}
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
          <div className="py-20 text-center text-zinc-400"><Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />词典数据加载中...</div>
        ) : rows.length === 0 ? (
          <div className="py-20 text-center text-zinc-400 text-sm">该分类下暂无分词词条</div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
            {rows.map((row) => (
              <div
                key={row.id}
                className="p-2.5 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 shadow-xs flex items-center justify-between group hover:border-blue-300 dark:hover:border-blue-800 transition-colors"
              >
                <div className="min-w-0 pr-1">
                  <div className="text-xs font-bold text-zinc-800 dark:text-zinc-200 truncate">{row.word}</div>
                  <Tag className="text-[9px] m-0 px-1 py-0 border-0 bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
                    {row.type}
                  </Tag>
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Pencil className="w-3 h-3 text-zinc-400 hover:text-blue-600 cursor-pointer" onClick={() => openEdit(row)} />
                  <Popconfirm title="确定停用该词条？" onConfirm={() => handleDelete(row)} okText="确认" cancelText="取消">
                    <Trash2 className="w-3 h-3 text-zinc-400 hover:text-red-600 cursor-pointer" />
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
            <label className="block font-semibold mb-1">医学分词 (word)*</label>
            <Input value={form.word} onChange={(e) => setForm({ ...form, word: e.target.value })} placeholder="例如: 冠状动脉" />
          </div>
          <div>
            <label className="block font-semibold mb-1">词典分类 (type)*</label>
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
