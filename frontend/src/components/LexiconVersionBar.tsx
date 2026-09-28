import { useCallback, useEffect, useState } from 'react';
import { message as antdMessage } from 'antd';
import { Loader2, Zap, Fingerprint } from 'lucide-react';
import { adminAPI } from '../services/matchService';

// 后端 GET /lexicon/versions 返回
type VersionInfo = { version: string; count: number; updated_at?: string };
type VersionsResp = {
  versions: Record<string, VersionInfo[]>;   // table_key -> versions
  default_version: string;
  fallback_chain: string[];
  rule_fingerprint: string;
};

type Props = {
  activeVersion: string;
  onVersionChange: (v: string) => void;
  /** 当前展示的表 key，决定版本切换器是否可用（无 version 列的表置灰） */
  activeTable?: string;
};

// 带 version 列的表（后端 lexicon_service.VERSIONED_TABLES 对应）
const VERSIONED_TABLES = new Set([
  'phrase_map', 'ambiguity', 'checkitem_standard',
]);

/**
 * 词库治理台顶层版本切换栏：
 *  - 下拉切换生效版本（作为下方表格的默认过滤条件）
 *  - 显示各版本行数、内容指纹
 *  - 触发热重载
 */
export function LexiconVersionBar({ activeVersion, onVersionChange, activeTable }: Props) {
  const [data, setData] = useState<VersionsResp | null>(null);
  const [loading, setLoading] = useState(false);
  const [reloading, setReloading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = (await adminAPI.getLexiconVersions()) as unknown as VersionsResp;
      setData(res);
      // 首次进入：把后端默认版本回填给父组件
      if (!activeVersion && res?.default_version) onVersionChange(res.default_version);
    } catch { antdMessage.error('加载版本清单失败'); }
    finally { setLoading(false); }
  }, [activeVersion, onVersionChange]);

  useEffect(() => { load(); }, [load]);

  const handleReload = async () => {
    setReloading(true);
    try {
      const res: any = await adminAPI.reloadLexicon();
      antdMessage.success(res?.rule_version ? `已热重载，规则版本 ${res.rule_version}` : '已热重载生效');
      load();  // 重新拉指纹
    } catch { antdMessage.error('热重载失败'); }
    finally { setReloading(false); }
  };

  const disabled = activeTable ? !VERSIONED_TABLES.has(activeTable) : false;

  // 版本列表：优先当前表实际拥有的版本；无法映射时回退到全表并集
  const allVersions = (() => {
    if (!data?.versions) return [] as string[];
    if (activeTable && VERSIONED_TABLES.has(activeTable)) {
      const arr = data.versions[activeTable] || [];
      return arr.map((v) => v.version).sort((a, b) => (a < b ? 1 : -1));
    }
    const set = new Set<string>();
    for (const arr of Object.values(data.versions)) for (const v of arr) set.add(v.version);
    return Array.from(set).sort((a, b) => (a < b ? 1 : -1));
  })();

  // 当前表切到无当前版本时，自动跳到该表的最新版本
  useEffect(() => {
    if (!data || disabled) return;
    if (!allVersions.length) return;
    if (!activeVersion || !allVersions.includes(activeVersion)) {
      onVersionChange(allVersions[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTable, data]);

  // 当前版本在各表中的行数
  const versionStats = (v: string) => {
    if (!data?.versions) return '';
    const parts: string[] = [];
    for (const [tbl, arr] of Object.entries(data.versions)) {
      const hit = arr.find((x) => x.version === v);
      if (hit) parts.push(`${tblLabel(tbl)}:${hit.count}`);
    }
    return parts.join(' · ');
  };

  return (
    <div className="rounded-lg border border-blue-100 dark:border-blue-500/30 bg-blue-50/40 dark:bg-blue-500/5 p-2.5 space-y-1.5">
      <div className="flex items-center gap-2 flex-wrap text-xs">
        <span className="text-zinc-600 dark:text-zinc-300 font-medium">生效版本</span>
        <select
          value={activeVersion}
          disabled={disabled || loading || !data}
          onChange={(e) => onVersionChange(e.target.value)}
          className="px-2 py-1 text-xs rounded border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 disabled:opacity-50"
          title={disabled ? '该表无 version 列，版本切换对本表无效' : '切换后下方表格自动按此版本过滤'}
        >
          {allVersions.map((v) => (
            <option key={v} value={v}>{v}</option>
          ))}
        </select>

        {data?.default_version && (
          <span
            className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-100 dark:bg-zinc-800 text-zinc-500"
            title={`匹配引擎默认调用版本 (VERSION_FALLBACK head)：${data.default_version}，回退链：${data.fallback_chain.join(' → ')}`}
          >
            默认 {data.default_version} · 回退 {data.fallback_chain.join('→')}
          </span>
        )}

        <span className="ml-auto flex items-center gap-1 text-[10px] text-zinc-400" title="规则表内容 md5 指纹，任何增删改都会变化">
          <Fingerprint className="w-3 h-3" />
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : (data?.rule_fingerprint ?? '—')}
        </span>

        <button onClick={handleReload} disabled={reloading}
          title="词库改动后触发引擎热重载，秒级生效"
          className="inline-flex items-center gap-1 py-1 px-2 text-xs rounded border border-amber-300 dark:border-amber-500/40 text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-500/10 disabled:opacity-40">
          {reloading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />} 热重载
        </button>
      </div>

      {activeVersion && !disabled && (
        <div className="text-[10px] text-zinc-500 pl-1">
          <span className="text-zinc-400">当前版本行数 </span>
          {versionStats(activeVersion) || '—'}
        </div>
      )}
      {disabled && (
        <div className="text-[10px] text-amber-600 dark:text-amber-400 pl-1">
          此表无版本列（全局生效），版本切换器不作用于本表
        </div>
      )}
    </div>
  );
}

function tblLabel(k: string) {
  switch (k) {
    case 'phrase_map': return '别名映射';
    case 'ambiguity': return '消歧规则';
    case 'checkitem_standard': return '标准查找表';
    default: return k;
  }
}
