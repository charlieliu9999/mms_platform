import React, { useState } from 'react';
import { Card, Form, Input, InputNumber, Select, Button, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import { evaluationAPI } from '../../services/evaluationService';

const { Option } = Select;
const { TextArea } = Input;

const CreateTask: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      await evaluationAPI.createTask({
        name: values.name,
        description: values.description,
        test_file_path: values.test_file_path,
        sample_size: values.sample_size,
        modality: values.modality,
        created_by: values.created_by || 'web_user',
      });

      message.success('任务创建成功');
      navigate(`/evaluation`);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '创建任务失败');
      console.error('Create task error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b pb-3 border-border-theme">
        <h2 className="text-xl font-bold tracking-tight text-text-primary m-0">创建评测任务</h2>
        <p className="text-xs mt-1 m-0 text-text-secondary">配置测试参数并创建新的自动化规则评测任务</p>
      </div>

      <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            sample_size: 100,
            modality: undefined,
          }}
        >
          <Form.Item
            label={<span className="text-xs font-semibold text-text-primary">任务名称</span>}
            name="name"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="例如：CT项目匹配测试" />
          </Form.Item>

          <Form.Item label={<span className="text-xs font-semibold text-text-primary">任务描述</span>} name="description">
            <TextArea
              rows={3}
              placeholder="描述本次评测的目的和范围"
            />
          </Form.Item>

          <Form.Item
            label={<span className="text-xs font-semibold text-text-primary">测试文件路径</span>}
            name="test_file_path"
            rules={[{ required: true, message: '请输入测试文件路径' }]}
            extra={<span className="text-[11px] text-text-secondary">CSV 格式，包含 check_item, modality, expected_standard_code, expected_standard_name 列</span>}
          >
            <Input placeholder="tests/benchmark/16zzy_ct_115k.csv" />
          </Form.Item>

          <Form.Item
            label={<span className="text-xs font-semibold text-text-primary">采样数量</span>}
            name="sample_size"
            extra={<span className="text-[11px] text-text-secondary">留空则使用全部数据</span>}
          >
            <InputNumber
              min={1}
              max={100000}
              placeholder="100"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item
            label={<span className="text-xs font-semibold text-text-primary">模态过滤</span>}
            name="modality"
            extra={<span className="text-[11px] text-text-secondary">仅测试指定模态的数据，留空则测试所有模态</span>}
          >
            <Select placeholder="选择模态" allowClear>
              <Option value="CT">CT</Option>
              <Option value="DR">DR</Option>
              <Option value="MR">MR</Option>
              <Option value="US">US</Option>
              <Option value="RF">RF</Option>
              <Option value="MG">MG</Option>
            </Select>
          </Form.Item>

          <Form.Item label={<span className="text-xs font-semibold text-text-primary">创建人</span>} name="created_by">
            <Input placeholder="你的名字" />
          </Form.Item>

          <Form.Item className="mb-0 pt-2">
            <div className="flex gap-3">
              <Button type="primary" htmlType="submit" loading={loading} className="font-bold">
                创建任务
              </Button>
              <Button onClick={() => navigate('/evaluation')}>
                取消
              </Button>
            </div>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default CreateTask;
