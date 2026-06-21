// ============================================================
// AI 平台 API（与后端 router.py 严格对齐，2026-05-21 修订）
// ============================================================
import { http } from '@/utils/request'

export const aiApi = {
  // ============================================================
  // 任务中心（/ai/task/list · /ai/task/cancel · /ai/task/stream）
  // ============================================================

  /** AI 任务列表（POST /ai/task/list） */
  tasks: (params: { page?: number; pageSize?: number; status?: string; type?: string }) =>
    http.post<{
      list: Array<{
        id: number
        taskId: string
        type: string
        status: string
        cost: number
        model: string
        confidence: number
        createdAt: string
      }>
      total: number
    }>('/ai/task/list', params),

  /** AI 任务详情（GET /ai/task/detail/:id） */
  taskDetail: (taskId: string) =>
    http.get<{
      taskId: string
      type: string
      status: string
      progress: number
      result?: unknown
      error?: string
      cost: number
      model: string
      confidence: number
      createdAt: string
      finishedAt?: string
    }>(`/ai/task/detail/${taskId}`),

  /** 取消任务（POST /ai/task/cancel） */
  taskCancel: (taskId: string) =>
    http.post<{ ok: boolean }>('/ai/task/cancel', { taskId }),

  // ============================================================
  // 字段抽取（/ai/extract/upload · /ai/extract/apply · batch）
  // ============================================================

  /** 单张字段抽取（POST /ai/extract/upload） */
  extractInvoice: (data: { fileId: string; fileUrl: string; type: string; templateId?: string }) =>
    http.post<{
      taskId: string
      type: string
      fields: Record<string, { value: any; confidence: number; bbox?: number[]; needsReview?: boolean }>
      suggestions?: {
        linkToContract?: string
        linkToClient?: string
        linkToProject?: string
      }
      meta: {
        model: string
        version: string
        confidence: number
        durationMs: number
        costCents: number
        traceId: string
      }
    }>('/ai/extract/upload', data),

  /** 采纳 AI 抽取结果（数据回流，POST /ai/extract/apply） */
  extractApply: (data: {
    taskId: string
    type: string
    originalFields: Record<string, any>
    correctedFields: Record<string, any>
    action: 'save-to-form' | 'discard' | 're-extract'
  }) => http.post<{ taskId: string; appliedToForm: boolean; invoiceId?: string }>('/ai/extract/apply', data),

  // ============================================================
  // 风险扫描（/ai/risk/scan · /ai/risk/warnings · /ai/risk/dismiss）
  // ============================================================

  /** 风险扫描（POST /ai/risk/scan） */
  riskScan: <T = any>(data: {
    objectType: 'project' | 'contract' | 'expense' | 'voucher'
    objectId: number
    scanTypes?: string[]
    similarLimit?: number
    deepScan?: boolean
  }) => http.post<T>('/ai/risk/scan', data),

  /** 拉取某对象的所有风险（POST /ai/risk/warnings） */
  riskWarnings: <T = any>(data: {
    objectType: string
    objectId: number
    onlyActive?: boolean
  }) => http.post<T>('/ai/risk/warnings', data),

  /** 忽略/采纳/已修复（POST /ai/risk/dismiss） */
  riskDismiss: (data: {
    warningId: string
    action: 'dismiss' | 'accept' | 'fix'
    remark?: string
  }) => http.post<{ ok: boolean }>('/ai/risk/dismiss', data),

  // ============================================================
  // 智能问答（/ai/ask/*）
  // ============================================================

  /** 自然语言提问（POST /ai/ask/ask） */
  ask: (data: {
    question: string
    context?: { currentPage?: string; conversationId?: string; currentFilters?: any }
    options?: { stream?: boolean; returnChart?: boolean; maxSources?: number }
  }) => http.post<{
    answer: string
    answerType: 'data' | 'doc' | 'chart' | 'draft'
    data?: any
    chart?: any
    sources: Array<{ type: string; id: string; title: string; url: string; snippet: string }>
    conversationId: string
    messageId: string
    meta: { model: string; durationMs: number; tokensUsed: number; costCents: number }
  }>('/ai/ask/ask', data),

  /** 推荐问题（POST /ai/ask/suggestions） */
  askSuggestions: (data: { page?: string; limit?: number }) =>
    http.post<{
      suggestions: Array<{ text: string; icon: string; category: string }>
    }>('/ai/ask/suggestions', data),

  // ============================================================
  // 智能预警（/ai/alert/today · /ai/alert/dismiss）
  // ============================================================

  /** 今日 AI 助手提醒（POST /ai/alert/today） */
  alerts: (data: { limit?: number } = { limit: 10 }) =>
    http.post<{
      total: number
      items: Array<{
        id: string
        level: 'high' | 'medium' | 'low'
        type: string
        title: string
        summary: string
        actionUrl: string
        actionLabel: string
        objectType?: string
        objectId?: number
        createdAt: string
      }>
    }>('/ai/alert/today', data),

  /** 关闭提醒（POST /ai/alert/dismiss） */
  alertDismiss: (data: { alertId: string; snoozeHours?: number }) =>
    http.post<{ ok: boolean }>('/ai/alert/dismiss', data),

  // ============================================================
  // 反馈（/ai/feedback/submit · /ai/ask/feedback）
  // ============================================================

  /** 通用反馈（POST /ai/feedback/submit） */
  feedbackSubmit: (data: {
    targetType: 'extract' | 'risk' | 'ask' | 'generate' | 'match'
    targetId: string
    rating: 'up' | 'down'
    category?: string
    comment?: string
    tags?: string[]
  }) => http.post<{ ok: boolean }>('/ai/feedback/submit', data),

  // ============================================================
  // 模型管理（/ai/model/list · /ai/model/config）
  // ============================================================

  /** 模型列表（POST /ai/model/list） */
  modelList: () =>
    http.post<{
      models: Array<{
        id: string
        name: string
        type: string
        status: 'healthy' | 'degraded' | 'down' | 'disabled'
        version: string
        metrics: { latencyMs: number; accuracy: number; qps: number }
        config: Record<string, any>
        costPerCallCents: number
        monthlyUsage: number
      }>
    }>('/ai/model/list', {}),

  /** 配置模型（POST /ai/model/config） */
  modelConfig: (data: { modelId: string; config: Record<string, any>; enabled?: boolean }) =>
    http.post<{ ok: boolean }>('/ai/model/config', data),

  // ============================================================
  // P1 8 触点新增：AI 一键起草 + 智能匹配（后端等资质，前端 mock 兜底）
  // ============================================================

  /** AI 一键起草（POST /ai/generate/draft，触点 #6 #12） */
  generateDraft: (data: { type: 'contract' | 'reminder' | 'email' | 'notice'; context: Record<string, any>; templateId?: string }) =>
    http.post<{
      taskId: string
      type: string
      draft: {
        title: string
        content: string
        sections: Array<{ heading: string; body: string }>
        fields: Record<string, any>
        confidence: number
        model: string
        durationMs: number
      }
    }>('/ai/generate/draft', data),

  /** AI 智能匹配（POST /ai/match/run，触点 #9） */
  matchRun: (data: { type: 'invoice-to-contract' | 'expense-to-project' | 'contract-to-client'; source: Record<string, any>; candidates?: string[] }) =>
    http.post<{
      taskId: string
      matches: Array<{
        targetId: string
        targetType: string
        targetName: string
        score: number  // 0-1
        reasons: string[]
        meta?: Record<string, any>
      }>
      bestMatchId: string
      model: string
      durationMs: number
    }>('/ai/match/run', data),
}
