// ============================================================
// 认证 API
// ============================================================
import { http } from '@/utils/request'
import type { LoginReq, LoginRes, UserInfo } from '@/types/api'

export const authApi = {
  /** 登录 */
  login: (data: LoginReq) => http.post<LoginRes>('/auth/login', data),

  /** 登出 */
  logout: () => http.post<{ message: string }>('/auth/logout'),

  /** 刷新 token */
  refresh: (refreshToken: string) =>
    http.post<{ token: string; refreshToken: string }>('/auth/refresh', { refreshToken }),

  /** 当前用户信息 */
  me: () => http.get<UserInfo>('/auth/me'),
}
