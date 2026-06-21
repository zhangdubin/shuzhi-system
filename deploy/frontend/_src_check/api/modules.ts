// ============================================================
// 业务模块 API（按域分）
//
// 2026-05-21 路径与后端实际注册对齐（来自后端 openapi.json）：
//   /api/v1/projects/         (复数)
//   /api/v1/contracts/        (复数)
//   /api/v1/expenses/         (复数)
//   /api/v1/receivables/      (复数)
//   /api/v1/invoice/ocr/      (单数子段)
//   /api/v1/invoice/templates/(复数)
//
// 注意：/api/v1/clients/ 当前后端未注册，前端调用需 mock
// ============================================================
import { http } from '@/utils/request'
import type { PageReq, PageRes } from '@/types/api'

// ---------- Dashboard ----------
export const dashboardApi = {
  stats: () =>
    http.post<{
      greeting?: { name: string; time: string }
      quarterRemainingDays?: number
      moduleStats?: Array<{ module: string; name: string; value: number; unit: string; icon: string; color: string }>
      kpi?: Array<{ key: string; label: string; value: number; unit: string; delta?: number; deltaType?: 'up' | 'down' | 'flat'; extra?: string }>
      trendChart?: { period: string; labels: string[]; series: Array<{ name: string; color: string; data: number[] }> }
      todos?: Array<{ type: 'warning' | 'normal' | 'danger'; title: string; meta: string; link?: string }>
      teamMembers?: Array<{ userId: string; name: string; role: string; avatar?: string; online: boolean }>
    }>('/dashboard/summary'),
}

// ---------- 项目 ----------
export interface Project {
  id: number
  code: string
  name: string
  type?: string
  clientId?: number
  clientName: string
  managerId?: number
  managerName: string
  status: string
  contractAmount: number
  budget?: number
  spent?: number
  startDate: string
  endDate: string
  progress: number
  description?: string
  createdAt?: string
  updatedAt?: string
  /** AI 风险评级（来自 ai_risk 表） */
  aiRiskLevel?: 'high' | 'medium' | 'low' | 'unknown'
  /** AI 智能摘要 */
  aiSummary?: string
  /** AI 智能标签 */
  aiTags?: string[]
  /** AI 健康分 0-100 */
  aiHealthScore?: number
}
export const projectApi = {
  list: (params: PageReq) => http.post<PageRes<Project>>('/projects/list', params),
  detail: (id: number) => http.post<Project>('/projects/detail', undefined, { params: { projectId: id } }),
  create: (data: Partial<Project>) => http.post<Project>('/projects/create', data),
  update: (id: number, data: Partial<Project>) => http.post<Project>('/projects/update', data, { params: { projectId: id } }),
  delete: (id: number) => http.post(`/projects/delete`, undefined, { params: { projectId: id } }),
  stats: () => http.post<any>('/projects/stats', {}),
}

// ---------- 合同 ----------
export interface Contract {
  contractId: number
  code: string
  name: string
  type?: string
  status: string
  clientId?: number
  clientName: string
  projectId?: number
  projectName?: string
  managerId?: number
  managerName: string
  amount: number
  currency?: string
  signDate?: string
  effectiveDate?: string
  expireDate?: string
  createdAt?: string
  /** AI 风险评级 */
  aiRiskLevel?: 'high' | 'medium' | 'low' | 'unknown'
  /** AI 体检分 0-100 */
  aiHealthScore?: number
  /** AI 风险标签 */
  aiTags?: string[]
}
export const contractApi = {
  list: (params: PageReq) => http.post<PageRes<Contract>>('/contracts/list', params),
  detail: (id: number) => http.post<Contract>('/contracts/detail', undefined, { params: { contractId: id } }),
  create: (data: Partial<Contract>) => http.post<Contract>('/contracts/create', data),
  update: (id: number, data: Partial<Contract>) => http.post<Contract>('/contracts/update', data, { params: { contractId: id } }),
  delete: (id: number) => http.post(`/contracts/delete`, undefined, { params: { contractId: id } }),
  submit: (id: number) => http.post(`/contracts/submit`, undefined, { params: { contractId: id } }),
  approve: (id: number, data: { action: 'approve' | 'reject' | 'transfer'; comment?: string; transferTo?: number }) =>
    http.post(`/contracts/approve`, { contractId: id, ...data }),
  stats: () => http.post<any>('/contracts/stats', {}),
}

// ---------- 销售费用 ----------
export interface Expense {
  expenseId: number
  code: string
  category: string
  title?: string
  amount: number
  currency?: string
  expenseDate?: string
  applicantId?: number
  applicantName: string
  departmentId?: number
  departmentName?: string
  status: string
  submitAt?: string
  createdAt?: string
  /** AI 异常标签 */
  aiTags?: string[]
}
export const expenseApi = {
  list: (params: PageReq) => http.post<PageRes<Expense>>('/expenses/list', params),
  detail: (id: number) => http.post<Expense>('/expenses/detail', undefined, { params: { expenseId: id } }),
  create: (data: Partial<Expense>) => http.post<Expense>('/expenses/create', data),
  update: (id: number, data: Partial<Expense>) => http.post<Expense>('/expenses/update', data, { params: { expenseId: id } }),
  delete: (id: number) => http.post(`/expenses/delete`, undefined, { params: { expenseId: id } }),
  submit: (id: number) => http.post(`/expenses/submit`, undefined, { params: { expenseId: id } }),
  approve: (id: number, data: { action: 'approve' | 'reject' | 'transfer'; comment?: string; transferTo?: number }) =>
    http.post(`/expenses/approve`, { expenseId: id, ...data }),
  stats: () => http.post<any>('/expenses/stats', {}),
}

// ---------- 回款 ----------
export interface Receivable {
  receivableId: number
  code: string
  contractId: number
  contractCode: string
  clientId?: number
  clientName: string
  type?: string
  planAmount: number
  receivedAmount: number
  pendingAmount: number
  planDate: string
  actualDate?: string
  overdueDays: number
  managerId?: number
  managerName?: string
  status: string
  createdAt?: string
  /** AI 智能匹配状态 */
  aiMatchStatus?: 'matched' | 'pending' | 'mismatch'
  /** AI 逾期风险 */
  aiOverdueRisk?: 'high' | 'medium' | 'low' | 'none'
}
export const receivableApi = {
  list: (params: PageReq) => http.post<PageRes<Receivable>>('/receivables/list', params),
  detail: (id: number) => http.post<Receivable>('/receivables/detail', undefined, { params: { receivableId: id } }),
  create: (data: Partial<Receivable>) => http.post<Receivable>('/receivables/create', data),
  update: (id: number, data: Partial<Receivable>) => http.post<Receivable>('/receivables/update', data, { params: { receivableId: id } }),
  delete: (id: number) => http.post(`/receivables/delete`, undefined, { params: { receivableId: id } }),
  remind: (id: number) => http.post(`/receivables/remind`, undefined, { params: { receivableId: id } }),
  receive: (id: number, data: { receivedAmount: number; receivedDate?: string; remark?: string }) =>
    http.post(`/receivables/receive`, { receivableId: id, ...data }),
  stats: () => http.post<any>('/receivables/stats', {}),
}

// ---------- 发票模板 ----------
/** 模板字段类型 */
export type InvoiceFieldType = 'text' | 'number' | 'date' | 'select' | 'textarea'
/** 模板类别 */
export type InvoiceTemplateCategory = '差旅' | '办公' | '招待' | '其他'

/** 模板单个字段（详情 / 编辑共用） */
export interface InvoiceTemplateField {
  /** 字段唯一 id（编辑用） */
  key: string
  /** 字段显示名（中文） */
  label: string
  /** 字段类型 */
  type: InvoiceFieldType
  /** 是否必填 */
  required: boolean
  /** 默认值 */
  defaultValue?: string
  /** select 类型时的可选项 */
  options?: string[]
  /** 排序顺序（1 开始） */
  order: number
  /** AI 自动识别此字段（Phase 1） */
  aiExtractEnabled?: boolean
}

export interface InvoiceTemplate {
  id: number
  code: string
  name: string
  category: InvoiceTemplateCategory | string
  description?: string
  fields: InvoiceTemplateField[]
  /** 详情扩展 */
  createdBy?: string
  createdAt?: string
  updatedAt: string
  updatedBy: string
  status?: '启用中' | '待启用' | '已停用' | string
}
export const invoiceTemplateApi = {
  list: (params: PageReq) => http.post<PageRes<InvoiceTemplate>>('/invoice/templates/list', params),
  detail: (id: number) => http.post<InvoiceTemplate>('/invoice/templates/detail', undefined, { params: { templateId: id } }),
  create: (data: Partial<InvoiceTemplate>) => http.post<InvoiceTemplate>('/invoice/templates/save', data),
  update: (id: number, data: Partial<InvoiceTemplate>) => http.post<InvoiceTemplate>('/invoice/templates/save', { ...data, id }),
  delete: (id: number) => http.post(`/invoice/templates/delete`, undefined, { params: { id } }),
}

// ---------- 发票识别 (OCR) ----------
export interface OcrResult {
  id?: number
  code: string
  ocrStatus: string
  confidence: number
  fields: {
    invoiceType?: string
    invoiceCode?: string
    invoiceNo?: string
    issueDate?: string
    sellerName?: string
    buyerName?: string
    totalAmount?: number
    taxAmount?: number
    items?: Array<{ name: string; amount: number; taxRate: number }>
  }
  fileUrl?: string
  verifyStatus?: string
}
export const invoiceOcrApi = {
  stats: () => http.post<any>('/invoice/ocr/stats', {}).catch(() => null),

  /** 上传并识别（multipart） */
  upload: (formData: FormData) => http.upload<OcrResult>('/invoice/ocr/upload', formData),
  /** 识别记录 */
  records: (params: PageReq) => http.post<PageRes<OcrResult>>('/invoice/ocr/list', params),
  /** 单条识别详情 */
  detail: (id: number) => http.post<OcrResult>('/invoice/ocr/detail', undefined, { params: { invoiceId: id } }),
  /** 验真 */
  verify: (data: {
    invoiceCode: string
    invoiceNo: string
    issueDate: string
    totalAmount: number
  }) =>
    http.post<{
      verifyId: string
      result: 'pass' | 'risk' | 'repeat' | 'not_found'
      source: string
      verifiedAt: string
      elapsed: number
      riskReason?: string
    }>('/invoice/verify/single', data),
}
