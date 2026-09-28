import apiClient from './api';

// ==================== 类型定义 ====================

export interface EvalTask {
  id: number;
  name: string;
  description?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  total_count: number;
  matched_count: number;
  correct_count: number;
  wrong_count: number;
  no_match_count: number;
  match_rate?: number;
  accuracy?: number;
  f1_score?: number;
  avg_confidence?: number;
  avg_response_time?: number;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
}

export interface CreateTaskRequest {
  name: string;
  description?: string;
  test_file_path: string;
  sample_size?: number;
  modality?: string;
  tags?: string[];
  created_by?: string;
}

export interface TaskListResponse {
  total: number;
  tasks: EvalTask[];
}

export interface FailureCase {
  id: number;
  check_item: string;
  modality?: string;
  expected_code?: string;
  expected_name?: string;
  actual_code?: string;
  actual_name?: string;
  confidence?: number;
  failure_reason?: string;
  failure_detail?: string;
}

export interface FailuresResponse {
  total: number;
  cases: FailureCase[];
}

export interface FailureStatsResponse {
  stats: Record<string, number>;
}

// ==================== API 方法 ====================

export const evaluationAPI = {
  // 创建评测任务
  createTask: (data: CreateTaskRequest): Promise<EvalTask> =>
    apiClient.post('/evaluation/tasks', data),

  // 获取任务列表
  listTasks: (params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<TaskListResponse> =>
    apiClient.get('/evaluation/tasks', { params }),

  // 获取任务详情
  getTask: (taskId: number): Promise<EvalTask> =>
    apiClient.get(`/evaluation/tasks/${taskId}`),

  // 启动评测
  startEvaluation: (taskId: number): Promise<{ message: string; task_id: number }> =>
    apiClient.post(`/evaluation/tasks/${taskId}/start`),

  // 获取失败案例
  getFailures: (
    taskId: number,
    params?: {
      failure_reason?: string;
      limit?: number;
      offset?: number;
    }
  ): Promise<FailuresResponse> =>
    apiClient.get(`/evaluation/tasks/${taskId}/failures`, { params }),

  // 获取失败统计
  getFailureStats: (taskId: number): Promise<FailureStatsResponse> =>
    apiClient.get(`/evaluation/tasks/${taskId}/failures/stats`),

  // 删除任务
  deleteTask: (taskId: number): Promise<{ message: string; task_id: number }> =>
    apiClient.delete(`/evaluation/tasks/${taskId}`),
};
