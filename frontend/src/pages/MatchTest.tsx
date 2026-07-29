import React, { useState } from 'react';
import { Card, Form, Input, Button, Select, Tag } from 'antd';
import { SearchOutlined, CheckCircleOutlined, CloseCircleOutlined, ExperimentOutlined } from '@ant-design/icons';
import { matchAPI, MatchRequest, MatchResult } from '@/services/matchService';

const { Option } = Select;

const MatchTest: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MatchResult | null>(null);

  const handleMatch = async (values: MatchRequest) => {
    setLoading(true);
    try {
      const data = await matchAPI.matchOne(values);
      setResult(data);
    } catch (error) {
      console.error('Match failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight m-0">单项匹配测试</h1>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">实时模拟检验医学词典归一化、短语映射与消除歧义规则效果</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-400 text-xs font-medium border border-blue-200/60 dark:border-blue-800/40">
          <ExperimentOutlined /> 沙箱测试模式
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 左侧表单 */}
        <div className="lg:col-span-5">
          <Card
            bordered={false}
            className="bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 shadow-xs rounded-xl"
            title={<span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">输入待匹配文本</span>}
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleMatch}
              initialValues={{ modality: 'CT' }}
              className="space-y-4"
            >
              <Form.Item
                label={<span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">检查项目原始名称</span>}
                name="check_item"
                rules={[{ required: true, message: '请输入检查项目名称' }]}
              >
                <Input
                  placeholder="例如: 胸部CT平扫"
                  size="large"
                  className="rounded-lg text-sm"
                />
              </Form.Item>

              <Form.Item
                label={<span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">检查模态 (Modality)</span>}
                name="modality"
                rules={[{ required: true, message: '请选择检查模态' }]}
              >
                <Select size="large" className="rounded-lg">
                  <Option value="CT">CT - 电子计算机断层扫描</Option>
                  <Option value="MR">MR - 磁共振成像</Option>
                  <Option value="DR">DR - 数字化X射线摄影</Option>
                  <Option value="CR">CR - 计算机X射线摄影</Option>
                  <Option value="RF">RF - X线透视造影</Option>
                  <Option value="MG">MG - 乳腺钼靶摄影</Option>
                  <Option value="US">US - 电子超声检查</Option>
                  <Option value="SPECT">SPECT - 单光子发射断层</Option>
                  <Option value="PET">PET - 正电子发射断层</Option>
                </Select>
              </Form.Item>

              <Form.Item className="mb-0 pt-2">
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SearchOutlined />}
                  loading={loading}
                  size="large"
                  block
                  className="bg-blue-600 hover:bg-blue-700 font-medium rounded-lg h-11 border-none shadow-xs"
                >
                  运行算法匹配
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </div>

        {/* 右侧匹配诊断结果 */}
        <div className="lg:col-span-7">
          {result ? (
            <Card
              bordered={false}
              className="bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 shadow-xs rounded-xl h-full flex flex-col"
              title={<span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">引擎匹配分析结果</span>}
            >
              <div className="space-y-6">
                {/* 状态 Header */}
                <div className={`p-4 rounded-xl border flex items-center justify-between ${
                  result.matched
                    ? 'bg-emerald-50/60 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800/60'
                    : 'bg-rose-50/60 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800/60'
                }`}>
                  <div className="flex items-center gap-3">
                    {result.matched ? (
                      <CheckCircleOutlined className="text-2xl text-emerald-600 dark:text-emerald-400" />
                    ) : (
                      <CloseCircleOutlined className="text-2xl text-rose-600 dark:text-rose-400" />
                    )}
                    <div>
                      <h3 className={`text-base font-bold m-0 ${
                        result.matched ? 'text-emerald-900 dark:text-emerald-200' : 'text-rose-900 dark:text-rose-200'
                      }`}>
                        {result.matched ? '匹配成功 (Matched)' : '未能完成匹配 (Unmatched)'}
                      </h3>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400 m-0 mt-0.5">
                        {result.matched ? '规则引擎成功映射至标准目录项' : '需录入规则或补充词库条目'}
                      </p>
                    </div>
                  </div>

                  {result.confidence !== undefined && (
                    <div className="text-right">
                      <div className="text-xs text-zinc-500 dark:text-zinc-400 font-medium">置信度</div>
                      <div className="text-xl font-black text-blue-600 dark:text-blue-400">
                        {(result.confidence * 100).toFixed(1)}%
                      </div>
                    </div>
                  )}
                </div>

                {/* 详细匹配数据或原因 */}
                {result.matched ? (
                  <div className="space-y-4 bg-zinc-50 dark:bg-zinc-800/40 p-4 rounded-xl border border-zinc-200/60 dark:border-zinc-800">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <span className="text-xs text-zinc-400 dark:text-zinc-500 block mb-1 font-medium">标准项目名称</span>
                        <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{result.standard_name}</span>
                      </div>
                      <div>
                        <span className="text-xs text-zinc-400 dark:text-zinc-500 block mb-1 font-medium">标准项目编码</span>
                        <span className="inline-block px-2.5 py-0.5 rounded bg-zinc-200 dark:bg-zinc-700 text-zinc-800 dark:text-zinc-200 text-xs font-mono font-medium">
                          {result.standard_code}
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-zinc-400 dark:text-zinc-500 block mb-1 font-medium">匹配执行链路</span>
                        <Tag color="blue" className="rounded-md border-none px-2.5 py-0.5 text-xs font-medium">
                          {result.match_method || '规则引擎主通道'}
                        </Tag>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 rounded-xl bg-amber-50/50 dark:bg-amber-950/30 border border-amber-200/70 dark:border-amber-800/50 space-y-2">
                    <span className="text-xs font-semibold text-amber-800 dark:text-amber-400 block">未匹配诊断原因分析</span>
                    <p className="text-xs text-amber-700 dark:text-amber-300/90 leading-relaxed m-0">
                      {result.reason || '当前输入的短语在词典库中缺乏映射规则或部位特征无法与标准体库对齐。'}
                    </p>
                  </div>
                )}
              </div>
            </Card>
          ) : (
            <Card
              bordered={false}
              className="bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 shadow-xs rounded-xl h-full flex flex-col justify-center items-center text-center p-12"
            >
              <div className="w-16 h-16 rounded-full bg-blue-50 dark:bg-blue-950/60 flex items-center justify-center text-blue-600 dark:text-blue-400 mb-4 text-2xl">
                <SearchOutlined />
              </div>
              <h3 className="text-base font-semibold text-zinc-800 dark:text-zinc-200 mb-1">等待测试运行</h3>
              <p className="text-xs text-zinc-400 dark:text-zinc-500 max-w-sm">
                在左侧输入需要测试的原始检查项目名称与模态，点击“运行算法匹配”获取实时诊断链条。
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default MatchTest;

