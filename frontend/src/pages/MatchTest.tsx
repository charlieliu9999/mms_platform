import React, { useState } from 'react';
import { Card, Input, Select, Button, Tag, Progress, Row, Col, Spin, Empty } from 'antd';
import { SearchOutlined, CheckCircleFilled, ExclamationCircleOutlined, ThunderboltOutlined, ExperimentOutlined } from '@ant-design/icons';
import { matchAPI, MatchResult } from '../services/matchService';

const PRESET_TEST_CASES = [
  { label: 'CT头部平扫', text: 'CT头部平扫', modality: 'CT' },
  { label: 'CT头部平扫+增强', text: 'CT头部平扫+增强', modality: 'CT' },
  { label: '膝关节正侧位', text: '膝关节正、侧位', modality: 'DR' },
  { label: '胸部平扫', text: 'CT胸部高分辨率平扫', modality: 'CT' },
  { label: '头部MRA', text: 'MR头颅MRA血管造影', modality: 'MR' },
  { label: '超声心动', text: '彩色多普勒超声心动图', modality: 'US' },
];

const MatchTest: React.FC = () => {
  const [rawText, setRawText] = useState<string>('CT头部平扫+增强');
  const [modality, setModality] = useState<string>('CT');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<MatchResult | null>(null);

  const handleMatch = async () => {
    if (!rawText.trim()) return;
    setLoading(true);
    try {
      const res = await matchAPI.matchOne({
        name: rawText.trim(),
        modality: modality,
      });
      setResult(res);
    } catch {
      // Error handled
    } finally {
      setLoading(false);
    }
  };

  const handleApplyPreset = (preset: { text: string; modality: string }) => {
    setRawText(preset.text);
    setModality(preset.modality);
  };

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="border-b pb-3 border-border-theme">
        <h2 className="text-xl font-bold tracking-tight flex items-center gap-2 m-0 text-text-primary">
          <ExperimentOutlined className="text-brand-color" />
          医学标准化规则匹配算法实验室
        </h2>
        <p className="text-xs mt-1 m-0 text-text-secondary">输入任意原始检查描述，实时测试规则引擎的分词、别名归一、消歧及标准检索命中过程</p>
      </div>

      {/* 测试用例与输入框 */}
      <Card bordered={false} className="shadow-xs rounded-xl bg-bg-card border-border-theme">
        <div className="space-y-4">
          <div className="flex items-center gap-2 flex-wrap select-none">
            <span className="text-xs font-semibold text-text-secondary">快速预设测试用例:</span>
            {PRESET_TEST_CASES.map((tc, idx) => (
              <button
                key={idx}
                onClick={() => handleApplyPreset(tc)}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors border cursor-pointer bg-bg-subtle border-border-theme text-text-primary hover:bg-brand-color/10 hover:text-brand-color"
              >
                {tc.label}
              </button>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <Select
              value={modality}
              onChange={setModality}
              className="w-full sm:w-36 text-xs h-10"
              size="large"
            >
              {['CT', 'MR', 'US', 'DR', 'RF', 'MG', 'SPECT', 'DSA', 'PET/CT', 'PET/MR', 'OCT'].map((m) => (
                <Select.Option key={m} value={m}>{m} 检查</Select.Option>
              ))}
            </Select>

            <Input
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="输入原始检查描述文本（如: CT头部平扫+增强）..."
              onPressEnter={handleMatch}
              size="large"
              className="flex-1 text-sm rounded-lg"
            />

            <Button
              type="primary"
              size="large"
              icon={<SearchOutlined />}
              onClick={handleMatch}
              loading={loading}
              className="px-6 font-bold shadow-xs h-10"
            >
              运行单项算法匹配
            </Button>
          </div>
        </div>
      </Card>

      {/* 匹配结果控制台 */}
      {loading ? (
        <Card bordered={false} className="shadow-xs rounded-xl py-16 text-center bg-bg-card border-border-theme">
          <Spin size="large" />
          <p className="text-xs mt-4 m-0 text-text-secondary">正在调用算法引擎计算匹配路径与信心度...</p>
        </Card>
      ) : result ? (
        <div className="space-y-4">
          <Row gutter={[16, 16]}>
            {/* 匹配信心度 Dashboard */}
            <Col xs={24} md={8}>
              <Card bordered={false} className="shadow-xs rounded-xl text-center h-full flex flex-col justify-center bg-bg-card border-border-theme">
                <div className="text-xs font-semibold mb-2 text-text-secondary">匹配信心度得分</div>
                <div className="my-2">
                  <Progress
                    type="dashboard"
                    percent={Math.round(((result as any).score || (result.confidence ? result.confidence * 100 : 0)))}
                    format={() => (
                      <span className="text-2xl font-extrabold font-mono text-brand-color">
                        {(result as any).score || (result.confidence ? Math.round(result.confidence * 100) : 0)}
                      </span>
                    )}
                    strokeColor={{ '0%': '#3b82f6', '100%': '#10b981' }}
                  />
                </div>
                <div className="text-xs font-bold">
                  {result.matched || (result as any).num_standard > 0 ? (
                    <span className="text-emerald-600 flex items-center justify-center gap-1">
                      <CheckCircleFilled /> 匹配精准命中
                    </span>
                  ) : (
                    <span className="text-amber-600 flex items-center justify-center gap-1">
                      <ExclamationCircleOutlined /> 未在标准库中直接命中
                    </span>
                  )}
                </div>
              </Card>
            </Col>

            {/* 命中标准详情 */}
            <Col xs={24} md={16}>
              <Card
                bordered={false}
                className="shadow-xs rounded-xl h-full bg-bg-card border-border-theme"
                title={
                  <span className="text-sm font-bold flex items-center gap-2 text-text-primary">
                    <ThunderboltOutlined className="text-brand-color" />
                    算法命中标准检查项目 (Hit Standard Items)
                  </span>
                }
              >
                {(result as any).data && (result as any).data.length > 0 ? (
                  <div className="space-y-3">
                    {(result as any).data.map((item: any, idx: number) => (
                      <div key={idx} className="p-3.5 rounded-xl flex items-center justify-between bg-bg-subtle border border-border-theme">
                        <div>
                          <div className="text-xs font-mono font-bold text-brand-color">{item.item_code}</div>
                          <div className="text-sm font-extrabold mt-0.5 text-text-primary">{item.item_name}</div>
                        </div>
                        <Tag color="emerald" className="font-bold px-2 py-0.5 m-0 text-xs">
                          {item.modality || modality}
                        </Tag>
                      </div>
                    ))}
                  </div>
                ) : result.standard_name ? (
                  <div className="p-4 rounded-xl flex items-center justify-between bg-bg-subtle border border-border-theme">
                    <div>
                      <div className="text-xs font-mono font-bold text-brand-color">{result.standard_code || 'STD-ITEM'}</div>
                      <div className="text-sm font-extrabold mt-0.5 text-text-primary">{result.standard_name}</div>
                    </div>
                    <Tag color="emerald" className="font-bold px-2 py-0.5 m-0 text-xs">
                      {modality}
                    </Tag>
                  </div>
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无命中标准项目" />
                )}
              </Card>
            </Col>
          </Row>
        </div>
      ) : (
        <Card bordered={false} className="shadow-xs rounded-xl py-16 text-center bg-bg-card border-border-theme">
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="点击“运行单项算法匹配”查看匹配过程" />
        </Card>
      )}
    </div>
  );
};

export default MatchTest;
