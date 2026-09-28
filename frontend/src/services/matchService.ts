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

export type TechnicalDetailStatus =
  | 'pending_review'
  | 'approved'
  | 'rejected'
  | 'applied'
  | 'superseded';

export interface TechnicalDetailSourceRef {
  item_id: number;
  item_code: string;
  item_name: string;
  role: string;
}

export interface TechnicalDetailConflict {
  field: string;
  resolution: string;
  plain_value?: string;
  enhanced_value?: string;
}

export interface TechnicalDetailCandidateSummary {
  id: number;
  target_item_id: number;
  target_item_code: string;
  target_item_name: string;
  target_version: string;
  modality: string;
  generation_method: string;
  confidence: number;
  conflicts_json: TechnicalDetailConflict[];
  source_item_ids_json: number[];
  algorithm_version: string;
  rationale: string;
  status: TechnicalDetailStatus;
  reviewer?: string;
  reviewed_at?: string;
  has_manual_edits: boolean;
  last_edited_by?: string;
  last_edited_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TechnicalDetailRevision {
  id: number;
  revision_no: number;
  before_json: Record<string, string>;
  after_json: Record<string, string>;
  edited_by: string;
  edit_notes?: string;
  created_at: string;
}

export interface TechnicalDetailPublication {
  id: number;
  candidate_id?: number;
  target_item_code?: string;
  before_json?: Record<string, string | null>;
  after_json: Record<string, string>;
  published_by: string;
  publish_notes?: string;
  published_at: string;
  status: 'published' | 'rolled_back';
  rolled_back_by?: string;
  rollback_reason?: string;
  rolled_back_at?: string;
}

export interface TechnicalDetailCandidate extends TechnicalDetailCandidateSummary {
  candidate_json: Record<string, string>;
  field_sources_json: Record<string, TechnicalDetailSourceRef[]>;
  source_fingerprint: string;
  review_notes?: string;
  revisions: TechnicalDetailRevision[];
  publications: TechnicalDetailPublication[];
}

export interface TechnicalDetailProvenance {
  id: number;
  source_kind: 'historical_import' | 'rule_fusion' | 'evaluation_import';
  source_system: string;
  source_table: string;
  source_record_key?: string;
  import_batch: string;
  match_method: string;
  field_names: string[];
  source_notes?: string;
  publication_id?: number;
  created_at: string;
  source_label: string;
}

export interface TechnicalDetailLibraryItem {
  id: number;
  item_code: string;
  item_name: string;
  modality: string;
  version: string;
  scan_method?: string;
  post_processing?: string;
  is_active: boolean;
  body_position?: string;
  scan_scope?: string;
  contrast_agent?: string;
  image_region?: string;
  image_focus?: string;
  scan_method_detail?: string;
  scan_param?: string;
  coil?: string;
  base_sequence?: string;
  compose_sequence?: string;
  clinical_indication?: string;
  clinical_significance?: string;
  organs?: string;
  anatomical_structure?: string;
  technical_notes?: string;
  image_grade?: string;
  image_score?: number;
  sources: TechnicalDetailProvenance[];
}

export interface TechnicalDetailLibraryStats {
  total: number;
  active_total: number;
  ct_total: number;
  mr_total: number;
  sources: { source_kind: string; source_table: string; count: number }[];
}

export interface TechnicalDetailStats {
  total: number;
  by_status: Partial<Record<TechnicalDetailStatus, number>>;
  by_method: Record<string, number>;
  conflict_count: number;
  active_publication_count: number;
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
  last_matched: boolean | null;
  last_tier: string | null;
  last_confidence: number | null;
  last_source: string | null;
  last_effective_modality: string | null;
  last_standards: { code: string; name: string }[];
  last_reason_code: string | null;
  last_detail: string | null;
  last_rule_version: string | null;
  last_evaluated_at: string | null;
}

export interface ProcedureItemsResponse {
  items: ProcedureItem[];
  total: number;
  modality_stats: Record<string, {
    total: number;
    matched: number;
    unmatched: number;
    untested: number;
  }>;
  match_config: { clear_cache_before_run: boolean };
}

/** 单条检查项目的匹配结果（源 → 标准项对应） */
export interface ProcedureMatchResult {
  procedure_id: number;
  semantic_id: string;
  name_zh: string;
  modality: string;
  effective_modality?: string;
  matched: boolean;
  tier: string;
  confidence: number;
  engine: string;
  source?: string;
  cache_hit?: boolean;
  rule_version?: string;
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

  // 正式技术参数库及来源
  getTechnicalDetailLibraryStats: (): Promise<TechnicalDetailLibraryStats> =>
    apiClient.get('/admin/technical-detail-library/stats'),

  getTechnicalDetailLibrary: (params?: {
    modality?: string;
    source_kind?: 'historical_import' | 'rule_fusion' | 'evaluation_import';
    search?: string;
    is_active?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<{ total: number; items: TechnicalDetailLibraryItem[] }> =>
    apiClient.get('/admin/technical-detail-library', { params }),

  getTechnicalDetailLibraryItem: (id: number): Promise<TechnicalDetailLibraryItem> =>
    apiClient.get(`/admin/technical-detail-library/${id}`),

  // 技术详情构建、审核与官网发布
  getTechnicalDetailStats: (): Promise<TechnicalDetailStats> =>
    apiClient.get('/admin/technical-detail-candidates/stats'),

  getTechnicalDetailCandidates: (params?: {
    status?: TechnicalDetailStatus;
    modality?: string;
    search?: string;
    has_conflicts?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<{ total: number; items: TechnicalDetailCandidateSummary[] }> =>
    apiClient.get('/admin/technical-detail-candidates', { params }),

  getTechnicalDetailCandidate: (id: number): Promise<TechnicalDetailCandidate> =>
    apiClient.get(`/admin/technical-detail-candidates/${id}`),

  generateTechnicalDetailCandidates: (data: {
    version: string;
    modality: string;
    item_code?: string;
    limit?: number;
    persist: boolean;
  }): Promise<any> =>
    apiClient.post('/admin/technical-detail-candidates/generate', data, { timeout: 180000 }),

  editTechnicalDetailCandidate: (
    id: number,
    data: { candidate_fields: Record<string, string>; editor: string; notes?: string },
  ): Promise<TechnicalDetailCandidate> =>
    apiClient.put(`/admin/technical-detail-candidates/${id}`, data),

  reviewTechnicalDetailCandidate: (
    id: number,
    data: { decision: 'approved' | 'rejected'; reviewer: string; notes?: string },
  ): Promise<{ id: number; status: TechnicalDetailStatus }> =>
    apiClient.post(`/admin/technical-detail-candidates/${id}/review`, data),

  publishTechnicalDetailCandidate: (
    id: number,
    data: { publisher?: string; notes?: string },
  ): Promise<{ publication_id: number; target_item_code: string; published_fields: string[]; status: string }> =>
    apiClient.post(`/admin/technical-detail-candidates/${id}/publish`, data),

  bulkReviewAndPublishTechnicalDetails: (data: {
    candidate_ids?: number[];
    select_all?: boolean;
    status?: TechnicalDetailStatus;
    modality?: string;
    search?: string;
    has_conflicts?: boolean;
    operator?: string;
    notes?: string;
  }): Promise<{
    requested_count: number;
    published_count: number;
    skipped_count: number;
    failed_count: number;
    failed: { id: number; reason: string }[];
  }> =>
    apiClient.post('/admin/technical-detail-bulk/review-and-publish', data, { timeout: 300000 }),

  rollbackTechnicalDetailPublication: (
    id: number,
    data: { operator: string; reason: string },
  ): Promise<{ publication_id: number; target_item_code: string; status: string }> =>
    apiClient.post(`/admin/technical-detail-publications/${id}/rollback`, data),

  getTechnicalDetailPublications: (params?: {
    status?: 'published' | 'rolled_back';
    limit?: number;
    offset?: number;
  }): Promise<{ total: number; items: TechnicalDetailPublication[] }> =>
    apiClient.get('/admin/technical-detail-publications', { params }),

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

  // 批量评测前失效全部 L1 缓存，确保本轮使用当前规则重新计算
  clearMatchCache: (): Promise<{ status: string; count: number }> =>
    apiClient.post('/cache/invalidate', { modality: null }),
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
