import React, { useState } from 'react';
import { Card, Form, Input, InputNumber, Select, Button, message, Upload } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
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
      const task = await evaluationAPI.createTask({
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
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">创建评测任务</h1>
        <p className="text-gray-600">配置测试参数并创建新的评测任务</p>
      </div>

      <Card>
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
            label="任务名称"
            name="name"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="例如：CT项目匹配测试" />
          </Form.Item>

          <Form.Item label="任务描述" name="description">
            <TextArea
              rows={3}
              placeholder="描述本次评测的目的和范围"
            />
          </Form.Item>

          <Form.Item
            label="测试文件路径"
            name="test_file_path"
            rules={[{ required: true, message: '请输入测试文件路径' }]}
            extra="CSV 格式，包含 check_item, modality, expected_standard_code, expected_standard_name 列"
          >
            <Input placeholder="tests/benchmark/16zzy_ct_115k.csv" />
          </Form.Item>

          <Form.Item
            label="采样数量"
            name="sample_size"
            extra="留空则使用全部数据"
          >
            <InputNumber
              min={1}
              max={100000}
              placeholder="100"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item
            label="模态过滤"
            name="modality"
            extra="仅测试指定模态的数据，留空则测试所有模态"
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

          <Form.Item label="创建人" name="created_by">
            <Input placeholder="你的名字" />
          </Form.Item>

          <Form.Item>
            <div className="flex gap-4">
              <Button type="primary" htmlType="submit" loading={loading}>
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
