/**
 * 强类型 SDK - 基于 OpenAPI 自动生成的 schema
 * 使用方式：
 *   import { sdk } from '@/api/sdk'
 *   const r = await sdk.contracts.list({ page: 1, pageSize: 20 })
 *   // r.data.list[0] 强类型 Contract
 */
import { http } from '@/utils/request'

// 业务类型（手写 + 标注 openapi 来源）
// 这些类型与后端 Pydantic schema 一一对应，可由 scripts/gen-sdk.js 自动生成
export interface Contract {
  contractId: number
  code: string
  name: string
  type: string
  status: 'draft' | 'pending' | 'approving' | 'approved' | 'rejected' | 'signed'
  clientId: number
  clientName?: string
  managerId: number
  managerName?: string
  amount: number
  currency?: string
  signDate: string
  effectiveDate?: string
  expireDate?: string
  paymentMethod?: string
  paymentTerm?: string
  description?: string
  createdAt: string
  updatedAt: string
  [k: string]: any
}

export interface ContractCreate {
  code?: string
  name: string
  type: string
  clientId: number
  managerId?: number
  amount: number
  currency?: string
  signDate: string
  effectiveDate?: string
  expireDate?: string
  paymentMethod?: string
  paymentTerm?: string
  description?: string
  [k: string]: any
}

export interface ContractApproveRequest {
  contractId: number
  action: 'approve' | 'reject' | 'transfer'
  comment?: string
  transferTo?: number
}

export interface Expense {
  expenseId: number
  code: string
  title: string
  category: string
  amount: number
  status: 'draft' | 'pending' | 'approving' | 'approved' | 'rejected'
  applicantId?: number
  applicantName?: string
  departmentId?: number
  departmentName?: string
  contractId?: number
  projectId?: number
  expenseDate: string
  description?: string
  createdAt: string
  updatedAt: string
  [k: string]: any
}

export interface ExpenseCreate {
  title: string
  category: string
  amount: number
  expenseDate: string
  description?: string
  contractId?: number
  projectId?: number
  breakdown?: any[]
  attachmentIds?: string[]
  [k: string]: any
}

export interface ExpenseUpdate {
  title?: string
  category?: string
  amount?: number
  expenseDate?: string
  description?: string
  [k: string]: any
}

export interface ExpenseApproveRequest {
  expenseId: number
  action: 'approve' | 'reject' | 'transfer'
  comment?: string
  transferTo?: number
}

export interface Receivable {
  receivableId: number
  code: string
  contractId: number
  contractCode?: string
  clientId: number
  clientName?: string
  planAmount: number
  receivedAmount: number
  planDate: string
  actualDate?: string
  status: 'pending' | 'partial' | 'received' | 'overdue' | 'cancelled'
  receivableType?: string
  managerId?: number
  managerName?: string
  remarks?: string
  createdAt: string
  updatedAt: string
  [k: string]: any
}

export interface ReceivableCreate {
  contractId: number
  clientId: number
  planAmount: number
  planDate: string
  receivableType?: string
  managerId?: number
  remarks?: string
  [k: string]: any
}

export interface ReceivableUpdate {
  planAmount?: number
  planDate?: string
  receivableType?: string
  managerId?: number
  remarks?: string
  [k: string]: any
}

export interface Project {
  projectId: number
  code: string
  name: string
  clientId: number
  clientName?: string
  managerId: number
  managerName?: string
  type: string
  status: 'planning' | 'active' | 'in_progress' | 'paused' | 'completed' | 'cancelled'
  startDate?: string
  endDate?: string
  budget?: number
  description?: string
  createdAt: string
  updatedAt: string
  [k: string]: any
}

export interface Client {
  clientId: number
  code: string
  name: string
  level: 'A' | 'B' | 'C' | 'D'
  industry?: string
  taxNo?: string
  contactName?: string
  contactPhone?: string
  contactEmail?: string
  address?: string
  status: 'active' | 'inactive' | 'blacklist'
  createdAt: string
  updatedAt: string
  [k: string]: any
}

export interface UserInfo {
  userId: number
  name: string
  avatar?: string | null
  role: string
  department?: string
  permissions: string[]
}

export interface LoginResponse {
  token: string
  refreshToken?: string
  expiresIn: number
  userInfo: UserInfo
}

export type PageReq = {
  page?: number
  pageSize?: number
  keyword?: string
  filters?: Record<string, any>
  [k: string]: any
}

export type PageRes<T> = { list: T[]; total: number; page?: number; pageSize?: number }

export const sdk = {
  // ==================== 合同 ====================
  contracts: {
    list: (data: PageReq) =>
      http.post<PageRes<Contract>>('/contracts/list', data),
    detail: (contractId: number) =>
      http.post<Contract>('/contracts/detail', {}, { params: { contractId } }),
    create: (data: Partial<ContractCreate>) =>
      http.post<Contract>('/contracts/create', data),
    update: (contractId: number, data: Partial<ContractCreate>) =>
      http.post<Contract>('/contracts/update', data, { params: { contractId } }),
    delete: (contractId: number) =>
      http.post(`/contracts/delete`, undefined, { params: { contractId } }),
    submit: (contractId: number) =>
      http.post(`/contracts/submit`, undefined, { params: { contractId } }),
    approve: (data: { contractId: number; action: 'approve' | 'reject' | 'transfer'; comment?: string; transferTo?: number }) =>
      http.post('/contracts/approve', data),
    stats: () => http.post<any>('/contracts/stats', {}),
  },

  // ==================== 费用 ====================
  expenses: {
    list: (data: PageReq) =>
      http.post<PageRes<Expense>>('/expenses/list', data),
    detail: (expenseId: number) =>
      http.post<Expense>('/expenses/detail', undefined, { params: { expenseId } }),
    create: (data: Partial<ExpenseCreate>) =>
      http.post<Expense>('/expenses/create', data),
    update: (expenseId: number, data: Partial<ExpenseUpdate>) =>
      http.post<Expense>('/expenses/update', data, { params: { expenseId } }),
    delete: (expenseId: number) =>
      http.post(`/expenses/delete`, undefined, { params: { expenseId } }),
    submit: (expenseId: number) =>
      http.post(`/expenses/submit`, undefined, { params: { expenseId } }),
    approve: (data: { expenseId: number; action: 'approve' | 'reject' | 'transfer'; comment?: string; transferTo?: number }) =>
      http.post('/expenses/approve', data),
    stats: () => http.post<any>('/expenses/stats', {}),
  },

  // ==================== 回款 ====================
  receivables: {
    list: (data: PageReq) =>
      http.post<PageRes<Receivable>>('/receivables/list', data),
    detail: (receivableId: number) =>
      http.post<Receivable>('/receivables/detail', undefined, { params: { receivableId } }),
    create: (data: Partial<ReceivableCreate>) =>
      http.post<Receivable>('/receivables/create', data),
    update: (receivableId: number, data: Partial<ReceivableUpdate>) =>
      http.post<Receivable>('/receivables/update', data, { params: { receivableId } }),
    delete: (receivableId: number) =>
      http.post(`/receivables/delete`, undefined, { params: { receivableId } }),
    remind: (receivableId: number) =>
      http.post(`/receivables/remind`, undefined, { params: { receivableId } }),
    receive: (data: { receivableId: number; receivedAmount: number; receivedDate?: string; remark?: string }) =>
      http.post('/receivables/receive', data),
    stats: () => http.post<any>('/receivables/stats', {}),
  },

  // ==================== 项目 ====================
  projects: {
    list: (data: PageReq) =>
      http.post<PageRes<Project>>('/projects/list', data),
    detail: (projectId: number) =>
      http.post<Project>('/projects/detail', undefined, { params: { projectId } }),
    create: (data: Partial<Project>) => http.post<Project>('/projects/create', data),
    update: (projectId: number, data: Partial<Project>) =>
      http.post<Project>('/projects/update', data, { params: { projectId } }),
    delete: (projectId: number) =>
      http.post(`/projects/delete`, undefined, { params: { projectId } }),
    addMilestone: (data: any) => http.post('/projects/milestone/add', data),
    stats: () => http.post<any>('/projects/stats', {}),
  },

  // ==================== 客户 ====================
  clients: {
    list: (data: PageReq) => http.post<PageRes<Client>>('/common/clients', data),
    detail: (clientId: number) =>
      http.post<Client>('/common/clients/detail', {}, { params: { clientId } }),
    create: (data: Partial<Client>) => http.post<Client>('/common/clients/create', data),
    update: (clientId: number, data: Partial<Client>) =>
      http.post<Client>('/common/clients/update', data, { params: { clientId } }),
    delete: (clientId: number) =>
      http.post(`/common/clients/delete`, {}, { params: { clientId } }),
  },

  // ==================== 通用 ====================
  common: {
    dict: (dictType: string) =>
      http.get<{ code: 0; data: { list: any[]; total: number } }>('/common/dict', { dictType }),
    projectsRef: () => http.post<{ code: 0; data: { list: Project[]; total: number } }>('/common/projects/ref', {}),
    contractsRef: () => http.post<{ code: 0; data: { list: Contract[]; total: number } }>('/common/contracts/ref', {}),
    users: () => http.post<{ code: 0; data: { list: any[]; total: number } }>('/common/users', {}),
    upload: (formData: FormData) =>
      http.post<{ code: 0; data: { url: string; fileId: string } }>('/common/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }),
  },

  // ==================== Auth ====================
  auth: {
    login: (data: { account: string; password: string; rememberMe?: boolean }) =>
      http.post<LoginResponse>('/auth/login', data),
    me: () => http.get<UserInfo>('/auth/me'),
    logout: () => http.post<{ code: 0; data: any }>('/auth/logout', {}),
    passwordResetRequest: (data: { account: string; verifyType: 'email' | 'sms' }) =>
      http.post('/auth/password/reset/request', data),
    passwordResetConfirm: (data: any) =>
      http.post('/auth/password/reset/confirm', data),
  },

  // ==================== Dashboard ====================
  dashboard: {
    summary: () => http.post<any>('/dashboard/summary', {}),
    activities: (data: { page?: number; pageSize?: number } = {}) =>
      http.post<{ list: any[]; total: number }>('/dashboard/activities', data),
  },

  // ==================== AI ====================
  ai: {
    tasks: (data: { page?: number; pageSize?: number; status?: string; type?: string } = {}) =>
      http.post<{ list: any[]; total: number }>('/ai/task/list', data),
    taskCancel: (taskId: string) =>
      http.post<{ ok: boolean }>('/ai/task/cancel', { taskId }),
    ask: (data: { question: string }) =>
      http.post<{ answer: string; sql?: string; chartType?: string; sources?: any[] }>('/ai/ask/ask', data),
    askSuggestions: (data: { page?: string; limit?: number } = {}) =>
      http.post<{ suggestions: string[] }>('/ai/ask/suggestions', data),
    riskScan: (data: { objectType: string; objectId: number }) =>
      http.post<any>('/ai/risk/scan', data),
    riskWarnings: (data: { objectType: string; objectId: number; onlyActive?: boolean }) =>
      http.post<{ warnings: any[]; lastScanAt: string }>('/ai/risk/warnings', data),
    alertToday: () => http.post<{ list: any[]; total: number }>('/ai/alert/today', {}),
    modelList: () => http.post<{ list: any[]; total: number }>('/ai/model/list', {}),
  },

  // ==================== Admin ====================
  admin: {
    // 用户
    users: (data: PageReq) => http.post<PageRes<any>>('/admin/users/list', data),
    userDetail: (userId: number) =>
      http.post<any>('/admin/users/detail', {}, { params: { userId } }),
    userCreate: (data: any) => http.post<any>('/admin/users/create', data),
    userUpdate: (userId: number, data: any) =>
      http.post<any>('/admin/users/update', data, { params: { userId } }),
    userDelete: (userId: number) =>
      http.post<any>('/admin/users/delete', {}, { params: { userId } }),
    userResetPwd: (userId: number, newPassword: string) =>
      http.post<any>('/admin/users/reset-password', { userId, newPassword }),
    userToggleActive: (userId: number, isActive: boolean) =>
      http.post<any>('/admin/users/toggle-active', { userId, isActive }),
    // 角色
    roles: () => http.post<{ list: any[]; total: number }>('/admin/roles/list', {}),
    roleDetail: (roleId: number) =>
      http.post<any>('/admin/roles/detail', {}, { params: { roleId } }),
    roleCreate: (data: any) => http.post<any>('/admin/roles/create', data),
    roleUpdate: (roleId: number, data: any) =>
      http.post<any>('/admin/roles/update', data, { params: { roleId } }),
    roleDelete: (roleId: number) =>
      http.post<any>('/admin/roles/delete', {}, { params: { roleId } }),
    permissions: () => http.post<{ list: any[]; total: number }>('/admin/permissions/list', {}),
    // 部门
    depts: () => http.post<{ list: any[]; total: number }>('/admin/depts/list', {}),
    deptsTree: () => http.get<{ list: any[]; total: number }>('/admin/depts/tree'),
    deptCreate: (data: any) => http.post<any>('/admin/depts/create', data),
    deptUpdate: (deptId: number, data: any) =>
      http.post<any>('/admin/depts/update', data, { params: { deptId } }),
    deptDelete: (deptId: number) =>
      http.post<any>('/admin/depts/delete', {}, { params: { deptId } }),
    // 字典
    dicts: (dictType: string) =>
      http.post<{ list: any[]; total: number }>('/admin/dicts/list', { dictType }),
    dictCreate: (data: any) => http.post<any>('/admin/dicts/create', data),
    dictUpdate: (dictId: number, data: any) =>
      http.post<any>('/admin/dicts/update', data, { params: { dictId } }),
    dictDelete: (dictId: number) =>
      http.post<any>('/admin/dicts/delete', {}, { params: { dictId } }),
    // 审计日志
    auditLogs: (data: PageReq) => http.post<PageRes<any>>('/admin/audit-logs/list', data),
  },

  // ==================== Cron ====================
  cron: {
    overdueCheck: () => http.post<{ scanned: number; alerted: number }>('/cron/overdue-check', {}),
    upcomingDue: () => http.post<{ scanned: number; alerted: number }>('/cron/upcoming-due', {}),
    contractExpiring: () => http.post<{ scanned: number; alerted: number }>('/cron/contract-expiring', {}),
    all: () => http.post<any>('/cron/all', {}),
    jobs: () => http.get<{ running: boolean; jobs: any[] }>('/cron/jobs'),
  },
}

export default sdk
