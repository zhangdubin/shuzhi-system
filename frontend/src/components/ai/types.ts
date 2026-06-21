// ============================================================
// AI 风险扫描面板类型定义
// 2026-05-21 引入
//
// 与 design/AI-API.md §6.2 risk/scan 严格对齐
// 与 backend/app/modules/ai/schemas.py 保持字段一致
// ============================================================

/** 风险等级（与 .ai-risk-chip 的 3 个变体对应） */
export type RiskLevel = 'low' | 'medium' | 'high'

/** 业务对象类型（可扫描的对象） */
export type ScanObjectType = 'project' | 'contract' | 'expense' | 'voucher'

/** 单维度评分（5 维健康度的一项） */
export interface AiDimension {
  /** 维度名：进度/成本/质量/风险/客户 等 */
  name: string
  /** 分数 0-100 */
  score: number
  /** 权重 0-1 */
  weight: number
  /** 异常描述（无异常时可省略） */
  issues?: string[]
}

/** 风险预警 */
export interface AiWarning {
  id: string
  level: RiskLevel
  /** 业务类型（合同/项目/费用/凭证 各自的子类型） */
  type: string
  title: string
  description: string
  /** AI 建议的处置 */
  suggestion?: string
  /** 置信度 0-100 */
  confidence: number
  /** 证据（支撑这个警告的数据） */
  dataPoints?: Record<string, any>
  createdAt: string
}

/** AI 建议（可执行动作） */
export interface AiSuggestion {
  id: string
  title: string
  description: string
  /** 置信度 0-100 */
  confidence: number
  /** 可执行动作（前端根据 type 渲染按钮） */
  action?: {
    type: string
    params?: Record<string, any>
  }
}

/** 相似对象（横向对比） */
export interface AiSimilarObject {
  objectType: ScanObjectType
  objectId: number
  name: string
  /** 健康分 0-100 */
  healthScore: number
  /** 延期天数（正数=延期，负数=提前，0=准时） */
  delayDays?: number
  /** 超支率（小数，0.08 = 8%） */
  overBudget?: number
  /** 是否是当前对象（用于高亮） */
  isCurrent?: boolean
}

/** AI 异常事件时间线 */
export interface AiTimelineEvent {
  /** 距今描述，如 "2 小时前" */
  time: string
  /** 时间戳（用于排序，可选） */
  timestamp?: string
  text: string
  level?: RiskLevel
}

/** 风险扫描完整结果（与 AI-API.md §6.2.1 response 对齐） */
export interface AiScanResult {
  objectType: ScanObjectType
  objectId: number
  /** 综合健康分 0-100 */
  overallScore: number
  /** 综合风险等级 */
  riskLevel: RiskLevel
  /** 5 维评分（5 个 dimension） */
  dimensions: AiDimension[]
  /** 风险预警列表 */
  warnings: AiWarning[]
  /** AI 建议列表 */
  suggestions: AiSuggestion[]
  /** 相似对象对比 */
  similarObjects?: AiSimilarObject[]
  /** AI 异常事件时间线 */
  timeline?: AiTimelineEvent[]
  /** AI 元信息（成本/耗时/模型） */
  meta: {
    model: string
    version: string
    durationMs: number
    costCents: number
    confidence: number
  }
  /** 最后扫描时间（用于"是否需要重新扫描"判断） */
  scannedAt?: string
}

/** 组件 Props */
export interface AiRiskScanPanelProps {
  /** 要扫描的对象类型 */
  objectType: ScanObjectType
  /** 要扫描的对象 ID */
  objectId: number
  /** 是否自动加载（默认 true） */
  autoLoad?: boolean
  /** 相似对象对比数（默认 3） */
  similarLimit?: number
  /** 是否深度扫描（慢但准） */
  deepScan?: boolean
}

/** 组件 Emits */
export interface AiRiskScanPanelEmits {
  /** 扫描完成 */
  (e: 'loaded', result: AiScanResult): void
  /** 扫描失败 */
  (e: 'error', err: Error): void
  /** 用户采纳了某条建议 */
  (e: 'accept-suggestion', suggestion: AiSuggestion): void
  /** 用户忽略了某条风险 */
  (e: 'dismiss-warning', warning: AiWarning): void
  /** 反馈（👍/👎） */
  (e: 'feedback', payload: { rating: 'up' | 'down'; comment?: string }): void
}
