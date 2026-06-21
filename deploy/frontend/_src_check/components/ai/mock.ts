// ============================================================
// AI 风险扫描 Mock 数据
// 用于前端独立调试（不需要启动后端）
//
// 用法（在 .vue 中）：
//   import { mockRiskScanResult } from '@/components/ai/mock'
//   aiApi.riskScan = async () => mockRiskScanResult
// ============================================================

import type { AiScanResult } from './types'

export const mockRiskScanResult: AiScanResult = {
  objectType: 'contract',
  objectId: 123,
  overallScore: 72,
  riskLevel: 'medium',
  dimensions: [
    { name: '条款完整', score: 78, weight: 0.25 },
    { name: '付款条件', score: 55, weight: 0.20, issues: ['预计超支 8%'] },
    { name: '法务合规', score: 62, weight: 0.20 },
    { name: '金额风险', score: 88, weight: 0.15 },
    { name: '客户资质', score: 92, weight: 0.20 },
  ],
  warnings: [
    {
      id: 'w_1',
      level: 'high',
      type: 'payment_period',
      title: '付款周期短于行业平均 33%',
      description: '约定"月结 30 天"，行业 SaaS 合同平均为 45 天。客户付款压力大 → 我方回款风险增加。',
      suggestion: '建议与客户协商延至 45 天（基于 12 个相似合同，回款及时率可提升 22%）。',
      confidence: 88,
      dataPoints: { clause: '3.2', industryBenchmark: 45 },
      createdAt: '2026-05-21T10:00:00',
    },
    {
      id: 'w_2',
      level: 'high',
      type: 'penalty_missing',
      title: '未约定违约金条款',
      description: '逾期付款无任何约束。一旦客户拖欠 3 个月以上，维权成本（诉讼+利息）可能超过合同金额本身。',
      suggestion: '补充"逾期 0.05%/天"违约金条款（法务库 v3.2 标准模板）。',
      confidence: 92,
      dataPoints: { clause: '3.2', hasPenalty: false },
      createdAt: '2026-05-21T10:00:00',
    },
    {
      id: 'w_3',
      level: 'medium',
      type: 'data_ownership',
      title: '数据归属与保密期未约定',
      description: '涉及客户业务数据归属、保密期限不明确。服务终止后，可能产生数据迁移纠纷。',
      suggestion: '补充"数据归属 + 3 年保密期"条款（法务库 v3.2 通用 SaaS 模板）。',
      confidence: 85,
      dataPoints: { clause: '5', hasDataClause: false },
      createdAt: '2026-05-21T10:00:00',
    },
  ],
  suggestions: [
    {
      id: 's_1',
      title: '与客户协商付款周期延至 45 天',
      description: '基于 12 个相似 SaaS 合同，付款周期从 30 → 45 天，<strong>回款及时率提升 22%</strong>，且不影响签约率（下降仅 3%）。',
      confidence: 88,
      action: { type: 'send-email', params: { template: 'payment-period-extension' } },
    },
    {
      id: 's_2',
      title: '补充"逾期 0.05%/天"违约金条款',
      description: '参考法务部标准条款库 v3.2。AI 已生成 v2 合同草稿，新增第 3.3 条。',
      confidence: 92,
      action: { type: 'update-status', params: { assignee: '王芳' } },
    },
    {
      id: 's_3',
      title: '补充"数据归属 + 3 年保密"条款',
      description: '客户业务数据归客户所有，我方留存 90 天用于服务支持，保密期 3 年。参考模板：法务库 v3.2 通用 SaaS 模板。',
      confidence: 85,
    },
  ],
  similarObjects: [
    { objectType: 'contract', objectId: 123, name: 'HT-2026-031（当前）', healthScore: 72, delayDays: 0, overBudget: 0.08, isCurrent: true },
    { objectType: 'contract', objectId: 100, name: 'HT-2025-118（万象续约）', healthScore: 88, delayDays: 0, overBudget: -0.02 },
    { objectType: 'contract', objectId: 203, name: 'HT-2025-203（智云）', healthScore: 91, delayDays: -2, overBudget: 0.05 },
    { objectType: 'contract', objectId: 89, name: 'HT-2026-089（远见）', healthScore: 68, delayDays: 18, overBudget: 0.15 },
  ],
  timeline: [
    { time: '2 小时前', text: '⚠️ 销售 <strong>王芳</strong> 提交合同时，付款周期从 45 → 30 天（<span style="color:var(--color-danger);">-15 天</span>）' },
    { time: '昨天 16:42', text: '📉 与去年同期合同 HT-2025-118 对比，<strong>违约金条款被删除</strong>' },
    { time: '昨天', text: '🤖 AI 完成首次扫描，识别出 3 个中高风险' },
    { time: '2 天前', text: '📝 商务 <strong>王芳</strong> 创建合同（来自销售线索 L-2026-128）' },
    { time: '1 周前', text: '✅ 客户<strong>万象科技</strong>信用评级：A（基于 3 年合作历史）' },
  ],
  meta: {
    model: 'risk-v2.3',
    version: '2.3.1',
    durationMs: 320,
    costCents: 1,
    confidence: 91,
  },
  scannedAt: '2026-05-21T10:23:18',
}
