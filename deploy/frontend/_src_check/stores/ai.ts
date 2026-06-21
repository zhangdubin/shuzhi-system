// ============================================================
// AI 状态管理 store（Phase 1，2026-05-21 引入）
//
// 职责：
// 1. 全局任务列表（用于"任务中心"页面 + Dashboard 提醒）
// 2. 今日 AI 提醒（用于 Dashboard 顶部提醒条）
// 3. 当前活跃的 SSE 订阅（用于关闭/重连）
// 4. AI 偏好（用户反馈后的学习）
// ============================================================

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { aiApi } from '@/api/ai'

export interface AiTask {
  id: number
  taskId: string
  type: string          // 'extract' | 'risk' | 'match' | 'agent'
  status: string        // 'pending' | 'running' | 'done' | 'failed'
  cost: number
  model: string
  confidence: number
  createdAt: string
  finishedAt?: string
  progress?: number
  result?: unknown
  error?: string
}

export interface AiAlert {
  id: string
  level: 'high' | 'medium' | 'low'
  type: string
  title: string
  summary: string
  actionUrl?: string
  actionLabel?: string
  objectType?: string
  objectId?: number
  read?: boolean
  createdAt: string
}

export const useAiStore = defineStore('ai', () => {
  // ---------- 状态 ----------
  /** 任务列表（最近 50 条） */
  const tasks = ref<AiTask[]>([])
  /** 今日 AI 提醒（最多 3 条） */
  const alerts = ref<AiAlert[]>([])
  /** 未读提醒数 */
  const unreadCount = ref(0)
  /** 加载状态 */
  const loading = ref({
    tasks: false,
    alerts: false,
  })

  // ---------- 计算属性 ----------
  /** 进行中的任务数 */
  const runningTaskCount = computed(
    () => tasks.value.filter((t) => t.status === 'running' || t.status === 'pending').length
  )

  /** 今日总成本（元） */
  const todayCost = computed(() => {
    const today = new Date().toISOString().slice(0, 10)
    return tasks.value
      .filter((t) => t.createdAt?.startsWith(today))
      .reduce((sum, t) => sum + (t.cost || 0), 0)
  })

  // ---------- Actions ----------

  /** 加载任务列表 */
  async function loadTasks(params?: { status?: string; type?: string }) {
    loading.value.tasks = true
    try {
      const data = await aiApi.tasks({ page: 1, pageSize: 50, ...params })
      tasks.value = data.list || []
    } catch (e) {
      // 容错：后端暂时没有 → 用空数组
      tasks.value = []
      console.warn('[aiStore] 任务列表加载失败', e)
    } finally {
      loading.value.tasks = false
    }
  }

  /** 加载今日 AI 提醒 */
  async function loadAlerts() {
    loading.value.alerts = true
    try {
      const data = await aiApi.alerts({ limit: 10 })
      // 后端返回 {id, type, level, title, summary, actionUrl, actionLabel, createdAt}
      // 已是 AiAlert 格式，直接用
      alerts.value = (data.items || []).map((a: any) => ({
        id: a.id,
        level: a.level,
        type: a.type,
        title: a.title,
        summary: a.summary || '',
        actionUrl: a.actionUrl,
        actionLabel: a.actionLabel,
        read: false,
        createdAt: a.createdAt,
      }))
      unreadCount.value = alerts.value.filter((a) => !a.read).length
    } catch (e) {
      alerts.value = []
      unreadCount.value = 0
      console.warn('[aiStore] 提醒加载失败', e)
    } finally {
      loading.value.alerts = false
    }
  }

  /** 标记单条已读 */
  function markRead(alertId: number | string) {
    const alert = alerts.value.find((a) => a.id === alertId)
    if (alert && !alert.read) {
      alert.read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }

  /** 全部已读 */
  function markAllRead() {
    alerts.value.forEach((a) => (a.read = true))
    unreadCount.value = 0
  }

  /** 忽略单条 */
  function dismiss(alertId: number | string) {
    alerts.value = alerts.value.filter((a) => a.id !== alertId)
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }

  /** 提交 AI 反馈（用于模型迭代） */
  async function submitFeedback(payload: {
    targetType: 'extract' | 'risk' | 'ask' | 'generate' | 'match'
    targetId: string
    rating: 'up' | 'down'
    category?: string
    comment?: string
    tags?: string[]
  }) {
    await aiApi.feedbackSubmit(payload).catch((e) => {
      console.warn('[aiStore] 反馈提交失败', e)
    })
  }

  /** 触发一次发票抽取（异步任务） */
  async function extractInvoice(payload: { fileId: string; fileUrl: string; type?: string }) {
    const res = await aiApi.extractInvoice({
      fileId: payload.fileId,
      fileUrl: payload.fileUrl,
      type: payload.type || 'invoice',
    })
    // 触发后立即刷一次任务列表
    await loadTasks()
    return res
  }

  return {
    // 状态
    tasks,
    alerts,
    unreadCount,
    loading,
    // 计算
    runningTaskCount,
    todayCost,
    // Actions
    loadTasks,
    loadAlerts,
    markRead,
    markAllRead,
    dismiss,
    submitFeedback,
    extractInvoice,
  }
})
