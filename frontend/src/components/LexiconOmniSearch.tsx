import React, { useState, useEffect, useRef } from 'react';
import { Input, Popover, Tag, Spin, Empty } from 'antd';
import { SearchOutlined, BookOutlined, SwapOutlined, ThunderboltOutlined, CheckSquareOutlined } from '@ant-design/icons';
import { adminAPI } from '../services/matchService';

interface SearchResultItem {
  type: 'medical_dict' | 'phrase_map' | 'ambiguity' | 'standard';
  title: string;
  subtitle: string;
  meta: string;
  raw: any;
}

interface LexiconOmniSearchProps {
  onSelectResult: (targetTab: string, subCategory?: string, searchKeyword?: string) => void;
}

export const LexiconOmniSearch: React.FC<LexiconOmniSearchProps> = ({ onSelectResult }) => {
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [open, setOpen] = useState(false);
  const timerRef = useRef<any>(null);

  useEffect(() => {
    if (!keyword.trim()) {
      setResults([]);
      setOpen(false);
      return;
    }

    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(async () => {
      setLoading(true);
      setOpen(true);
      try {
        const query = keyword.trim();
        const searchPromises = [
          adminAPI.getLexiconRows('medical_dict', { page: 1, page_size: 5, search: query }),
          adminAPI.getPhraseMapGrouped({ page: 1, page_size: 5, search: query }),
          adminAPI.getLexiconRows('ambiguity', { page: 1, page_size: 5, search: query }),
        ];

        const [dictRes, phraseRes, ambRes] = await Promise.allSettled(searchPromises);

        const items: SearchResultItem[] = [];

        // 解析医学词典
        if (dictRes.status === 'fulfilled' && (dictRes.value as any)?.data) {
          (dictRes.value as any).data.slice(0, 4).forEach((row: any) => {
            items.push({
              type: 'medical_dict',
              title: row.word,
              subtitle: `类型: ${row.type}`,
              meta: '医学分词库',
              raw: row,
            });
          });
        }

        // 解析别名映射
        if (phraseRes.status === 'fulfilled' && (phraseRes.value as any)?.data) {
          (phraseRes.value as any).data.slice(0, 4).forEach((group: any) => {
            items.push({
              type: 'phrase_map',
              title: `${group.aliases?.map((a: any) => a.src_word).join(', ') || ''} ➔ ${group.dst_word}`,
              subtitle: `阶段: ${group.step} | 模态: ${group.modality || 'ALL'}`,
              meta: '别名映射库',
              raw: group,
            });
          });
        }

        // 解析消歧规则
        if (ambRes.status === 'fulfilled' && (ambRes.value as any)?.data) {
          (ambRes.value as any).data.slice(0, 4).forEach((row: any) => {
            items.push({
              type: 'ambiguity',
              title: `${row.raw_modality || '全模态'} | 条件: ${row.pattern_condition || '任意'}`,
              subtitle: `目标: ${row.target_body || '-'} / ${row.target_scan || '-'}`,
              meta: '消歧规则库',
              raw: row,
            });
          });
        }

        setResults(items);
      } catch (err) {
        console.error('Omni-search failed:', err);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [keyword]);

  const handleItemClick = (item: SearchResultItem) => {
    setOpen(false);
    if (item.type === 'medical_dict') {
      onSelectResult('medical_dict', item.raw.type, item.raw.word);
    } else if (item.type === 'phrase_map') {
      onSelectResult('phrase_map', item.raw.step, item.raw.dst_word);
    } else if (item.type === 'ambiguity') {
      onSelectResult('ambiguity', undefined, item.raw.target_body || keyword);
    }
  };

  const getBadgeIcon = (type: string) => {
    switch (type) {
      case 'medical_dict': return <BookOutlined className="text-blue-500" />;
      case 'phrase_map': return <SwapOutlined className="text-emerald-500" />;
      case 'ambiguity': return <ThunderboltOutlined className="text-amber-500" />;
      default: return <CheckSquareOutlined className="text-purple-500" />;
    }
  };

  const popoverContent = (
    <div className="w-[420px] max-h-[380px] overflow-y-auto py-1 space-y-1 select-none">
      {loading ? (
        <div className="py-8 text-center text-zinc-400 dark:text-zinc-500 text-xs space-y-2">
          <Spin size="small" />
          <div>跨词库全局检索中...</div>
        </div>
      ) : results.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="未搜索到匹配的词条或规则" className="my-4" />
      ) : (
        results.map((item, idx) => (
          <div
            key={idx}
            onClick={() => handleItemClick(item)}
            className="p-2.5 rounded-lg hover:bg-zinc-100/80 dark:hover:bg-zinc-800/80 cursor-pointer transition-colors flex items-center justify-between border border-transparent hover:border-zinc-200 dark:hover:border-zinc-700"
          >
            <div className="space-y-0.5 min-w-0 pr-2">
              <div className="text-xs font-bold text-zinc-800 dark:text-zinc-200 truncate flex items-center gap-1.5">
                {getBadgeIcon(item.type)}
                <span>{item.title}</span>
              </div>
              <div className="text-[11px] text-zinc-400 dark:text-zinc-500 truncate">{item.subtitle}</div>
            </div>
            <Tag color="blue" className="m-0 text-[10px] shrink-0 font-normal">
              {item.meta}
            </Tag>
          </div>
        ))
      )}
    </div>
  );

  return (
    <Popover
      content={popoverContent}
      open={open && keyword.trim().length > 0}
      onOpenChange={(v) => !v && setOpen(false)}
      trigger="click"
      placement="bottomLeft"
    >
      <Input
        prefix={<SearchOutlined className="text-zinc-400 dark:text-zinc-500 mr-1" />}
        placeholder="跨表搜词条、别名或规则（如: 胸部、平扫、CTA）..."
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        allowClear
        className="w-80 md:w-96 rounded-lg bg-zinc-50 dark:bg-zinc-800/80 border-zinc-200 dark:border-zinc-700 text-xs h-9 hover:border-blue-500 focus:border-blue-500"
      />
    </Popover>
  );
};
