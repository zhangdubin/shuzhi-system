// ============================================================
// API 基础类型
// ============================================================

/** 后端统一响应（部分接口如登录直接返业务对象，无包装） */
export interface ApiResponse<T = unknown> {
  code: number
  data: T
  message?: string
  traceId?: string
}

/** 业务码 0 = 成功 */
export const SUCCESS_CODE = 0

/** 分页请求 */
export interface PageReq {
  page?: number
  pageSize?: number
  keyword?: string
  [key: string]: unknown
}

/** 分页响应 */
export interface PageRes<T = unknown> {
  list: T[]
  total: number
  page: number
  pageSize: number
}

/** 用户信息 */
export interface UserInfo {
  userId: number
  name: string
  avatar?: string | null
  role: string
  department: string
  permissions?: string[]
}

/** 登录请求 */
export interface LoginReq {
  account: string
  password: string
  /** 记住我（7 天免登录） */
  remember?: boolean
}

/** 登录响应（直接业务对象，无 code 包装） */
export interface LoginRes {
  token: string
  refreshToken: string
  expiresIn: number
  userInfo: UserInfo
}
