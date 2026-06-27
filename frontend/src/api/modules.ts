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
  activities: (page = 1, pageSize = 10) =>
    http.post<{ list: any[]; total: number; page: number; pageSize: number }>('/dashboard/activities', { page, pageSize }),
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
  batchDelete: (ids: number[]) => http.post<{deleted: number; skipped: any[]; deletedIds: number[]}>(`/contracts/batch/delete`, { contractIds: ids }),
  submit: (id: number) => http.post(`/contracts/submit`, undefined, { params: { contractId: id } }),
  approve: (id: number, data: { action: 'approve' | 'reject' | 'transfer'; comment?: string; transferTo?: number }) =>
    http.post(`/contracts/approve`, { contractId: id, ...data }),
  /** 催办（仅审批中状态） */
  urge: (id: number, data?: { message?: string; targetUserIds?: number[] }) =>
    http.post<{ contractId: number; notifiedUserIds: number[]; message: string }>(
      '/contracts/urge', { contractId: id, ...(data || {}) },
    ),
  /** 下载合同（PDF 摘要）— 返回 blob 与后端给的文件名 */
  download: async (id: number) => {
    const axios = (await import('axios')).default
    const userStore = (await import('@/stores/user')).useUserStore()
    const base = (import.meta.env?.VITE_API_BASE as string | undefined) || '/api/v1'
    const resp = await axios.get(`${base}/contracts/${id}/download`, {
      responseType: 'blob',
      headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
    })
    const cd = resp.headers['content-disposition'] || ''
    const m = cd.match(/filename\*=UTF-8''([^;]+)|filename="([^"]+)"/)
    const filename = m ? decodeURIComponent(m[1] || m[2]) : `合同_${id}.pdf`
    return { blob: resp.data as Blob, filename }
  },
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
  batchDelete: (expenseIds: number[]) => http.post<{deleted: number; skipped: any[]; deletedIds: number[]}>(`/expenses/batch/delete`, { expenseIds }),
  submit: (id: number) => http.post(`/expenses/submit`, undefined, { params: { expenseId: id } }),
  approve: (id: number, data: { action: 'approve' | 'reject' | 'transfer'; comment?: string; transferTo?: number }) =>
    http.post(`/expenses/approve`, { expenseId: id, ...data }),
  markPaid: (id: number) => http.post(`/expenses/mark-paid`, undefined, { params: { expenseId: id } }),
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
  fieldLibrary: () => http.post<{ groups: Array<{ name: string; fields: any[] }> }>('/invoice/templates/field-library', {}),
  create: (data: Partial<InvoiceTemplate>) => http.post<InvoiceTemplate>('/invoice/templates/save', data),
  update: (id: number, data: Partial<InvoiceTemplate>) => http.post<InvoiceTemplate>('/invoice/templates/save', { ...data, templateId: id }),
  delete: (id: number) => http.post(`/invoice/templates/delete`, { templateId: id }),
  duplicate: (id: number) => http.post<InvoiceTemplate>('/invoice/templates/duplicate', { templateId: id }),
  toggleStatus: (id: number) => http.post<{ status: string; message: string }>('/invoice/templates/toggle', { templateId: id }),
}

// ---------- 发票识别 (OCR) ----------
export interface OcrResult {
  id?: number
  invoiceId?: number  // 后端 OCR upload 返回字段（兼容新旧）
  code?: string | null
  ocrStatus: string
  confidence: number
  error?: string
  fields: {
    invoiceType?: string
    invoiceCode?: string
    invoiceNo?: string
    issueDate?: string
    sellerName?: string
    buyerName?: string
    buyerTaxNo?: string
    taxRate?: string
    totalAmount?: number
    taxAmount?: number
    // 后端启发式归类（销售方名/发票类型 → 费用类型）
    expenseType?: string
    items?: Array<{ name: string; amount: number; taxRate: number }>
  }
  fileUrl?: string
  verifyStatus?: string
}
export const invoiceOcrApi = {
  stats: () => http.post<any>('/invoice/ocr/stats', {}).catch(() => null),

  /** 上传并识别（multipart） */
  upload: (formData: FormData) => http.upload<OcrResult>('/invoice/ocr/upload', formData),
  /** 批量上传（R8：独立页 /invoice/ocr/batch） */
  batchUpload: (formData: FormData) => http.upload<{
    batchId: string
    total: number
    taskCode: string
  }>('/invoice/ocr/batch/upload', formData),
  /** 识别记录 */
  records: (params: PageReq) => http.post<PageRes<OcrResult>>('/invoice/ocr/list', params),
  /** 批量删除发票 */
  batchDelete: (invoiceIds: number[]) => http.post<{deleted: number}>('/invoice/ocr/batch/delete', { invoiceIds }),
  /** 单条编辑/核验 */
  update: (id: number, data: any) => http.post<any>('/invoice/ocr/update', data, { params: { invoiceId: id } }),
  /** 单条提交入账 */
  submit: (id: number, reason?: string) => http.post<any>('/invoice/ocr/submit', undefined, { params: { invoiceId: id, reason } }),
  /** 重新识别（recheck） */
  recheck: (id: number) => http.post<any>('/invoice/ocr/recheck', undefined, { params: { invoiceId: id } }),
  /** R-extra: 可关联的发票列表（未关联任何费用、已核验） */
  unlinked: (params: { keyword?: string; page?: number; pageSize?: number }) => http.post<{ list: any[]; total: number }>('/invoice/ocr/unlinked', params),
  /** 批量提交入账 */
  batchSubmit: (invoiceIds: number[], reason?: string) => http.post<{updated: number; invoiceIds: number[]}>('/invoice/ocr/batch/submit', { invoiceIds, reason }),
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
  /** 查验记录列表 */
  verifyList: (params: { page?: number; pageSize?: number; filters?: any }) =>
    http.post<PageRes<any>>('/invoice/verify/list', { page: params.page || 1, pageSize: params.pageSize || 20, filters: params.filters || {} }),
  /** 批量验真 */
  verifyBatch: (data: { invoices: Array<{ invoiceId?: number; invoiceCode: string; invoiceNo: string; issueDate: string; totalAmount: number; verifyCode?: string }> }) =>
    http.post<{ batchId: string; total: number; summary: { pass: number; risk: number }; items: any[] }>('/invoice/verify/batch', data),
  /** 下载查验凭证 */
  verifyCertificate: (verifyId: string) =>
    http.post<{ verifyId: string; certificateUrl: string }>('/invoice/verify/certificate', undefined, { params: { verifyId } }),
  /** 标记风险发票 */
  verifyMark: (verifyId: string, action: 'mark' | 'isolate' | 'report', comment?: string) =>
    http.post<{ verifyId: string; action: string; marked: boolean }>('/invoice/verify/mark', { verifyId, action, comment }),
  /** 国税接口健康检查 */
  verifyHealth: () => http.get<{
    mode: string; configured: boolean; useSandbox: boolean; apiUrl: string;
    status: 'mock' | 'reachable' | 'degraded' | 'down'; message: string;
  }>('/invoice/verify/health'),
  /** 查看当前配置（脱敏） */
  verifyConfig: () => http.get<{
    mode: string; apiUrl: string; useSandbox: boolean;
    appKeyMasked: string; appSecretMasked: string; accessTokenMasked: string;
    configured: boolean; configSource: string; guide: string;
  }>('/invoice/verify/config'),
}

// ============================================================
// 系统设置（admin only）
// ============================================================
export interface SettingItem {
  key: string
  group: string
  label: string
  type: 'string' | 'int' | 'float' | 'bool' | 'enum'
  sensitive?: boolean
  warning?: string
  help?: string
  placeholder?: string
  options?: string[]
  min?: number
  max?: number
  step?: number
  isSet: boolean
  displayValue: string
  rawType: string
  hotReload: boolean
  options_help?: Record<string, string>
}

export const settingsApi = {
  getAll: () => http.get<{
    groups: Record<string, SettingItem[]>
    envFilePath: string
    runtimeEnv: string
    version: string
  }>('/admin/settings/all'),
  update: (updates: Record<string, string>) =>
    http.put<{
      applied: Array<{ key: string; hotReload: boolean }>
      rejected: Array<{ key: string; reason: string }>
      envWritten: boolean
      envPath: string
    }>('/admin/settings/update', { updates }),
  testConnection: (target: 'ocr' | 'nuonuo' | 'redis' | 'database') =>
    http.post<{ target: string; status: string; error?: string }>('/admin/settings/test-connection', { target }),
  // 触点 #52：配置备份/恢复/系统更新
  exportSettings: () =>
    http.get<{
      formatVersion: number
      exportedAt: string
      exportedBy: number
      runtimeEnv: string
      appName: string
      safeItems: Array<{ key: string; group: string; label: string; type: string; value: string }>
      sensitiveKeys: Array<{ key: string; group: string; label: string; isSet: boolean }>
      notice: string
    }>('/admin/settings/export'),
  importSettings: (payload: any) =>
    http.post<{ applied: any[]; skipped: string[]; rejected: any[] }>(
      '/admin/settings/import', { payload },
    ),
  checkUpdate: () =>
    http.get<{
      currentVersion: string
      latestVersion: string | null
      hasUpdate: boolean
      releaseUrl: string | null
      releaseNotes?: string
      publishedAt?: string
      assetSizeMB?: number
      error?: string
    }>('/admin/settings/update/check'),
  restartBackend: () =>
    http.post<{
      message: string
      delay_seconds: number
      estimated_recovery_seconds: number
      note: string
    }>('/admin/settings/restart'),
  healthCheck: async () => {
    // 直接用 fetch 绕过 axios 的 /api/v1 baseURL 拦截器（健康检查在根路径）
    // 后端只返回 "ok\n" 文本，不要 r.json() 会报错
    const r = await fetch('/health', { cache: 'no-store' })
    if (!r.ok) throw new Error('health ' + r.status)
    return { status: 'ok' }
  },
}

// ---------- 报销中心 ----------
export interface ReimburseForm {
  formId: number
  formNo: string
  templateType: string
  title: string
  applicant?: { userId: number; name: string }
  department?: { id: number; name: string }
  totalAmount: number
  actualAmount: number
  currency?: string
  status: string
  statusLabel: string
  expenseDate?: string
  paymentDate?: string
  voucherNo?: string
  detailCount?: number
  aiDescription?: string
  aiRiskFlag?: string
  aiRiskReason?: string
  remark?: string
  createdAt?: string
  updatedAt?: string
  details?: Array<{
    id: number
    expenseId: number
    expenseCode?: string
    expenseType?: string
    expenseDate?: string
    clientName?: string
    projectName?: string
    title?: string
    amount: number
    reimbursedAmount: number
    seq: number
  }>
  templateSnapshot?: any
}
export interface ReimburseTemplate {
  code: string
  name: string
  type: string
  icon?: string
  color?: string
  description?: string
  schema?: any
}
export const reimburseApi = {
  list: (params: PageReq) => http.post<PageRes<ReimburseForm>>('/reimbursements/list', params),
  detail: (formId: number) => http.post<ReimburseForm>('/reimbursements/detail', undefined, { params: { formId } }),
  create: (data: { templateType: string; title?: string; expenseIds: number[]; remark?: string; expenseDate?: string; aiDescription?: string }) =>
    http.post<ReimburseForm>('/reimbursements/create', data),
  update: (formId: number, data: any) => http.post<ReimburseForm>('/reimbursements/update', { ...data, formId }),
  delete: (formId: number) => http.post('/reimbursements/delete', { formId }),
  /** R-extra: 批量删除报销单（仅超管/草稿） */
  batchDelete: (formIds: number[]) => http.post<{deleted: number; skipped: any[]}>('/reimbursements/batch/delete', { formIds }),
  /** R-extra: 导出报销单（CSV/Excel 当前用 CSV，含明细） */
  exportList: (params: { keyword?: string; filters?: any }) => http.post<{csv: string; filename: string; count: number}>('/reimbursements/export', params),
  fillback: (data: { formId: number; actualAmount: number; paymentDate?: string; voucherNo?: string; remark?: string; detailAmounts?: Record<string, number> }) =>
    http.post<ReimburseForm>('/reimbursements/fillback', data),
  markPrinted: (formId: number) => http.post<ReimburseForm>('/reimbursements/mark-printed', { formId }),
  templates: () => http.get<ReimburseTemplate[]>('/reimbursements/templates'),
  template: (code: string) => http.get<ReimburseTemplate>(`/reimbursements/templates/${code}`),
  aiDescription: (data: { expenseIds: number[]; formId?: number }) =>
    http.post<{ description: string }>('/reimbursements/ai-description', data),
  aiRisk: (data: { expenseIds: number[]; formId?: number }) =>
    http.post<{ level: string; reasons: string[] }>('/reimbursements/ai-risk', data),
  exportData: (formId: number) => http.get<ReimburseForm>(`/reimbursements/export-data`, { params: { formId } }),
  // ===== 模板自定义 =====
  createTemplate: (data: { code?: string; name: string; type?: string; icon?: string; color?: string; description?: string; schema: any }) =>
    http.post<ReimburseTemplate>('/reimbursements/templates/custom', data),
  updateTemplate: (templateId: number, data: Partial<{ name: string; type: string; icon: string; color: string; description: string; schema: any }>) =>
    http.post<ReimburseTemplate>('/reimbursements/templates/custom/update', { templateId, ...data }),
  deleteTemplate: (templateId: number) =>
    http.post('/reimbursements/templates/custom/delete', { templateId }),
  cloneTemplate: (code: string) =>
    http.post<ReimburseTemplate>('/reimbursements/clone', { code }),
  recognizeFromText: (text: string) =>
    http.post<{ detectedFields: any[]; suggestedSchema: any; confidence: number; textPreview: string }>('/reimbursements/templates/recognize-text', undefined, { params: { text } } as any).then((r: any) => r?.data || r),
  recognizeFromFile: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/reimbursements/templates/recognize-file', fd, { headers: { 'Content-Type': 'multipart/form-data' } } as any).then((r: any) => r?.data || r)
  },
}

// ---------- 文件库（专门管理非结构化数据：发票 PDF/图片/合同附件/报销凭证） ----------
export interface FileObject {
  fileId: string
  name: string
  ext: string
  size: number
  mimeType: string
  url: string
  storage: string
  uploaderId: number | null
  uploaderName: string
  bizType: string | null
  bizId: number | null
  createdAt: string
}
export const fileApi = {
  list: (params: { bizType?: string; bizId?: number; storage?: string; keyword?: string; page?: number; pageSize?: number }) =>
    http.post<{ list: FileObject[]; total: number; page: number; pageSize: number }>('/common/files/list', params),
  stats: (params?: { bizType?: string }) =>
    http.post<{ total: number; totalSize: number; byStorage: Record<string, { count: number; size: number }>; byBizType: Record<string, { count: number; size: number }> }>('/common/files/stats', params || {}),
}
