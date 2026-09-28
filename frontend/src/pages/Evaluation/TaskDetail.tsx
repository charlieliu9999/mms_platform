import React, { useEffect, useState } from 'react';
import { Card, Descriptions, Table, Tag, Tabs, Statistic, Row, Col, Button, message, Spin, Select, Input } from 'antd';
import { ArrowLeftOutlined, ReloadOutlined, FilterOutlined, ClearOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { evaluationAPI, EvalTask, FailureCase } from '../../services/evaluationService';

const { TabPane } = Tabs;

const TaskDetail: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [task, setTask] = useState<EvalTask | null>(null);
  const [failures, setFailures] = useState<FailureCase[]>([]);
  const [failureStats, setFailureStats] = useState<Record<string, number>>({});
  const [failuresTotal, setFailuresTotal] = useState(0);
  const [failurePagination, setFailurePagination] = useState({ current: 1, pageSize: 20 });

  // 详细分析数据
  const [modalityPerformance, setModalityPerformance] = useState<any[]>([]);
  const [frequentFailures, setFrequentFailures] = useState<any[]>([]);

  // 筛选器状态
  const [filters, setFilters] = useState({
    failure_reason: undefined as string | undefined,
    modality: undefined as string | undefined,
    search: '' as string,
  });

  // 加载任务详情
  const loadTask = async () => {
    if (!taskId) return;
    setLoading(true);
    try {
      const data = await evaluationAPI.getTask(Number(taskId));
      setTask(data);
    } catch (error) {
      message.error('加载任务详情失败');
      console.error('Load task error:', error);
    } finally {
      setLoading(false);
    }
  };

  // 加载失败案例
  const loadFailures = async (page = 1, pageSize = 20) => {
    if (!taskId) return;
    try {
      const response = await evaluationAPI.getFailures(Number(taskId), {
        limit: pageSize,
        offset: (page - 1) * pageSize,
        failure_reason: filters.failure_reason,
      });

      // 在前端进行额外筛选（模态和搜索）
      let filteredCases = response.cases;

      if (filters.modality) {
        filteredCases = filteredCases.filter(c => c.modality === filters.modality);
      }

      if (filters.search.trim()) {
        const searchLower = filters.search.toLowerCase();
        filteredCases = filteredCases.filter(c =>
          c.check_item?.toLowerCase().includes(searchLower) ||
          c.expected_name?.toLowerCase().includes(searchLower) ||
          c.actual_name?.toLowerCase().includes(searchLower)
        );
      }

      setFailures(filteredCases);
      setFailuresTotal(response.total);
      setFailurePagination({ current: page, pageSize });
    } catch (error) {
      message.error('加载失败案例失败');
      console.error('Load failures error:', error);
    }
  };

  // 加载失败统计
  const loadFailureStats = async () => {
    if (!taskId) return;
    try {
      const response = await evaluationAPI.getFailureStats(Number(taskId));
      setFailureStats(response.stats);
    } catch (error) {
      console.error('Load failure stats error:', error);
    }
  };

  // 加载详细分析数据
  const loadDetailedAnalysis = async () => {
    if (!taskId) return;
    try {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api';
      const response = await fetch(`${apiBaseUrl}/evaluation/tasks/${taskId}/analysis`);
      const data = await response.json();
      setModalityPerformance(data.modality_performance || []);
      setFrequentFailures(data.frequent_failures || []);
    } catch (error) {
      console.error('Load detailed analysis error:', error);
    }
  };

  useEffect(() => {
    loadTask();
    loadFailures();
    loadFailureStats();
    loadDetailedAnalysis();
  }, [taskId]);

  // 监听筛选条件变化
  useEffect(() => {
    if (taskId) {
      loadFailures(1, failurePagination.pageSize);
    }
  }, [filters]);

  if (loading || !task) {
    return (
      <div className="flex justify-center items-center h-48">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  // 失败案例表格列
  const failureColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '原始项目',
      dataIndex: 'check_item',
      key: 'check_item',
      ellipsis: true,
      width: 300,
      render: (text: string) => <span className="font-bold text-text-primary">{text}</span>,
    },
    {
      title: '模态',
      dataIndex: 'modality',
      key: 'modality',
      width: 80,
    },
    {
      title: '期望结果',
      key: 'expected',
      width: 200,
      render: (_: any, record: FailureCase) => (
        <div>
          <div className="text-xs text-text-secondary">{record.expected_code}</div>
          <div className="text-text-primary font-bold text-xs">{record.expected_name}</div>
        </div>
      ),
    },
    {
      title: '实际结果',
      key: 'actual',
      width: 200,
      render: (_: any, record: FailureCase) =>
        record.actual_name ? (
          <div>
            <div className="text-xs text-text-secondary">{record.actual_code}</div>
            <div className="text-text-primary font-bold text-xs">{record.actual_name}</div>
          </div>
        ) : (
          <span className="text-text-secondary">(未匹配)</span>
        ),
    },
    {
      title: '失败原因',
      dataIndex: 'failure_reason',
      key: 'failure_reason',
      width: 120,
      render: (reason: string) => {
        const reasonMap: Record<string, { color: string; text: string }> = {
          missing_word: { color: 'orange', text: '缺少词汇' },
          ambiguity: { color: 'purple', text: '存在歧义' },
          complex: { color: 'blue', text: '复杂表述' },
          algorithm: { color: 'red', text: '算法问题' },
          no_standard: { color: 'default', text: '无标准项' },
          wrong_match: { color: 'volcano', text: '错误匹配' },
        };
        const config = reasonMap[reason] || { color: 'default', text: reason };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
  ];

  // 状态标签
  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: '待执行' },
      running: { color: 'processing', text: '执行中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
    };
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b pb-3 gap-3 border-border-theme">
        <div className="flex items-center gap-3">
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/evaluation')}
            size="small"
          >
            返回
          </Button>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-text-primary m-0">{task.name}</h2>
            <p className="text-xs mt-1 m-0 text-text-secondary">{task.description}</p>
          </div>
        </div>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => {
            loadTask();
            loadFailures(failurePagination.current, failurePagination.pageSize);
          }}
          size="small"
        >
          刷新
        </Button>
      </div>

      {/* 任务基本信息 */}
      <Card title="任务信息" bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
        <Descriptions column={3}>
          <Descriptions.Item label="任务ID">{task.id}</Descriptions.Item>
          <Descriptions.Item label="状态">{getStatusTag(task.status)}</Descriptions.Item>
          <Descriptions.Item label="进度">{task.progress}%</Descriptions.Item>
          <Descriptions.Item label="测试总数">{task.total_count}</Descriptions.Item>
          <Descriptions.Item label="匹配数量">{task.matched_count}</Descriptions.Item>
          <Descriptions.Item label="正确数量">{task.correct_count}</Descriptions.Item>
          <Descriptions.Item label="错误数量">{task.wrong_count}</Descriptions.Item>
          <Descriptions.Item label="未匹配数">{task.no_match_count}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {task.created_at ? new Date(task.created_at).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 核心指标 */}
      {task.status === 'completed' && (
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
              <Statistic
                title="匹配率"
                value={task.match_rate || 0}
                suffix="%"
                valueStyle={{ color: (task.match_rate || 0) >= 85 ? '#10b981' : '#f59e0b', fontWeight: 800 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
              <Statistic
                title="准确率"
                value={task.accuracy || 0}
                suffix="%"
                valueStyle={{ color: (task.accuracy || 0) >= 90 ? '#10b981' : '#f59e0b', fontWeight: 800 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
              <Statistic
                title="F1分数"
                value={task.f1_score}
                valueStyle={{ color: (task.f1_score || 0) >= 0.80 ? '#10b981' : '#f59e0b', fontWeight: 800 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
              <Statistic
                title="平均响应时间"
                value={task.avg_response_time}
                suffix="ms"
                valueStyle={{ fontWeight: 800 }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 失败案例 */}
      <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
        <Tabs defaultActiveKey="cases">
          <TabPane tab={`失败案例 (${failuresTotal})`} key="cases">
            {/* 筛选器 */}
            <div className="mb-4 p-3 rounded-lg bg-bg-subtle border border-border-theme">
              <div className="flex items-center gap-3 flex-wrap">
                <div className="flex items-center gap-2">
                  <FilterOutlined className="text-text-secondary" />
                  <span className="text-xs font-semibold text-text-secondary">筛选条件：</span>
                </div>

                <Select
                  placeholder="失败原因"
                  allowClear
                  className="w-32 text-xs"
                  size="small"
                  value={filters.failure_reason}
                  onChange={(value) => setFilters({ ...filters, failure_reason: value })}
                >
                  <Select.Option value="missing_word">缺少词汇</Select.Option>
                  <Select.Option value="ambiguity">存在歧义</Select.Option>
                  <Select.Option value="complex">复杂表述</Select.Option>
                  <Select.Option value="algorithm">算法问题</Select.Option>
                  <Select.Option value="no_standard">无标准项</Select.Option>
                  <Select.Option value="wrong_match">错误匹配</Select.Option>
                </Select>

                <Select
                  placeholder="模态"
                  allowClear
                  className="w-24 text-xs"
                  size="small"
                  value={filters.modality}
                  onChange={(value) => setFilters({ ...filters, modality: value })}
                >
                  <Select.Option value="CT">CT</Select.Option>
                  <Select.Option value="MR">MR</Select.Option>
                  <Select.Option value="DR">DR</Select.Option>
                  <Select.Option value="US">US</Select.Option>
                  <Select.Option value="DSA">DSA</Select.Option>
                  <Select.Option value="PET">PET</Select.Option>
                  <Select.Option value="SPECT">SPECT</Select.Option>
                </Select>

                <Input
                  placeholder="搜索项目名称..."
                  allowClear
                  className="w-48 text-xs"
                  size="small"
                  value={filters.search}
                  onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                />

                <Button
                  size="small"
                  icon={<ClearOutlined />}
                  onClick={() => {
                    setFilters({ failure_reason: undefined, modality: undefined, search: '' });
                  }}
                  className="text-xs"
                >
                  清空筛选
                </Button>

                <span className="ml-auto text-xs text-text-secondary">
                  显示 {failures.length} / {failuresTotal} 条
                </span>
              </div>
            </div>

            <Table
              columns={failureColumns}
              dataSource={failures}
              rowKey="id"
              pagination={{
                current: failurePagination.current,
                pageSize: failurePagination.pageSize,
                total: failuresTotal,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条`,
                onChange: (page, pageSize) => loadFailures(page, pageSize),
              }}
            />
          </TabPane>
          <TabPane tab="失败原因统计" key="stats">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {Object.entries(failureStats).map(([reason, count]) => {
                const reasonMap: Record<string, string> = {
                  missing_word: '缺少词汇',
                  ambiguity: '存在歧义',
                  complex: '复杂表述',
                  algorithm: '算法问题',
                  no_standard: '无标准项',
                  wrong_match: '错误匹配',
                };
                return (
                  <Card key={reason} bordered={false} className="bg-bg-subtle border border-border-theme">
                    <Statistic
                      title={reasonMap[reason] || reason}
                      value={count}
                      suffix="条"
                    />
                  </Card>
                );
              })}
            </div>
          </TabPane>
          <TabPane tab="详细分析" key="analysis">
            {/* 各模态匹配表现 */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold mb-3 text-text-primary">各模态匹配表现</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="bg-bg-subtle">
                      <th className="px-3 py-2 text-left border border-border-theme">模态</th>
                      <th className="px-3 py-2 text-right border border-border-theme">测试总数</th>
                      <th className="px-3 py-2 text-right border border-border-theme">匹配数</th>
                      <th className="px-3 py-2 text-right border border-border-theme">正确数</th>
                      <th className="px-3 py-2 text-right border border-border-theme">未匹配</th>
                      <th className="px-3 py-2 text-right border border-border-theme">匹配率</th>
                      <th className="px-3 py-2 text-right border border-border-theme">准确率</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modalityPerformance.map((stat: any) => (
                      <tr key={stat.modality} className="hover:bg-bg-subtle/50">
                        <td className="px-3 py-2 border border-border-theme font-semibold">{stat.modality}</td>
                        <td className="px-3 py-2 text-right border border-border-theme">{stat.total}</td>
                        <td className="px-3 py-2 text-right border border-border-theme">{stat.matched}</td>
                        <td className="px-3 py-2 text-right border border-border-theme">{stat.correct}</td>
                        <td className="px-3 py-2 text-right border border-border-theme text-text-secondary">{stat.no_match}</td>
                        <td className="px-3 py-2 text-right border border-border-theme">
                          <span className={stat.match_rate >= 85 ? 'text-green-600 font-semibold' : stat.match_rate >= 60 ? 'text-yellow-600' : 'text-red-600'}>
                            {stat.match_rate}%
                          </span>
                        </td>
                        <td className="px-3 py-2 text-right border border-border-theme">
                          <span className={stat.accuracy >= 95 ? 'text-green-600 font-semibold' : stat.accuracy >= 85 ? 'text-yellow-600' : 'text-red-600'}>
                            {stat.accuracy}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 高频失败项目 */}
            <div>
              <h3 className="text-sm font-semibold mb-3 text-text-primary">高频未匹配项目（出现≥2次）</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="bg-bg-subtle">
                      <th className="px-3 py-2 text-left border border-border-theme">序号</th>
                      <th className="px-3 py-2 text-left border border-border-theme">项目名称</th>
                      <th className="px-3 py-2 text-left border border-border-theme">模态</th>
                      <th className="px-3 py-2 text-right border border-border-theme">出现次数</th>
                    </tr>
                  </thead>
                  <tbody>
                    {frequentFailures.slice(0, 30).map((item: any, index: number) => (
                      <tr key={index} className="hover:bg-bg-subtle/50">
                        <td className="px-3 py-2 border border-border-theme text-text-secondary">{index + 1}</td>
                        <td className="px-3 py-2 border border-border-theme">{item.check_item}</td>
                        <td className="px-3 py-2 border border-border-theme">
                          <Tag className="text-xs">{item.modality}</Tag>
                        </td>
                        <td className="px-3 py-2 text-right border border-border-theme font-semibold text-red-600">{item.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {frequentFailures.length > 30 && (
                  <div className="mt-2 text-xs text-text-secondary text-center">
                    还有 {frequentFailures.length - 30} 个项目未显示
                  </div>
                )}
              </div>
            </div>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default TaskDetail;
