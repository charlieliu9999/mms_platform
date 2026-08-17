import React, { useState, useEffect } from 'react';
import { Card, Tabs, Table, Tag, Button, Space, Statistic, Row, Col, Input, Select, message, Drawer, Descriptions, Empty, Badge, Tooltip } from 'antd';
import {
  FileTextOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
  EyeOutlined,
  HistoryOutlined,
  BulbOutlined,
  ExperimentOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { adminAPI } from '../services/matchService';
import type {
  TechnicalDetailLibraryItem,
  TechnicalDetailLibraryStats,
  TechnicalDetailCandidateSummary,
  TechnicalDetailStats,
  TechnicalDetailStatus,
} from '../services/matchService';

const { TabPane } = Tabs;
const { Search } = Input;

// 技术细节库页面
const TechnicalDetailLibrary: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<TechnicalDetailLibraryStats | null>(null);
  const [data, setData] = useState<TechnicalDetailLibraryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ page: 1, pageSize: 20 });
  const [filters, setFilters] = useState<{ modality?: string; search?: string; is_active?: boolean }>({});
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedItem, setSelectedItem] = useState<TechnicalDetailLibraryItem | null>(null);

  useEffect(() => {
    loadStats();
    loadData();
  }, [pagination, filters]);

  const loadStats = async () => {
    try {
      const result = await adminAPI.getTechnicalDetailLibraryStats();
      setStats(result);
    } catch (error) {
      message.error('加载统计数据失败');
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const { items, total: totalCount } = await adminAPI.getTechnicalDetailLibrary({
        ...filters,
        limit: pagination.pageSize,
        offset: (pagination.page - 1) * pagination.pageSize,
      });
      setData(items);
      setTotal(totalCount);
    } catch (error) {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetail = async (id: number) => {
    try {
      const item = await adminAPI.getTechnicalDetailLibraryItem(id);
      setSelectedItem(item);
      setDetailVisible(true);
    } catch (error) {
      message.error('加载详情失败');
    }
  };

  const columns: ColumnsType<TechnicalDetailLibraryItem> = [
    {
      title: '项目信息',
      key: 'item_info',
      width: 300,
      fixed: 'left',
      render: (_, record) => (
        <div>
          <div className="font-semibold text-blue-600 mb-1">{record.item_name}</div>
          <div className="text-xs text-gray-500">
            <Tag color="blue" className="mr-1">{record.modality}</Tag>
            <span>{record.item_code}</span>
          </div>
        </div>
      ),
    },
    {
      title: '技术参数',
      key: 'technical',
      width: 350,
      ellipsis: true,
      render: (_, record) => (
        <div className="space-y-1">
          {record.scan_method && (
            <div className="text-sm">
              <span className="text-gray-500">扫描方法：</span>
              <span className="text-gray-800">{record.scan_method}</span>
            </div>
          )}
          {record.contrast_agent && (
            <div className="text-sm">
              <span className="text-gray-500">对比剂：</span>
              <span className="text-gray-800">{record.contrast_agent}</span>
            </div>
          )}
          {record.body_position && (
            <div className="text-sm">
              <span className="text-gray-500">体位：</span>
              <span className="text-gray-800">{record.body_position}</span>
            </div>
          )}
        </div>
      ),
    },
    {
      title: '数据来源',
      dataIndex: 'sources',
      width: 200,
      render: (sources: any[]) => (
        <div className="space-y-1">
          {sources?.slice(0, 2).map((s, i) => (
            <Tag key={i} color="green" className="text-xs">
              {s.source_label}
            </Tag>
          ))}
          {sources?.length > 2 && (
            <Tooltip title={sources.slice(2).map(s => s.source_label).join(', ')}>
              <Tag className="text-xs cursor-pointer">+{sources.length - 2} 更多</Tag>
            </Tooltip>
          )}
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 100,
      align: 'center',
      render: (active) => (
        <Badge
          status={active ? 'success' : 'default'}
          text={active ? '启用' : '停用'}
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      fixed: 'right',
      align: 'center',
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record.id)}
        >
          查看详情
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16}>
          <Col span={6}>
            <Card className="shadow-sm hover:shadow-md transition-shadow">
              <Statistic
                title="总计"
                value={stats.total}
                prefix={<DatabaseOutlined className="text-blue-500" />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card className="shadow-sm hover:shadow-md transition-shadow">
              <Statistic
                title="启用中"
                value={stats.active_total}
                prefix={<CheckCircleOutlined className="text-green-500" />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card className="shadow-sm hover:shadow-md transition-shadow">
              <Statistic
                title="CT 项目"
                value={stats.ct_total}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card className="shadow-sm hover:shadow-md transition-shadow">
              <Statistic
                title="MR 项目"
                value={stats.mr_total}
                valueStyle={{ color: '#eb2f96' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 筛选工具栏 */}
      <Card className="shadow-sm">
        <div className="flex items-center justify-between">
          <Space size="middle">
            <Select
              placeholder="选择模态"
              style={{ width: 120 }}
              allowClear
              suffixIcon={<FilterOutlined />}
              onChange={(value) => setFilters({ ...filters, modality: value })}
            >
              <Select.Option value="CT">CT</Select.Option>
              <Select.Option value="MR">MR</Select.Option>
            </Select>
            <Select
              placeholder="状态"
              style={{ width: 120 }}
              allowClear
              onChange={(value) => setFilters({ ...filters, is_active: value })}
            >
              <Select.Option value={true}>启用</Select.Option>
              <Select.Option value={false}>停用</Select.Option>
            </Select>
            <Search
              placeholder="搜索项目名称或编码"
              style={{ width: 300 }}
              onSearch={(value) => setFilters({ ...filters, search: value })}
              enterButton={<SearchOutlined />}
              allowClear
            />
          </Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => loadData()}
          >
            刷新
          </Button>
        </div>
      </Card>

      {/* 数据表格 */}
      <Card className="shadow-sm">
        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey="id"
          scroll={{ x: 1200 }}
          pagination={{
            current: pagination.page,
            pageSize: pagination.pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
            onChange: (page, pageSize) => setPagination({ page, pageSize }),
          }}
        />
      </Card>

      {/* 详情抽屉 */}
      <Drawer
        title={
          <div className="flex items-center">
            <FileTextOutlined className="mr-2 text-blue-500" />
            <span className="font-bold">技术细节详情</span>
          </div>
        }
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
        width={720}
      >
        {selectedItem && (
          <div className="space-y-6">
            {/* 基本信息 */}
            <Card
              title={<span className="text-sm font-semibold">📋 基本信息</span>}
              size="small"
              className="shadow-sm"
            >
              <Descriptions column={2} size="small">
                <Descriptions.Item label="项目编码">{selectedItem.item_code}</Descriptions.Item>
                <Descriptions.Item label="版本">{selectedItem.version}</Descriptions.Item>
                <Descriptions.Item label="项目名称" span={2}>
                  <span className="font-semibold text-lg">{selectedItem.item_name}</span>
                </Descriptions.Item>
                <Descriptions.Item label="模态">
                  <Tag color="blue">{selectedItem.modality}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Badge
                    status={selectedItem.is_active ? 'success' : 'default'}
                    text={selectedItem.is_active ? '启用' : '停用'}
                  />
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* 技术参数 */}
            <Card
              title={
                <span className="text-sm font-semibold">
                  ⚡ 技术参数
                </span>
              }
              size="small"
              className="shadow-sm"
            >
              <div className="space-y-3">
                {selectedItem.scan_method && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">扫描方法</div>
                    <div className="font-medium text-gray-800">{selectedItem.scan_method}</div>
                  </div>
                )}
                {selectedItem.scan_method_detail && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">扫描方法详情</div>
                    <div className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                      {selectedItem.scan_method_detail}
                    </div>
                  </div>
                )}
                {selectedItem.body_position && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">扫描体位</div>
                    <div className="text-gray-700 leading-relaxed">{selectedItem.body_position}</div>
                  </div>
                )}
                {selectedItem.scan_scope && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">扫描范围</div>
                    <div className="text-gray-700">{selectedItem.scan_scope}</div>
                  </div>
                )}
                {selectedItem.contrast_agent && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">对比剂方案</div>
                    <div className="text-gray-700">{selectedItem.contrast_agent}</div>
                  </div>
                )}
                {selectedItem.post_processing && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">后处理</div>
                    <div className="text-gray-700">{selectedItem.post_processing}</div>
                  </div>
                )}
                {selectedItem.image_region && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">成像区域</div>
                    <div className="text-gray-700">{selectedItem.image_region}</div>
                  </div>
                )}
                {selectedItem.image_focus && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">成像关注点</div>
                    <div className="text-gray-700">{selectedItem.image_focus}</div>
                  </div>
                )}
                {selectedItem.scan_param && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">扫描参数</div>
                    <div className="text-gray-700">{selectedItem.scan_param}</div>
                  </div>
                )}
                {selectedItem.coil && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">线圈（MR）</div>
                    <div className="text-gray-700">{selectedItem.coil}</div>
                  </div>
                )}
                {selectedItem.base_sequence && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">基础序列（MR）</div>
                    <div className="text-gray-700">{selectedItem.base_sequence}</div>
                  </div>
                )}
                {selectedItem.compose_sequence && (
                  <div className="pb-3">
                    <div className="text-xs text-gray-500 mb-1">组合序列（MR）</div>
                    <div className="text-gray-700">{selectedItem.compose_sequence}</div>
                  </div>
                )}
              </div>
            </Card>

            {/* 临床应用 */}
            <Card
              title={
                <span className="text-sm font-semibold">
                  🩺 临床应用
                </span>
              }
              size="small"
              className="shadow-sm"
            >
              <div className="space-y-3">
                {selectedItem.clinical_indication && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">临床适应症</div>
                    <div className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                      {selectedItem.clinical_indication}
                    </div>
                  </div>
                )}
                {selectedItem.clinical_significance && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">临床意义</div>
                    <div className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                      {selectedItem.clinical_significance}
                    </div>
                  </div>
                )}
                {selectedItem.organs && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">器官</div>
                    <div className="text-gray-700">{selectedItem.organs}</div>
                  </div>
                )}
                {selectedItem.anatomical_structure && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">解剖结构</div>
                    <div className="text-gray-700">{selectedItem.anatomical_structure}</div>
                  </div>
                )}
                {selectedItem.technical_notes && (
                  <div className="border-b pb-3">
                    <div className="text-xs text-gray-500 mb-1">技术备注</div>
                    <div className="text-gray-600">{selectedItem.technical_notes}</div>
                  </div>
                )}
                <div className="flex gap-4">
                  {selectedItem.image_grade && (
                    <div>
                      <div className="text-xs text-gray-500 mb-1">图像等级</div>
                      <Tag color="purple">{selectedItem.image_grade}</Tag>
                    </div>
                  )}
                  {selectedItem.image_score !== null && selectedItem.image_score !== undefined && (
                    <div>
                      <div className="text-xs text-gray-500 mb-1">图像评分</div>
                      <Tag color="orange">{selectedItem.image_score} 分</Tag>
                    </div>
                  )}
                </div>
              </div>
            </Card>

            {/* 数据来源 */}
            <Card
              title={
                <span className="text-sm font-semibold">
                  <HistoryOutlined className="mr-1" />
                  数据来源
                </span>
              }
              size="small"
              className="shadow-sm"
            >
              {selectedItem.sources && selectedItem.sources.length > 0 ? (
                <div className="space-y-2">
                  {selectedItem.sources.map((source, idx) => (
                    <div key={idx} className="flex items-start p-2 bg-gray-50 rounded">
                      <Tag color="green" className="mt-1">{source.source_label}</Tag>
                      <div className="flex-1 text-sm text-gray-600">
                        <div>{source.source_table}</div>
                        {source.source_notes && (
                          <div className="text-xs text-gray-500 mt-1">{source.source_notes}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty description="暂无来源信息" />
              )}
            </Card>
          </div>
        )}
      </Drawer>
    </div>
  );
};

// 候选管理页面
const TechnicalDetailCandidates: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<TechnicalDetailStats | null>(null);
  const [data, setData] = useState<TechnicalDetailCandidateSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ page: 1, pageSize: 20 });
  const [filters, setFilters] = useState<{ status?: TechnicalDetailStatus; modality?: string; search?: string }>({});

  useEffect(() => {
    loadStats();
    loadData();
  }, [pagination, filters]);

  const loadStats = async () => {
    try {
      const result = await adminAPI.getTechnicalDetailStats();
      setStats(result);
    } catch (error) {
      message.error('加载统计数据失败');
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const { items, total: totalCount } = await adminAPI.getTechnicalDetailCandidates({
        ...filters,
        limit: pagination.pageSize,
        offset: (pagination.page - 1) * pagination.pageSize,
      });
      setData(items);
      setTotal(totalCount);
    } catch (error) {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const getStatusConfig = (status: TechnicalDetailStatus) => {
    const configs = {
      pending_review: {
        color: 'warning',
        icon: <ClockCircleOutlined />,
        text: '待审核',
        badgeStatus: 'warning' as const
      },
      approved: {
        color: 'success',
        icon: <CheckCircleOutlined />,
        text: '已批准',
        badgeStatus: 'success' as const
      },
      rejected: {
        color: 'error',
        icon: <CloseCircleOutlined />,
        text: '已拒绝',
        badgeStatus: 'error' as const
      },
      applied: {
        color: 'processing',
        icon: <CheckCircleOutlined />,
        text: '已应用',
        badgeStatus: 'processing' as const
      },
      superseded: {
        color: 'default',
        icon: null,
        text: '已过期',
        badgeStatus: 'default' as const
      },
    };
    return configs[status];
  };

  const columns: ColumnsType<TechnicalDetailCandidateSummary> = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      render: (id) => <span className="font-mono text-xs text-gray-500">#{id}</span>,
    },
    {
      title: '目标项目',
      key: 'target',
      width: 280,
      render: (_, record) => (
        <div>
          <div className="font-medium text-gray-800">{record.target_item_name}</div>
          <div className="text-xs text-gray-500 mt-1">
            <Tag color="blue" className="text-xs">{record.modality}</Tag>
            <span>{record.target_item_code}</span>
          </div>
        </div>
      ),
    },
    {
      title: '生成方法',
      dataIndex: 'generation_method',
      width: 150,
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <Tag icon={<BulbOutlined />} color="cyan" className="text-xs">
            {text}
          </Tag>
        </Tooltip>
      ),
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      width: 100,
      align: 'center',
      render: (value) => {
        const percent = (value * 100).toFixed(1);
        const color = value >= 0.8 ? 'green' : value >= 0.6 ? 'orange' : 'red';
        return <Tag color={color}>{percent}%</Tag>;
      },
    },
    {
      title: '冲突',
      dataIndex: 'conflicts_json',
      width: 80,
      align: 'center',
      render: (conflicts) =>
        conflicts?.length > 0 ? (
          <Tooltip title={`${conflicts.length} 个字段冲突`}>
            <Tag color="warning">{conflicts.length}</Tag>
          </Tooltip>
        ) : (
          <span className="text-gray-400">-</span>
        ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 120,
      align: 'center',
      render: (status) => {
        const config = getStatusConfig(status);
        return <Badge status={config.badgeStatus} text={config.text} />;
      },
    },
    {
      title: '审核人',
      dataIndex: 'reviewer',
      width: 100,
      ellipsis: true,
      render: (reviewer) => reviewer || <span className="text-gray-400">-</span>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 160,
      render: (text) => (
        <span className="text-xs text-gray-500">
          {text?.substring(0, 16).replace('T', ' ')}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16}>
          <Col span={6}>
            <Card className="shadow-sm hover:shadow-md transition-shadow">
              <Statistic
                title="总候选数"
                value={stats.total}
                prefix={<FileTextOutlined className="text-blue-500" />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card className="shadow-sm hover:shadow-md transition-shadow">
              <Statistic
                title="待审核"
                value={stats.by_status.pending_review || 0}
                prefix={<ClockCircleOutlined className="text-orange-500" />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card className="shadow-sm hover:shadow-md transition-shadow">
              <Statistic
                title="已批准"
                value={stats.by_status.approved || 0}
                prefix={<CheckCircleOutlined className="text-green-500" />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card className="shadow-sm hover:shadow-md transition-shadow">
              <Statistic
                title="冲突数"
                value={stats.conflict_count}
                prefix={<ExperimentOutlined className="text-red-500" />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 筛选工具栏 */}
      <Card className="shadow-sm">
        <div className="flex items-center justify-between">
          <Space size="middle">
            <Select
              placeholder="状态"
              style={{ width: 150 }}
              allowClear
              suffixIcon={<FilterOutlined />}
              onChange={(value) => setFilters({ ...filters, status: value })}
            >
              <Select.Option value="pending_review">待审核</Select.Option>
              <Select.Option value="approved">已批准</Select.Option>
              <Select.Option value="rejected">已拒绝</Select.Option>
              <Select.Option value="applied">已应用</Select.Option>
            </Select>
            <Select
              placeholder="模态"
              style={{ width: 120 }}
              allowClear
              onChange={(value) => setFilters({ ...filters, modality: value })}
            >
              <Select.Option value="CT">CT</Select.Option>
              <Select.Option value="MR">MR</Select.Option>
            </Select>
            <Search
              placeholder="搜索项目名称或编码"
              style={{ width: 300 }}
              onSearch={(value) => setFilters({ ...filters, search: value })}
              enterButton={<SearchOutlined />}
              allowClear
            />
          </Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => loadData()}
          >
            刷新
          </Button>
        </div>
      </Card>

      {/* 数据表格 */}
      <Card className="shadow-sm">
        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey="id"
          scroll={{ x: 1200 }}
          pagination={{
            current: pagination.page,
            pageSize: pagination.pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条候选`,
            onChange: (page, pageSize) => setPagination({ page, pageSize }),
          }}
        />
      </Card>
    </div>
  );
};

// 主组件
const TechnicalDetails: React.FC = () => {
  return (
    <div className="p-6">
      <Card
        title={
          <div className="flex items-center">
            <FileTextOutlined className="text-blue-500 text-xl mr-2" />
            <span className="font-bold text-lg">技术细节管理</span>
          </div>
        }
        extra={
          <Button type="primary" ghost href="/docs#/admin" target="_blank">
            API 文档
          </Button>
        }
        className="shadow-lg"
      >
        <Tabs defaultActiveKey="library" size="large">
          <TabPane
            tab={
              <span className="flex items-center">
                <DatabaseOutlined className="mr-1" />
                技术细节库
              </span>
            }
            key="library"
          >
            <TechnicalDetailLibrary />
          </TabPane>
          <TabPane
            tab={
              <span className="flex items-center">
                <FileTextOutlined className="mr-1" />
                候选管理
              </span>
            }
            key="candidates"
          >
            <TechnicalDetailCandidates />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default TechnicalDetails;
