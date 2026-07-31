import apiClient from './api';

export interface MatchRequest {
  name: string;
  modality: string;
  version?: string;
}

export interface MatchResult {
  matched: boolean;
  standard_name?: string;
  standard_code?: string;
  confidence?: number;
  match_method?: string;
  reason?: string;
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

// 匹配相关 API
export const matchAPI = {
  // 单个匹配
  matchOne: (data: MatchRequest): Promise<MatchResult> =>
    apiClient.post('/match', data),

  // 批量匹配
  matchBatch: (items: MatchRequest[]): Promise<MatchResult[]> =>
    apiClient.post('/batch-match', { items }),
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

  updateUnmatchedStatus: (id: number, status: string): Promise<any> =>
    apiClient.put(`/admin/unmatched/${id}/status`, { status }),
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
