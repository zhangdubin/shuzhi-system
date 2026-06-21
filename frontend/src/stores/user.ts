// ============================================================
// 用户 / 认证 store
// ============================================================
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { LoginReq, UserInfo } from '@/types/api'

const TOKEN_KEY = 'shuzhi_token'
const REFRESH_KEY = 'shuzhi_refresh'
const USER_KEY = 'shuzhi_user'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
  const refreshToken = ref<string>(localStorage.getItem(REFRESH_KEY) || '')
  const userInfo = ref<UserInfo | null>(
    (() => {
      const s = localStorage.getItem(USER_KEY)
      return s ? JSON.parse(s) : null
    })()
  )

  const isLoggedIn = computed(() => !!token.value)
  const permissions = computed<string[]>(() => userInfo.value?.permissions || [])

  /** 登录 */
  async function login(req: LoginReq) {
    const res = await authApi.login(req)
    token.value = res.token
    refreshToken.value = res.refreshToken
    userInfo.value = res.userInfo
    localStorage.setItem(TOKEN_KEY, res.token)
    localStorage.setItem(REFRESH_KEY, res.refreshToken)
    localStorage.setItem(USER_KEY, JSON.stringify(res.userInfo))
    return res
  }

  /** 拉取当前用户 */
  async function fetchMe() {
    const me = await authApi.me()
    userInfo.value = me
    localStorage.setItem(USER_KEY, JSON.stringify(me))
    return me
  }

  /** 登出 */
  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // 忽略后端报错，本地清空即可
    }
    clearLocal()
  }

  function clearLocal() {
    token.value = ''
    refreshToken.value = ''
    userInfo.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(USER_KEY)
  }

  /** 权限判断 */
  function hasPerm(code: string): boolean {
    if (!code) return true
    // super admin 自动放行：isAdmin=true 或 permissions 包含 '*' 或 code 是 'admin'
    if (userInfo.value?.isAdmin) return true
    if (permissions.value.includes('*')) return true
    if (code === 'admin') return !!userInfo.value?.isAdmin
    return permissions.value.includes(code)
  }

  /** 是否超级管理员 */
  const isAdmin = computed(() => !!userInfo.value?.isAdmin)

  return {
    token,
    refreshToken,
    userInfo,
    isLoggedIn,
    permissions,
    isAdmin,
    login,
    fetchMe,
    logout,
    clearLocal,
    hasPerm,
  }
})
