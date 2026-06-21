// ============================================================
// 客户管理 API（与后端 /api/v1/common/clients 严格对齐）
// ============================================================
import { http } from '@/utils/request'

/** 客户等级 */
export type ClientLevel = 'A' | 'B' | 'C' | 'D'

/** 客户状态 */
export type ClientStatus = 'active' | 'paused' | 'lost'

/** 客户来源 */
export type ClientSource =
  | '官网咨询' | '电话来访' | '客户介绍' | '展会收集' | '市场推广' | '其他'

/** 联系人角色 */
export type ContactRole = '主要联系人' | '商务联系人' | '技术联系人' | '财务联系人'

/** 与后端 Client model 1:1 对齐 */
export interface Client {
  id: number
  code: string
  name: string
  shortName?: string | null
  taxNo?: string | null
  legalPerson?: string | null
  contactName?: string | null
  contactPhone?: string | null
  contactEmail?: string | null
  address?: string | null
  bankName?: string | null
  bankAccount?: string | null
  industry?: string | null
  level: string
  isActive?: boolean
  remark?: string | null
  createdAt?: string
}

export interface ClientListStats {
  total: number
  active: number
  newThisMonth: number
  pending: number
}

export const clientApi = {
  list: (params: { page?: number; pageSize?: number; keyword?: string } = {}) =>
    http.post<{ list: Client[]; total: number }>('/common/clients', params),
  detail: (id: number) =>
    http.post<Client>('/common/clients/detail', {}, { params: { clientId: id } }),
  create: (data: Partial<Client>) =>
    http.post<Client>('/common/clients/create', data),
  update: (id: number, data: Partial<Client>) =>
    http.post<Client>('/common/clients/update', data, { params: { clientId: id } }),
  delete: (id: number) =>
    http.post<{ deleted: boolean }>('/common/clients/delete', {}, { params: { clientId: id } }),
  /** 统计卡（前端从 list 自己算，避免后端再加） */
  stats: async (): Promise<ClientListStats> => {
    const res = await http.post<{ list: Client[]; total: number }>('/common/clients', { page: 1, pageSize: 200 })
    const list = res.list || []
    const now = new Date()
    const thisMonth = list.filter(c => c.createdAt && new Date(c.createdAt).getMonth() === now.getMonth()).length
    return {
      total: res.total || list.length,
      active: list.filter(c => c.isActive !== false).length,
      newThisMonth: thisMonth,
      pending: 0,
    }
  },
}
