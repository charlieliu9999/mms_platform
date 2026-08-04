import apiClient from './api';

export interface MatchRequest {
  name: string;
  modality: string;
  version?: string;
}

/** 标准项候选（data 子项内嵌套，后端实际返回 {code, name}） */
export interface StandardCandidate {
  code: string;
  name: string;
}

/** 单条标准项命中（data 数组元素：每个医嘱子项及其标准项候选列表） */
export interface StandardHit {
  raw?: string;
  standard?: StandardCandidate[];
  // 兼容旧字段
  item_code?: string;
  item_name?: string;
  [key: string]: any;
}

/** 与后端引擎输出对齐（MatchDispatcher.match 返回结构） */
export interface MatchResult {
  check_item: string;
  num_standard: number;
  data: StandardHit[];
  score: number;
  tier: string;
  confidence: number;
  reason?: string;
  has_entity?: boolean | null;
  _cache_hit?: boolean;
  cache_source?: string | null;
  [key: string]: any;
}

/** /api/match 响应包装 */
export interface MatchResponse {
  result: MatchResult;
  rule_version: string;
}

export interface StandardItem {
  id: number;
  item_code: string;
  item_name: string;
  modality: string;
  body_part_l1?: string;
  body_part_l2?: string;
  body_part_l3?: string;
  scan_method?: string;
  post_processing?: string;
  version?: string;
  created_at?: string;
  // 完整视图额外字段
  position?: string;      // 摆位
  scope?: string;         // 范围
}

export interface MedicalDictItem {

  id: number;
  word: string;
  type: string;
  modality: string;
  enable: number;
  created_at?: string;
  updated_at?: string;
}

export interface StatsData {
  total_medical_dict: number;
  total_phrase_map: number;
  total_ambiguity: number;
  total_standard_items: number;
  rule_version: string;
  dict_type_distribution?: Record<string, number>;
  unmatched_distribution?: Record<string, number>;
  modality_distribution?: Record<string, number>;
}

// ─── Phase 4: 匹配测试中心（检查项目字典 procedure_dictionary） ─────────

/** 检查项目字典条目（含未匹配登记状态） */
export interface ProcedureItem {
  id: number;
  semantic_id: string;
  name_zh: string;
  modality: string;
  um_status: string | null;   // open / resolved / wontfix / null
  um_reason: string | null;
}

export interface ProcedureItemsResponse {
  items: ProcedureItem[];
  total: number;
  modality_stats: Record<string, { total: number; unmatched: number }>;
}

/** 单条检查项目的匹配结果（源 → 标准项对应） */
export interface ProcedureMatchResult {
  procedure_id: number;
  semantic_id: string;
  name_zh: string;
  modality: string;
  matched: boolean;
  tier: string;
  confidence: number;
  engine: string;
  standards: { code: string; name: string }[];
  reason_code?: string;
  detail?: string;
}

export interface MatchProceduresResponse {
  total_processed: number;
  matched_count: number;
  unmatched_count: number;
  by_modality: Record<string, { total: number; matched: number; unmatched: number }>;
  results: ProcedureMatchResult[];
}

// 匹配相关 API
export const matchAPI = {
  // 单个匹配：解包后端 {result, rule_version} 外层
  // 注：api.ts 响应拦截器已返回 response.data，此处按解包后的类型断言
  matchOne: (data: MatchRequest): Promise<MatchResult> =>
    apiClient.post('/match', data).then((res) => (res as unknown as MatchResponse).result),

  // 批量匹配：自动补 key，并把 {key: result} 字典还原为与输入同序的数组
  matchBatch: async (items: MatchRequest[]): Promise<MatchResult[]> => {
    const keyed = items.map((it, i) => ({ key: String(i), ...it }));
    const res = (await apiClient.post('/batch-match', { items: keyed })) as unknown as {
      results: Record<string, MatchResult>;
      stats: any;
      rule_version: string;
    };
    return keyed.map((it) => res.results[it.key]);
  },
};

// 管理后台 API
export const adminAPI = {
  // 获取统计数据
  getStats: (): Promise<StatsData> =>
    apiClient.get('/admin/stats'),

  // 医学词典
  getMedicalDict: (params?: { keyword?: string; modality?: string; page?: number; page_size?: number }): Promise<{ items: MedicalDictItem[]; total: number }> =>
    apiClient.get('/admin/medical-dict', { params }),

  createMedicalDict: (data: Omit<MedicalDictItem, 'id' | 'created_at' | 'updated_at'>): Promise<MedicalDictItem> =>
    apiClient.post('/admin/medical-dict', data),

  updateMedicalDict: (id: number, data: Partial<MedicalDictItem>): Promise<MedicalDictItem> =>
    apiClient.put(`/admin/medical-dict/${id}`, data),

  deleteMedicalDict: (id: number): Promise<void> =>
    apiClient.delete(`/admin/medical-dict/${id}`),

  // 词库管理通用 API
  getLexiconRows: (table: string, params?: any): Promise<any> =>
    apiClient.get(`/admin/lexicon/${table}`, { params }),

  createLexiconRow: (table: string, data: any): Promise<any> =>
    apiClient.post(`/admin/lexicon/${table}`, data),

  updateLexiconRow: (table: string, id: number, data: any): Promise<any> =>
    apiClient.put(`/admin/lexicon/${table}/${id}`, data),

  deleteLexiconRow: (table: string, id: number): Promise<any> =>
    apiClient.delete(`/admin/lexicon/${table}/${id}`),

  // 短语映射分组查询
  getPhraseMapGrouped: (params?: any): Promise<any> =>
    apiClient.get('/admin/lexicon/phrase_map/grouped', { params }),

  // 词库版本管理
  getLexiconVersions: (): Promise<any> =>
    apiClient.get('/admin/lexicon/versions'),

  reloadLexicon: (): Promise<any> =>
    apiClient.post('/admin/lexicon/reload'),

  // 版本历史
  getRuleVersionHistory: (params?: { limit?: number }): Promise<any> =>
    apiClient.get('/admin/rule-version/history', { params }),

  // 标准项目管理
  getStandardItems: (params?: {
    page?: number;
    page_size?: number;
    modality?: string;
    body_part_l1?: string;
    body_part_l2?: string;
    body_part_l3?: string;
    version?: string;
    search?: string;
  }): Promise<any> =>
    apiClient.get('/admin/standard-items', { params }),

  getStandardItemStats: (params?: { version?: string }): Promise<any> =>
    apiClient.get('/admin/standard-items/stats', { params }),

  getStandardItemFilterOptions: (params?: any): Promise<any> =>
    apiClient.get('/admin/standard-items/filter-options', { params }),

  importAllStandardItems: (): Promise<any> =>
    apiClient.post('/admin/standard-items/import-all'),


  // 未匹配工作台
  getUnmatchedSummary: (): Promise<any> =>
    apiClient.get('/admin/unmatched/summary'),

  getUnmatchedList: (params?: any): Promise<any> =>
    apiClient.get('/admin/unmatched/list', { params }),

  // 后端 status 为 Query 参数（^(open|resolved|wontfix)$），不能放 body
  updateUnmatchedStatus: (id: number, status: string): Promise<any> =>
    apiClient.put(`/admin/unmatched/${id}/status`, null, { params: { status } }),

  // ─── Phase 4: 匹配测试中心 ─────────────────────────────────────────
  // 列出检查项目字典（procedure_dictionary）+ 模态统计 + 未匹配状态
  getProcedureItems: (params?: { modality?: string; search?: string; limit?: number }): Promise<ProcedureItemsResponse> =>
    apiClient.get('/admin/procedure-items', { params }),

  // 对指定检查项目批量匹配并回写 unmatched_registry（单次上限 400，前端分块）
  matchProcedures: (procedureIds: number[]): Promise<MatchProceduresResponse> =>
    apiClient.post('/admin/match-procedures', { procedure_ids: procedureIds }, { timeout: 180000 }),
};

// Agent API
export const agentAPI = {
  // 分析未匹配项目
  analyze: (params: { since_days?: number; min_frequency?: number; modality?: string }): Promise<any> =>
    apiClient.post('/agent/analyze', params),

  // 获取建议列表
  getSuggestions: (params?: { status?: string }): Promise<any> =>
    apiClient.get('/agent/suggestions', { params }),

  // 审批建议
  approveSuggestion: (id: number): Promise<any> =>
    apiClient.post(`/agent/suggestions/${id}/approve`),
};
