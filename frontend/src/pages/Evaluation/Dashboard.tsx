import React, { useEffect, useState } from 'react';
import { Card, Statistic, Table, Button, Tag, Space, Modal, message, Progress } from 'antd';
import { ReloadOutlined, PlayCircleOutlined, DeleteOutlined, EyeOutlined, ExperimentOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { evaluationAPI, EvalTask } from '../../services/evaluationService';

const EvaluationDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<EvalTask[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const res = await evaluationAPI.listTasks();
      setTasks(res.tasks || []);
    } catch {
      message.error('获取评测任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const handleRunTask = async (taskId: number) => {
    try {
      message.info('开始执行评测任务...');
      await evaluationAPI.startEvaluation(taskId);
      message.success('评测任务已提交后台执行');
      fetchTasks();
    } catch {
      message.error('启动评测任务失败');
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除该评测任务吗？相关的结果数据也将被删除。',
      okText: '确认',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          await evaluationAPI.deleteTask(taskId);
          message.success('已删除评测任务');
          fetchTasks();
        } catch {
          message.error('删除评测任务失败');
        }
      },
    });
  };

  const totalTasks = tasks.length;
  const completedTasks = tasks.filter(t => t.status === 'completed').length;
  const avgAccuracy = tasks.reduce((sum, t) => sum + (t.accuracy || 0), 0) / (completedTasks || 1);

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: EvalTask) => (
        <div>
          <a
            onClick={() => navigate(`/evaluation/tasks/${record.id}`)}
            className="font-bold hover:underline text-xs text-brand-color"
          >
            {text}
          </a>
          <div className="text-[11px] mt-0.5 text-text-secondary">{record.description || '无描述'}</div>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          completed: 'success',
          failed: 'error',
        };
        return <Tag color={colorMap[status] || 'default'} className="m-0 font-bold">{status}</Tag>;
      },
    },
    {
      title: '准确率 (Accuracy)',
      dataIndex: 'accuracy',
      key: 'accuracy',
      render: (val: number | null, record: EvalTask) => {
        if (record.status !== 'completed' || val === null) return <span className="text-xs text-text-secondary">-</span>;
        const pct = Math.round(val * 100);
        return (
          <div className="flex items-center gap-2 w-32">
            <Progress percent={pct} size="small" strokeColor={pct >= 80 ? '#10b981' : '#f59e0b'} />
          </div>
        );
      },
    },
    {
      title: '样本数',
      dataIndex: 'total_samples',
      key: 'total_samples',
      render: (val: number) => <span className="font-mono text-xs text-text-secondary">{val || 0}</span>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (val: string) => <span className="text-xs text-text-secondary">{val ? new Date(val).toLocaleDateString() : '-'}</span>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: EvalTask) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/evaluation/tasks/${record.id}`)}
          >
            详情
          </Button>
          <Button
            type="text"
            size="small"
            icon={<PlayCircleOutlined className="text-brand-color" />}
            onClick={() => handleRunTask(record.id)}
            disabled={record.status === 'running'}
          >
            运行
          </Button>
          <Button
            type="text"
            danger
            size="small"
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteTask(record.id)}
          />
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b pb-3 gap-3 border-border-theme">
        <div>
          <h2 className="text-xl font-bold tracking-tight flex items-center gap-2 m-0 text-text-primary">
            <ExperimentOutlined className="text-brand-color" />
            医学匹配规则批量评测系统
          </h2>
          <p className="text-xs mt-1 m-0 text-text-secondary">创建自动化回归评测任务，针对黄金标注集测试标准化引擎的命中率与准确率</p>
        </div>
        <div className="flex items-center gap-2">
          <Button type="primary" onClick={() => navigate('/evaluation/create')} size="small">
            + 创建新评测任务
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchTasks} size="small" />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
          <Statistic title={<span className="text-xs font-semibold text-text-secondary">总评测任务数</span>} value={totalTasks} />
        </Card>
        <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
          <Statistic title={<span className="text-xs font-semibold text-text-secondary">已完成评测任务</span>} value={completedTasks} valueStyle={{ color: '#10b981' }} />
        </Card>
        <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
          <Statistic title={<span className="text-xs font-semibold text-text-secondary font-mono">平均准确率</span>} value={Math.round(avgAccuracy * 100)} suffix="%" valueStyle={{ color: 'var(--brand-color)' }} />
        </Card>
      </div>

      <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
        <Table rowKey="id" columns={columns} dataSource={tasks} loading={loading} />
      </Card>
    </div>
  );
};

export default EvaluationDashboard;
