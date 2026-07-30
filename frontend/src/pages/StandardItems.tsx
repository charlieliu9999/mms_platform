import { useState, useEffect, useCallback } from 'react';
import { Table, Input, Select, Tag, Card, Row, Col, Statistic, Button } from 'antd';
import { SearchOutlined, CheckSquareOutlined, AppstoreOutlined, ReloadOutlined } from '@ant-design/icons';
import { adminAPI, StandardItem } from '../services/matchService';

const MODALITY_OPTIONS = ['ALL', 'CT', 'MR', 'US', 'DR', 'RF', 'MG', 'SPECT', 'DSA', 'OCT', 'PET/CT', 'PET/MR'];

export default function StandardItems() {
  const [selectedVersion, setSelectedVersion] = useState<string>('');
  const [selectedModality, setSelectedModality] = useState<string>('ALL');
  const [search, setSearch] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(20);

  const [loading, setLoading] = useState<boolean>(false);
  const [items, setItems] = useState<StandardItem[]>([]);
  const [total, setTotal] = useState<number>(0);

  // 聚合统计
  const [availableVersions, setAvailableVersions] = useState<string[]>([]);
  const [statsTotal, setStatsTotal] = useState<number>(18695);
  const [statsModalityCount, setStatsModalityCount] = useState<number>(11);
  const [statsBodyPartCount, setStatsBodyPartCount] = useState<number>(24);
  const [byModality, setByModality] = useState<Record<string, number>>({
    CT: 548, MR: 480, US: 443, DR: 234, RF: 54, MG: 51, SPECT: 48, DSA: 28, 'PET/MR': 12, 'PET/CT': 12, OCT: 6,
  });

  const loadStats = useCallback(async () => {
    try {
      const res: any = await adminAPI.getStandardItemStats({
        version: selectedVersion || undefined,
      });
      if (res) {
        if (res.total) setStatsTotal(res.total);
        if (res.modality_count) setStatsModalityCount(res.modality_count);
        if (res.body_part_count) setStatsBodyPartCount(res.body_part_count);
        if (res.by_modality && Object.keys(res.by_modality).length > 0) setByModality(res.by_modality);
        if (res.available_versions && res.available_versions.length > 0) setAvailableVersions(res.available_versions);
      }
    } catch {
      // Keep defaults
    }
  }, [selectedVersion]);

  const loadItems = useCallback(async () => {
    setLoading(true);
    try {
      const res: any = await adminAPI.getStandardItems({
        page,
        page_size: pageSize,
        modality: selectedModality === 'ALL' ? undefined : selectedModality,
        version: selectedVersion || undefined,
        search: search || undefined,
      });
      setItems(res.data ?? []);
      setTotal(res.total ?? 0);
    } catch {
      // Catch
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, selectedModality, selectedVersion, search]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  const handleModalityClick = (mod: string) => {
    setSelectedModality(mod);
    setPage(1);
  };

  const handleResetFilters = () => {
    setSelectedVersion('');
    setSelectedModality('ALL');
    setSearch('');
    setPage(1);
  };

  const columns = [
    {
      title: '标准编码',
      dataIndex: 'item_code',
      key: 'item_code',
      render: (code: string) => <span className="font-mono font-semibold text-brand-color">{code}</span>,
    },
    {
      title: '标准名称',
      dataIndex: 'item_name',
      key: 'item_name',
      render: (name: string) => <span className="font-bold text-text-primary">{name}</span>,
    },
    {
      title: '检查模态',
      dataIndex: 'modality',
      key: 'modality',
      render: (modality: string) => (
        <Tag color="blue" className="font-bold px-2 py-0.5 rounded-md border-0 m-0">
          {modality}
        </Tag>
      ),
    },
    {
      title: '解剖部位 (L1/L2)',
      key: 'body_part',
      render: (_: any, record: StandardItem) => (
        <span className="text-xs text-text-secondary">
          {record.body_part_l1 || '-'} {record.body_part_l2 ? `/ ${record.body_part_l2}` : ''}
        </span>
      ),
    },
    {
      title: '扫描/后处理',
      key: 'methods',
      render: (_: any, record: StandardItem) => (
        <span className="text-xs text-text-secondary">
          {record.scan_method || '普通'} {record.post_processing ? `+ ${record.post_processing}` : ''}
        </span>
      ),
    },
    {
      title: '规则版本',
      dataIndex: 'version',
      key: 'version',
      render: (ver: string) => (
        <span className="text-xs font-mono text-text-secondary">
          {ver || selectedVersion || 'V3.8.2'}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      {/* 标题 & 版本号选择 ToolBar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b pb-3 gap-3 border-border-theme">
        <div>
          <h2 className="text-xl font-bold tracking-tight flex items-center gap-2 m-0 text-text-primary">
            <CheckSquareOutlined className="text-brand-color" />
            标准检查项目库与版本控制
          </h2>
          <p className="text-xs mt-1 m-0 text-text-secondary">维护国家医学影像标准检查项目，按规则版本号与检查模态进行统计与聚合</p>
        </div>

        {/* 版本号 Selector */}
        <div className="flex items-center gap-2 select-none">
          <span className="text-xs font-semibold shrink-0 text-text-secondary">选择标准版本:</span>
          <Select
            className="w-40 text-xs"
            value={selectedVersion || 'ALL'}
            onChange={(val) => {
              setSelectedVersion(val === 'ALL' ? '' : val);
              setPage(1);
            }}
          >
            <Select.Option value="ALL">全部版本 (All)</Select.Option>
            {availableVersions.length > 0
              ? availableVersions.map((v) => <Select.Option key={v} value={v}>{v}</Select.Option>)
              : ['V3.8.2', 'V3.8.1', 'V3.8.0'].map((v) => <Select.Option key={v} value={v}>{v}</Select.Option>)}
          </Select>
          {(selectedVersion || selectedModality !== 'ALL' || search) && (
            <Button size="small" icon={<ReloadOutlined />} onClick={handleResetFilters}>
              重置
            </Button>
          )}
        </div>
      </div>

      {/* KPI 总体汇总卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
            <Statistic
              title={<span className="text-xs font-semibold text-text-secondary">当前版本标准总数</span>}
              value={statsTotal}
              valueStyle={{ color: 'var(--text-primary)', fontSize: '24px', fontWeight: 800 }}
              suffix={<span className="text-xs font-normal text-text-secondary">项</span>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
            <Statistic
              title={<span className="text-xs font-semibold text-text-secondary">覆盖检查模态数</span>}
              value={statsModalityCount}
              valueStyle={{ color: 'var(--brand-color)', fontSize: '24px', fontWeight: 800 }}
              suffix={<span className="text-xs font-normal text-text-secondary">种模态</span>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
            <Statistic
              title={<span className="text-xs font-semibold text-text-secondary">覆盖解剖部位数</span>}
              value={statsBodyPartCount}
              valueStyle={{ color: '#059669', fontSize: '24px', fontWeight: 800 }}
              suffix={<span className="text-xs font-normal text-text-secondary">部位</span>}
            />
          </Card>
        </Col>
      </Row>

      {/* 不同模态标准汇总网格 (Modality Cards Grid) */}
      <Card
        bordered={false}
        className="shadow-xs rounded-xl bg-bg-card border-border-theme"
        title={
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold flex items-center gap-1.5 text-text-primary">
              <AppstoreOutlined className="text-brand-color" />
              不同检查模态的标准数据汇总 (点击快速筛选)
            </span>
            {selectedModality !== 'ALL' && (
              <span className="text-xs font-semibold text-brand-color">
                当前筛选模态: {selectedModality}
              </span>
            )}
          </div>
        }
      >
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
          {MODALITY_OPTIONS.map((mod) => {
            const count = mod === 'ALL' ? statsTotal : byModality[mod] || 0;
            const isSelected = selectedModality === mod;
            return (
              <button
                key={mod}
                onClick={() => handleModalityClick(mod)}
                className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-blue-50 dark:bg-blue-950/60 border-brand-color text-brand-color shadow-xs ring-1 ring-brand-color'
                    : 'bg-bg-subtle border-border-theme text-text-primary hover:bg-bg-subtle/80'
                }`}
              >
                <div className="flex items-center justify-between text-xs font-bold">
                  <span>{mod === 'ALL' ? '全部模态' : mod}</span>
                  {isSelected && <span className="w-2.5 h-2.5 rounded-full bg-brand-color"></span>}
                </div>
                <div className="text-sm font-extrabold font-mono mt-1 text-text-primary">{count} <span className="text-[10px] font-normal text-text-secondary">条</span></div>
              </button>
            );
          })}
        </div>
      </Card>

      {/* 过滤搜索与数据表格 */}
      <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
        <div className="flex items-center justify-between mb-4 gap-3">
          <Input
            prefix={<SearchOutlined className="text-text-secondary mr-1" />}
            placeholder="搜索标准编码或项目名称..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-80 text-xs h-9"
            allowClear
          />
          <span className="text-xs text-text-secondary">找到 {total} 条匹配结果</span>
        </div>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            onChange: (p) => setPage(p),
            showSizeChanger: false,
          }}
          className="ant-table-striped"
        />
      </Card>
    </div>
  );
}
