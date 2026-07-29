import { useState } from 'react';
import { LexiconVersionBar } from '../components/LexiconVersionBar';
import { PhraseMapView } from '../components/PhraseMapView';
import { MedicalDictView } from '../components/MedicalDictView';
import { AmbiguityView } from '../components/AmbiguityView';
import { KeywordRuleView } from '../components/KeywordRuleView';
import { CheckitemStandardView } from '../components/CheckitemStandardView';
import { LexiconOmniSearch } from '../components/LexiconOmniSearch';
import { BookOutlined, SwapOutlined, ThunderboltOutlined, CheckSquareOutlined } from '@ant-design/icons';

// 3 大主逻辑分组
const MAIN_GROUPS = [
  {
    key: 'lexicon_mapping',
    label: '基础词汇与别名映射',
    icon: <SwapOutlined />,
    desc: '医学分词库 + 文本归一化与别名映射',
    subTabs: [
      { key: 'medical_dict', label: '医学词典', hint: 'jieba 部位/扫描/后处理分词词条' },
      { key: 'phrase_map', label: '别名映射库', hint: '预处理/归一化/部位/血管映射链条' },
    ],
  },
  {
    key: 'rules_disambiguation',
    label: '歧义消除与匹配规则',
    icon: <ThunderboltOutlined />,
    desc: '上下文消歧补全 + 模态关键词规则',
    subTabs: [
      { key: 'ambiguity', label: '消歧补全规则', hint: '上下文歧义消解与默认值补充' },
      { key: 'keyword_match_rules', label: '模态关键词规则', hint: 'US/SPECT/PET/OCT/DSA 匹配逻辑' },
    ],
  },
  {
    key: 'standard_lookup',
    label: '标准参考字典库',
    icon: <CheckSquareOutlined />,
    desc: '国家标准检查项目与部位查找',
    subTabs: [
      { key: 'checkitem_standard', label: '标准项目检索表', hint: '标准项目查找（部位×扫描×后处理）' },
    ],
  },
];

export default function LexiconMgmt() {
  const [mainGroup, setMainGroup] = useState('lexicon_mapping');
  const [activeTable, setActiveTable] = useState('medical_dict');
  const [activeVersion, setActiveVersion] = useState('');

  // 处理全局 Omni-Search 的快速定位跳转
  const handleOmniSelect = (targetTab: string) => {
    if (targetTab === 'medical_dict' || targetTab === 'phrase_map') {
      setMainGroup('lexicon_mapping');
    } else if (targetTab === 'ambiguity' || targetTab === 'keyword_match_rules') {
      setMainGroup('rules_disambiguation');
    } else if (targetTab === 'checkitem_standard') {
      setMainGroup('standard_lookup');
    }
    setActiveTable(targetTab);
  };

  const currentGroupObj = MAIN_GROUPS.find((g) => g.key === mainGroup) || MAIN_GROUPS[0];

  const handleMainGroupChange = (groupKey: string) => {
    setMainGroup(groupKey);
    const targetGroup = MAIN_GROUPS.find((g) => g.key === groupKey);
    if (targetGroup && targetGroup.subTabs.length > 0) {
      setActiveTable(targetGroup.subTabs[0].key);
    }
  };

  const renderView = () => {
    switch (activeTable) {
      case 'medical_dict': return <MedicalDictView />;
      case 'phrase_map': return <PhraseMapView activeVersion={activeVersion} />;
      case 'ambiguity': return <AmbiguityView activeVersion={activeVersion} />;
      case 'keyword_match_rules': return <KeywordRuleView />;
      case 'checkitem_standard': return <CheckitemStandardView activeVersion={activeVersion} />;
      default: return null;
    }
  };

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* 顶部 Header + 跨表 Omni-Search */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3 gap-3">
        <div>
          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight m-0 flex items-center gap-2">
            <BookOutlined className="text-blue-600 dark:text-blue-400" />
            医学词库与规则治理中心
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 m-0">一站式管理分词词库、别名映射、歧义规则与标准字典参考表</p>
        </div>
        <LexiconOmniSearch onSelectResult={handleOmniSelect} />
      </div>

      {/* 版本号管控 ToolBar */}
      <LexiconVersionBar
        activeVersion={activeVersion}
        onVersionChange={setActiveVersion}
        activeTable={activeTable}
      />

      {/* 第一层: 3 大主功能区导航 (Main Group Nav) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 p-1 bg-zinc-100/70 dark:bg-zinc-850 rounded-xl">
        {MAIN_GROUPS.map((g) => {
          const isActive = mainGroup === g.key;
          return (
            <button
              key={g.key}
              onClick={() => handleMainGroupChange(g.key)}
              className={`p-3 rounded-lg text-left transition-all duration-150 border select-none ${
                isActive
                  ? 'bg-white dark:bg-zinc-900 text-blue-600 dark:text-blue-400 shadow-xs border-zinc-200/90 dark:border-zinc-700'
                  : 'bg-transparent text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/50 border-transparent'
              }`}
            >
              <div className="flex items-center gap-2 font-bold text-xs">
                <span className="text-sm">{g.icon}</span>
                <span>{g.label}</span>
              </div>
              <div className="text-[11px] text-zinc-400 dark:text-zinc-500 font-normal mt-0.5 truncate">{g.desc}</div>
            </button>
          );
        })}
      </div>

      {/* 第二层: 当前主功能区下的子子视图 Tabs */}
      {currentGroupObj.subTabs.length > 1 && (
        <div className="flex items-center gap-1.5 border-b border-zinc-200/80 dark:border-zinc-800 pb-2">
          {currentGroupObj.subTabs.map((st) => (
            <button
              key={st.key}
              title={st.hint}
              onClick={() => setActiveTable(st.key)}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-md transition-all ${
                activeTable === st.key
                  ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800/60'
                  : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-transparent'
              }`}
            >
              {st.label}
            </button>
          ))}
        </div>
      )}

      {/* 主数据表视图展示区 */}
      <div className="flex-1 min-h-0 pt-1">
        {renderView()}
      </div>
    </div>
  );
}
