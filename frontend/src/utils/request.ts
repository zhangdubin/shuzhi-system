// ============================================================
// Axios 封装：拦截器 + Token + 错误码映射
// ============================================================
import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import { useUserStore } from '@/stores/user'
import type { ApiResponse } from '@/types/api'

const BASE = (import.meta.env?.VITE_API_BASE as string | undefined) || '/api/v1'

NProgress.configure({ showSpinner: false, easing: 'ease', speed: 500 })

const service: AxiosInstance = axios.create({
  baseURL: BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// ---------- 请求拦截器 ----------
service.interceptors.request.use(
  (config) => {
    NProgress.start()
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (error) => {
    NProgress.done()
    return Promise.reject(error)
  }
)

// ---------- 响应拦截器 ----------
service.interceptors.response.use(
  (response: AxiosResponse) => {
    NProgress.done()
    const silent = (response.config as any)?.silent === true
    const res = response.data
    // 业务对象无 code 包装（登录、文件下载等）→ 直接返回 data
    if (res === null || res === undefined || typeof res !== 'object' || !('code' in res)) {
      return res
    }
    // 标准 {code, data, message} 包装
    const apiRes = res as ApiResponse
    if (apiRes.code === 0) {
      return apiRes.data
    }
    // 业务错误
    if (!silent) handleBusinessError(apiRes.code, apiRes.message)
    return Promise.reject(new Error(apiRes.message || `业务错误 ${apiRes.code}`))
  },
  (error: AxiosError) => {
    NProgress.done()
    const silent = (error.config as any)?.silent === true
    if (!silent) handleHttpError(error)
    return Promise.reject(error)
  }
)

// ---------- 错误处理 ----------
/** 401 会话过期弹窗去重：sessionStorage 跨标签页持久化
 *  解决：登录页内或跳转后还有 in-flight 请求返回 401 → 反复弹窗 */
const SS_KEY_401 = 'shuzhi_401_shown'
function is401DialogShown(): boolean {
  try { return sessionStorage.getItem(SS_KEY_401) === '1' } catch { return false }
}
function mark401DialogShown(): void {
  try { sessionStorage.setItem(SS_KEY_401, '1') } catch {}
}
function clear401DialogMark(): void {
  try { sessionStorage.removeItem(SS_KEY_401) } catch {}
}

function handleBusinessError(code: number, message?: string) {
  // 3001=业务限流 5101=AI模型 5102=AI超时 5103=AI安全 5104=AI格式
  const text = message || businessCodeText(code)
  if ([3001, 5101, 5102, 5103, 5104].includes(code)) {
    ElMessage.warning(text)
  } else {
    ElMessage.error(text)
  }
}

function handleHttpError(error: AxiosError) {
  const status = error.response?.status
  const userStore = useUserStore()
  const isLoginPage = window.location.pathname.startsWith('/login')

  if (status === 401) {
    userStore.clearLocal()
    // 登录页 / 已弹过 → 静默处理，不弹窗
    if (isLoginPage || is401DialogShown()) {
      return
    }
    mark401DialogShown()
    ElMessageBox.confirm('登录已过期，请重新登录', '会话过期', {
      confirmButtonText: '重新登录',
      cancelButtonText: '取消',
      type: 'warning',
    })
      .then(() => { clear401DialogMark(); window.location.href = '/login' })
      .catch(() => { clear401DialogMark(); window.location.href = '/login' })
  } else if (status === 403) {
    ElMessage.error('没有权限访问')
  } else if (status === 404) {
    ElMessage.error('资源不存在')
  } else if (status && status >= 500) {
    ElMessage.error('服务异常，请稍后再试')
  } else {
    ElMessage.error(error.message || '网络异常')
  }
}

function businessCodeText(code: number): string {
  const map: Record<number, string> = {
    1001: '参数校验失败',
    1002: '资源不存在',
    1003: '资源冲突',
    2001: '未授权',
    2002: '无权限',
    2003: '禁止访问',
    3001: '操作过于频繁',
    4001: '业务规则校验失败',
    5001: '系统异常',
    5002: '外部服务调用失败',
    5101: 'AI 模型暂不可用',
    5102: 'AI 处理超时',
    5103: 'AI 内容安全审核未通过',
    5104: 'AI 返回格式异常',
  }
  return map[code] || `业务错误 ${code}`
}

// ---------- 业务方法（强类型） ----------
export interface RequestOptions extends AxiosRequestConfig {
  /** 跳过全局错误提示（业务层自行处理） */
  silent?: boolean
}

/**
 * 通用 request：自动 unwrap data
 */
export function request<T = unknown>(config: RequestOptions): Promise<T> {
  return service.request<unknown, T>(config)
}

export const http = {
  get: <T = unknown>(url: string, params?: object, config?: RequestOptions) =>
    request<T>({ method: 'GET', url, params, ...config }),
  post: <T = unknown>(url: string, data?: object, config?: RequestOptions) =>
    request<T>({ method: 'POST', url, data, ...config }),
  put: <T = unknown>(url: string, data?: object, config?: RequestOptions) =>
    request<T>({ method: 'PUT', url, data, ...config }),
  delete: <T = unknown>(url: string, params?: object, config?: RequestOptions) =>
    request<T>({ method: 'DELETE', url, params, ...config }),
  upload: <T = unknown>(url: string, formData: FormData, config?: RequestOptions) =>
    request<T>({
      method: 'POST',
      url,
      data: formData,
      headers: { 'Content-Type': 'multipart/form-data' },
      ...config,
    }),
}

export default service
