import { useState, useEffect } from 'react';
import { Card, Table, Tag, Button, Input, Select, Space, message } from 'antd';
import { ExclamationCircleOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { adminAPI } from '../services/matchService';

/** 与后端 unmatched_registry 实际 reason_code 对齐 */
const REASON_META: Record<string, { label: string; color: string }> = {
  unmatchable_by_design: { label: '设计上不可匹配', color: 'default' },
  standard_lib_gap: { label: '标准库缺失', color: 'orange' },
  lexicon_gap: { label: '词库映射缺失', color: 'blue' },
  needs_manual: { label: '需人工审核', color: 'purple' },
  engine_error: { label: '引擎异常', color: 'red' },
};

export default function UnmatchedWorkbench() {
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [reasonCode, setReasonCode] = useState('');
  const [summary, setSummary] = useState<{ total: number; by_reason: { reason_code: string; count: number }[] }>({ total: 0, by_reason: [] });

  const loadSummary = async () => {
    try {
      const res: any = await adminAPI.getUnmatchedSummary();
      setSummary({ total: res.total ?? 0, by_reason: res.by_reason ?? [] });
    } catch {
      // 汇总失败不阻塞列表
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const res: any = await adminAPI.getUnmatchedList({
        page,
        page_size: 20,
        search: search || undefined,
        reason_code: reasonCode || undefined,
      });
      setRows(res.data ?? []);
      setTotal(res.total ?? 0);
    } catch {
      message.error('加载未匹配记录失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  useEffect(() => {
    loadData();
  }, [page, search, reasonCode]);

  const markResolved = async (id: number) => {
    try {
      await adminAPI.updateUnmatchedStatus(id, 'resolved');
      message.success('已标记为解决');
      loadData();
      loadSummary();
    } catch {
      message.error('状态更新失败');
    }
  };

  const columns = [
    {
      title: '未匹配原始文本',
      dataIndex: 'procedure_name',
      key: 'procedure_name',
      render: (text: string, record: any) => (
        <div>
          <div className="font-bold text-text-primary">{text || `procedure_id=${record.procedure_id}`}</div>
          {record.detail && <div className="text-xs text-text-secondary mt-0.5">{record.detail}</div>}
        </div>
      ),
    },
    {
      title: '检查模态',
      dataIndex: 'modality',
      key: 'modality',
      render: (mod: string) => <Tag color="blue" className="font-bold m-0">{mod || '通用'}</Tag>,
    },
    {
      title: '诊断分类原因',
      dataIndex: 'reason_code',
      key: 'reason_code',
      render: (code: string) => {
        const item = REASON_META[code] || { label: code || '未知原因', color: 'default' };
        return <Tag color={item.color} className="m-0 font-medium">{item.label}</Tag>;
      },
    },
    {
      title: '登记时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (ts: string) => <span className="text-xs text-text-secondary">{ts ? ts.slice(0, 10) : '-'}</span>,
    },
    {
      title: '工单状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'resolved' ? 'green' : 'gold'} className="m-0 font-semibold">
          {status === 'resolved' ? '已治理解决' : '待治理处理'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space size="small">
          {record.status !== 'resolved' && (
            <Button size="small" type="link" className="text-brand-color font-semibold" onClick={() => markResolved(record.id)}>
              标记已解决
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b pb-3 gap-3 border-border-theme">
        <div>
          <h2 className="text-xl font-bold tracking-tight flex items-center gap-2 m-0 text-text-primary">
            <ExclamationCircleOutlined className="text-amber-500" />
            未匹配问题治理工作台
          </h2>
          <p className="text-xs mt-1 m-0 text-text-secondary">归集临床未精准命中标准库的原始请求描述，按未匹配归因进行针对性词库治理</p>
        </div>
        <Button icon={<ReloadOutlined />} onClick={() => { loadData(); loadSummary(); }} size="small">
          刷新列表
        </Button>
      </div>

      {/* 归因汇总 */}
      <div className="flex flex-wrap gap-2">
        {summary.by_reason.map((item) => {
          const meta = REASON_META[item.reason_code] || { label: item.reason_code, color: 'default' };
          return (
            <Tag key={item.reason_code} color={meta.color} className="m-0 px-3 py-1 text-xs font-medium">
              {meta.label}: {item.count}
            </Tag>
          );
        })}
      </div>

      {/* 搜索与卡片表格 */}
      <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <Input
              prefix={<SearchOutlined className="text-text-secondary mr-1" />}
              placeholder="搜索未匹配描述..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="w-64 text-xs h-9"
              allowClear
            />
            <Select
              className="w-44 text-xs h-9"
              value={reasonCode || 'ALL'}
              onChange={(val) => { setReasonCode(val === 'ALL' ? '' : val); setPage(1); }}
            >
              <Select.Option value="ALL">全部诊断类型</Select.Option>
              <Select.Option value="lexicon_gap">词库映射缺失</Select.Option>
              <Select.Option value="standard_lib_gap">标准库缺失</Select.Option>
              <Select.Option value="unmatchable_by_design">设计上不可匹配</Select.Option>
              <Select.Option value="needs_manual">需人工审核</Select.Option>
              <Select.Option value="engine_error">引擎异常</Select.Option>
            </Select>
          </div>
          <span className="text-xs text-text-secondary">待处理工单: {total} 件</span>
        </div>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={rows}
          loading={loading}
          pagination={{
            current: page,
            pageSize: 20,
            total: total,
            onChange: setPage,
          }}
        />
      </Card>
    </div>
  );
}
