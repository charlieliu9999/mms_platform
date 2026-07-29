import React, { useEffect, useState } from 'react';
import { Card, Statistic, Table, Button, Tag, Space, Modal, message, Spin, Progress } from 'antd';
import { ReloadOutlined, PlayCircleOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { evaluationAPI, EvalTask } from '../../services/evaluationService';

const EvaluationDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<EvalTask[]>([]);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });

  // 加载任务列表
  const loadTasks = async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const response = await evaluationAPI.listTasks({
        limit: pageSize,
        offset: (page - 1) * pageSize,
      });
      setTasks(response.tasks);
      setTotal(response.total);
      setPagination({ current: page, pageSize });
    } catch (error) {
      message.error('加载任务列表失败');
      console.error('Load tasks error:', error);
    } finally {
      setLoading(false);
    }
  };

  // 启动评测
  const handleStart = async (taskId: number) => {
    try {
      await evaluationAPI.startEvaluation(taskId);
      message.success('评测已启动');
      // 开始轮询进度
      pollTaskProgress(taskId);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '启动评测失败');
      console.error('Start evaluation error:', error);
    }
  };

  // 轮询任务进度
  const pollTaskProgress = async (taskId: number) => {
    const timer = setInterval(async () => {
      try {
        const task = await evaluationAPI.getTask(taskId);

        // 更新任务列表中的对应项
        setTasks(prev =>
          prev.map(t => t.id === taskId ? task : t)
        );

        // 如果完成或失败，停止轮询
        if (task.status === 'completed' || task.status === 'failed') {
          clearInterval(timer);
          if (task.status === 'completed') {
            message.success(`任务 ${task.name} 已完成`);
          } else {
            message.error(`任务 ${task.name} 执行失败`);
          }
        }
      } catch (error) {
        clearInterval(timer);
        console.error('Poll task error:', error);
      }
    }, 2000); // 每2秒轮询一次

    // 最多轮询5分钟
    setTimeout(() => clearInterval(timer), 300000);
  };

  // 删除任务
  const handleDelete = (taskId: number, taskName: string) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除任务 "${taskName}" 吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await evaluationAPI.deleteTask(taskId);
          message.success('任务已删除');
          loadTasks(pagination.current, pagination.pageSize);
        } catch (error: any) {
          message.error(error.response?.data?.detail || '删除失败');
        }
      },
    });
  };

  // 查看详情
  const handleViewDetails = (taskId: number) => {
    navigate(`/evaluation/tasks/${taskId}`);
  };

  // 初始加载
  useEffect(() => {
    loadTasks();
  }, []);

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

  // 表格列定义
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string, record: EvalTask) => (
        <Space direction="vertical" size="small">
          {getStatusTag(status)}
          {status === 'running' && (
            <Progress percent={record.progress} size="small" />
          )}
        </Space>
      ),
    },
    {
      title: '测试数量',
      dataIndex: 'total_count',
      key: 'total_count',
      width: 100,
      render: (count: number) => count || '-',
    },
    {
      title: '匹配率',
      dataIndex: 'match_rate',
      key: 'match_rate',
      width: 100,
      render: (rate: number | undefined) =>
        rate !== undefined ? `${rate.toFixed(2)}%` : '-',
    },
    {
      title: '准确率',
      dataIndex: 'accuracy',
      key: 'accuracy',
      width: 100,
      render: (accuracy: number | undefined) =>
        accuracy !== undefined ? `${accuracy.toFixed(2)}%` : '-',
    },
    {
      title: 'F1分数',
      dataIndex: 'f1_score',
      key: 'f1_score',
      width: 100,
      render: (f1: number | undefined) =>
        f1 !== undefined ? f1.toFixed(2) : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: any, record: EvalTask) => (
        <Space>
          {record.status === 'pending' && (
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleStart(record.id)}
            >
              启动
            </Button>
          )}
          {record.status === 'completed' && (
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetails(record.id)}
            >
              详情
            </Button>
          )}
          {(record.status === 'completed' || record.status === 'failed') && (
            <Button
              danger
              size="small"
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.id, record.name)}
            >
              删除
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // 计算总览统计
  const stats = {
    total: total,
    completed: tasks.filter(t => t.status === 'completed').length,
    running: tasks.filter(t => t.status === 'running').length,
    pending: tasks.filter(t => t.status === 'pending').length,
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">评测系统</h1>
        <p className="text-gray-600">批量测试匹配引擎性能，分析失败原因，优化词表</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <Card>
          <Statistic title="总任务数" value={stats.total} />
        </Card>
        <Card>
          <Statistic
            title="已完成"
            value={stats.completed}
            valueStyle={{ color: '#3f8600' }}
          />
        </Card>
        <Card>
          <Statistic
            title="执行中"
            value={stats.running}
            valueStyle={{ color: '#1890ff' }}
          />
        </Card>
        <Card>
          <Statistic
            title="待执行"
            value={stats.pending}
            valueStyle={{ color: '#999' }}
          />
        </Card>
      </div>

      {/* 任务列表 */}
      <Card
        title="评测任务"
        extra={
          <Space>
            <Button
              type="primary"
              onClick={() => navigate('/evaluation/create')}
            >
              创建任务
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => loadTasks(pagination.current, pagination.pageSize)}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => loadTasks(page, pageSize),
          }}
        />
      </Card>
    </div>
  );
};

export default EvaluationDashboard;
