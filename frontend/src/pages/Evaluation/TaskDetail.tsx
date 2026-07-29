import React, { useEffect, useState } from 'react';
import { Card, Descriptions, Table, Tag, Tabs, Statistic, Row, Col, Button, message, Spin } from 'antd';
import { ArrowLeftOutlined, ReloadOutlined } from '@ant-design/icons';
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
      });
      setFailures(response.cases);
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

  useEffect(() => {
    loadTask();
    loadFailures();
    loadFailureStats();
  }, [taskId]);

  if (loading || !task) {
    return (
      <div className="flex justify-center items-center h-screen">
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
          <div className="text-xs text-gray-400 dark:text-gray-500">{record.expected_code}</div>
          <div className="text-gray-900 dark:text-gray-100">{record.expected_name}</div>
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
            <div className="text-xs text-gray-400 dark:text-gray-500">{record.actual_code}</div>
            <div className="text-gray-900 dark:text-gray-100">{record.actual_name}</div>
          </div>
        ) : (
          <span className="text-gray-500 dark:text-gray-400">(未匹配)</span>
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
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/evaluation')}
          >
            返回
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{task.name}</h1>
            <p className="text-gray-600 dark:text-gray-300">{task.description}</p>
          </div>
        </div>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => {
            loadTask();
            loadFailures(failurePagination.current, failurePagination.pageSize);
          }}
        >
          刷新
        </Button>
      </div>

      {/* 任务基本信息 */}
      <Card title="任务信息" className="mb-6">
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
        <Row gutter={16} className="mb-6">
          <Col span={6}>
            <Card>
              <Statistic
                title="匹配率"
                value={task.match_rate?.toFixed(2)}
                suffix="%"
                valueStyle={{ color: (task.match_rate || 0) >= 85 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="准确率"
                value={task.accuracy?.toFixed(2)}
                suffix="%"
                valueStyle={{ color: (task.accuracy || 0) >= 90 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="F1分数"
                value={task.f1_score?.toFixed(2)}
                valueStyle={{ color: (task.f1_score || 0) >= 80 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均响应时间"
                value={task.avg_response_time?.toFixed(2)}
                suffix="ms"
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 失败案例 */}
      <Card>
        <Tabs defaultActiveKey="cases">
          <TabPane tab={`失败案例 (${failuresTotal})`} key="cases">
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
            <div className="grid grid-cols-3 gap-4">
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
                  <Card key={reason}>
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
        </Tabs>
      </Card>
    </div>
  );
};

export default TaskDetail;
