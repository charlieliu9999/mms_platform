import { useState } from 'react';
import { LexiconVersionBar } from '../components/LexiconVersionBar';
import { PhraseMapView } from '../components/PhraseMapView';
import { MedicalDictView } from '../components/MedicalDictView';
import { AmbiguityView } from '../components/AmbiguityView';
import { KeywordRuleView } from '../components/KeywordRuleView';
import { CheckitemStandardView } from '../components/CheckitemStandardView';
import { BookOutlined } from '@ant-design/icons';

// 5 张规则表 tab 元数据（key 与后端 LEXICON_TABLES 对应）
const TABLE_TABS: { key: string; label: string; desc: string }[] = [
  { key: 'medical_dict', label: '医学词典', desc: 'jieba 分词词典：部位/扫描/后处理/摆位' },
  { key: 'phrase_map', label: '别名映射', desc: '预处理/归一化/部位映射/血管映射' },
  { key: 'ambiguity', label: '消歧规则', desc: '部位+处理方式的消歧与默认补全' },
  { key: 'keyword_match_rules', label: '关键词规则', desc: 'US/SPECT/PET/OCT/DSA 关键词匹配' },
  { key: 'checkitem_standard', label: '标准查找表', desc: '标准项目查找（部位×扫描×后处理）' },
];

export default function LexiconMgmt() {
  const [activeTable, setActiveTable] = useState('medical_dict');
  const [activeVersion, setActiveVersion] = useState('');

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
      <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3">
        <div>
          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight m-0 flex items-center gap-2">
            <BookOutlined className="text-blue-600 dark:text-blue-400" />
            词库治理工作台
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 m-0">查看、补充与上线医学归一化分词字典与歧义映射规则</p>
        </div>
      </div>

      <LexiconVersionBar
        activeVersion={activeVersion}
        onVersionChange={setActiveVersion}
        activeTable={activeTable}
      />

      <div className="flex items-center gap-1 flex-wrap border-b border-zinc-200/80 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-800/30 p-1 rounded-lg">
        {TABLE_TABS.map((t) => (
          <button
            key={t.key}
            title={t.desc}
            onClick={() => setActiveTable(t.key)}
            className={`px-4 py-2 text-xs font-semibold rounded-md transition-all duration-150 ${
              activeTable === t.key
                ? 'bg-white dark:bg-zinc-800 text-blue-700 dark:text-blue-400 shadow-xs border border-zinc-200/80 dark:border-zinc-700'
                : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-100/60 dark:hover:bg-zinc-800/40 border border-transparent'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 min-h-0 pt-1">
        {renderView()}
      </div>
    </div>
  );
}

