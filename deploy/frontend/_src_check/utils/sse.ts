// ============================================================
// SSE 客户端（与后端 core/sse.py 协议对齐）
// 2026-05-21 引入
//
// 用法：
//   const close = sse.connect('/api/v1/ai/extract/batch/stream?batchId=xxx', {
//     progress: (data) => console.log(data),
//     extracted: (data) => console.log(data),
//     completed: () => close(),
//     error: (e) => console.error(e),
//   })
//
// 重要：EventSource 不支持自定义 header，token 走 query string
// ============================================================

import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api/v1'

export interface SSEHandlers {
  /** 任意事件名 → 处理函数 */
  [event: string]: (data: any, event: MessageEvent) => void
}

export interface SSEOptions {
  /** 自动重连（默认 true） */
  reconnect?: boolean
  /** 重连延迟（ms，默认 3000） */
  reconnectDelay?: number
  /** 最大重连次数（默认 5） */
  maxReconnect?: number
  /** 失败回调 */
  onError?: (err: any) => void
  /** 重连回调 */
  onReconnect?: (attempt: number) => void
}

class SSEClient {
  /**
   * 订阅一个 SSE 端点
   * @param path 形如 '/api/v1/ai/extract/batch/stream'（不带 query）
   * @param handlers 事件处理函数
   * @param options 重连等配置
   * @returns 关闭函数
   */
  connect(path: string, handlers: SSEHandlers, options: SSEOptions = {}): () => void {
    const {
      reconnect = true,
      reconnectDelay = 3000,
      maxReconnect = 5,
      onError,
      onReconnect,
    } = options

    const userStore = useUserStore()
    const token = userStore.token || ''

    // EventSource 不支持自定义 header → token 走 query string
    // （后端需要在 SSE 鉴权时读 query 里的 token，详见 design/AI-API.md §3）
    const separator = path.includes('?') ? '&' : '?'
    const url = `${API_BASE}${path}${separator}token=${encodeURIComponent(token)}`

    let es: EventSource | null = null
    let closed = false
    let attempts = 0

    const open = () => {
      if (closed) return
      es = new EventSource(url)

      // 绑定事件
      Object.entries(handlers).forEach(([event, fn]) => {
        if (event === 'error' || event === 'reconnect') return  // 系统事件单独处理
        es!.addEventListener(event, (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data)
            fn(data, e)
          } catch (err) {
            console.warn(`[SSE] 事件 ${event} 数据解析失败:`, e.data, err)
            fn(e.data, e)  // 兜底：原样传字符串
          }
        })
      })

      // 系统事件：连接成功
      es.addEventListener('connected', () => {
        attempts = 0  // 重置重连次数
      })

      // 系统事件：连接错误
      es.addEventListener('error', (e: any) => {
        if (closed) return
        if (es?.readyState === EventSource.CLOSED) {
          // 主动关闭
          return
        }

        // 网络错误 / 服务端断开
        if (attempts < maxReconnect && reconnect) {
          attempts++
          onReconnect?.(attempts)
          es?.close()
          setTimeout(open, reconnectDelay)
        } else {
          onError?.(e)
          ElMessage.warning('SSE 连接中断，已达最大重试次数')
          handlers.error?.(e, e as any)
          es?.close()
        }
      })
    }

    open()

    // 返回关闭函数
    return () => {
      closed = true
      es?.close()
    }
  }

  /**
   * 高阶封装：自动清理 + 组件卸载时调用
   * 用法：
   *   onMounted(() => {
   *     cleanup = sse.autoConnect(...)
   *   })
   *   onUnmounted(() => cleanup?.())
   */
  autoConnect(
    path: string,
    handlers: SSEHandlers,
    options?: SSEOptions
  ): () => void {
    return this.connect(path, handlers, options)
  }

  /**
   * 单次短连接（只读取 completed/error 后自动关闭）
   * 适合"提问等结果"这种一次性场景
   */
  once<T = any>(
    path: string,
    eventName = 'completed'
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const userStore = useUserStore()
      const token = userStore.token || ''
      const separator = path.includes('?') ? '&' : '?'
      const url = `${API_BASE}${path}${separator}token=${encodeURIComponent(token)}`

      const es = new EventSource(url)

      const cleanup = () => {
        es.close()
      }

      es.addEventListener(eventName, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data)
          resolve(data as T)
        } catch {
          resolve(e.data as T)
        }
        cleanup()
      })

      es.addEventListener('error', (e: any) => {
        if (es.readyState === EventSource.CLOSED) return
        reject(new Error('SSE 连接失败'))
        cleanup()
      })
    })
  }
}

export const sse = new SSEClient()

/**
 * 通用进度订阅（高频场景）
 * 用于批量任务（OCR/AI抽取/扫描）
 */
export interface ProgressHandlers {
  /** 单条完成 */
  onItem?: (item: any) => void
  /** 进度更新 */
  onProgress?: (progress: { done: number; total: number; percent: number; stage?: string }) => void
  /** 全部完成 */
  onCompleted?: (summary: any) => void
  /** 出错 */
  onError?: (err: any) => void
}

export function watchTask(
  taskId: string,
  handlers: ProgressHandlers,
  options?: SSEOptions
): () => void {
  return sse.connect(
    `/api/v1/ai/task/stream/${taskId}`,
    {
      // 兼容两种事件名
      progress: (data) => handlers.onProgress?.(data),
      item_done: (data) => handlers.onItem?.(data),
      extracted: (data) => handlers.onItem?.(data),
      completed: (data) => {
        handlers.onCompleted?.(data)
      },
      error: (data) => handlers.onError?.(data),
    },
    options
  )
}
