// ============================================================
// Admin 模块 API（用户/角色/部门/字典/审计）
// 与后端 /api/v1/admin/* 严格对齐（后端 POST 风格 + /depts /roles /users /dicts /permissions /audit-logs）
// ============================================================
import { http } from '@/utils/request'

// ---------- 后端真实响应类型 ----------
export interface DeptItem {
  id: number
  name: string
  code: string
  parentId: number | null
  parentName: string | null
  managerId: number | null
  managerName: string | null
  memberCount: number
  sort: number
  isActive: boolean
  createdAt: string
}

export interface DeptTreeNode extends DeptItem {
  children: DeptTreeNode[]
}

export interface RoleItem {
  id: number
  code: string
  name: string
  description: string | null
  userCount: number
  isBuiltin: boolean
  createdAt: string
}

export interface PermissionItem {
  id: number
  code: string
  module: string
  action: string
  name: string
}

export interface AdminUserItem {
  id: number
  account: string
  name: string
  email: string | null
  phone: string | null
  isActive: boolean
  lastLoginAt: string | null
  departmentId: number | null
  departmentName: string | null
  roles: { id: number; name: string; code: string }[]
}

export interface DictItemRow {
  id: number
  dictType: string
  code: string
  name: string
  sort: number
  isActive: boolean
}

export interface AuditLogItem {
  id: number
  userId: number
  userName: string
  action: string
  module: string
  resource: string
  ip: string
  status: 'success' | 'failed'
  createdAt: string
}

// ---------- 接口 ----------
export const adminApi = {
  // 部门
  deptList: () => http.post<{ list: DeptItem[]; total: number }>('/admin/depts/list', {}),
  deptCreate: (data: { name: string; code: string; parentId?: number | null; managerId?: number | null; sort?: number }) =>
    http.post<DeptItem>('/admin/depts/create', data),
  deptUpdate: (deptId: number, data: Partial<DeptItem>) =>
    http.post<DeptItem>('/admin/depts/update', data, { params: { deptId } }),
  deptDelete: (deptId: number) =>
    http.post<{ deleted: boolean }>('/admin/depts/delete', {}, { params: { deptId } }),

  // 角色
  roleList: () => http.post<{ list: RoleItem[]; total: number }>('/admin/roles/list', {}),
  roleDetail: (roleId: number) =>
    http.post<RoleItem>('/admin/roles/detail', {}, { params: { roleId } }),
  roleCreate: (data: { code: string; name: string; description?: string }) =>
    http.post<RoleItem>('/admin/roles/create', data),
  roleUpdate: (roleId: number, data: Partial<RoleItem>) =>
    http.post<RoleItem>('/admin/roles/update', data, { params: { roleId } }),
  roleDelete: (roleId: number) =>
    http.post<{ deleted: boolean }>('/admin/roles/delete', {}, { params: { roleId } }),

  // 权限
  permList: () => http.post<{ list: PermissionItem[]; total: number }>('/admin/permissions/list', {}),

  // 用户
  userList: (params: { page?: number; pageSize?: number; keyword?: string; departmentId?: number; roleId?: number; isActive?: boolean } = {}) =>
    http.post<{ list: AdminUserItem[]; total: number }>('/admin/users/list', params),
  userDetail: (userId: number) =>
    http.post<AdminUserItem>('/admin/users/detail', {}, { params: { userId } }),
  userCreate: (data: { account: string; name: string; password: string; email?: string; phone?: string; departmentId?: number; roleIds?: number[] }) =>
    http.post<AdminUserItem>('/admin/users/create', data),
  userUpdate: (userId: number, data: Partial<AdminUserItem>) =>
    http.post<AdminUserItem>('/admin/users/update', data, { params: { userId } }),
  userDelete: (userId: number) =>
    http.post<{ deleted: boolean }>('/admin/users/delete', {}, { params: { userId } }),
  userResetPwd: (userId: number, newPassword: string) =>
    http.post<{ ok: boolean }>('/admin/users/reset-password', { userId, newPassword }),
  userToggleActive: (userId: number, isActive: boolean) =>
    http.post<{ ok: boolean }>('/admin/users/toggle-active', { userId, isActive }),

  // 字典
  dictList: (dictType: string) =>
    http.post<{ list: DictItemRow[]; total: number }>('/admin/dicts/list', {}, { params: { dictType } }),
  dictCreate: (data: { dictType: string; code: string; name: string; sort?: number }) =>
    http.post<DictItemRow>('/admin/dicts/create', data),
  dictUpdate: (dictId: number, data: Partial<DictItemRow>) =>
    http.post<DictItemRow>('/admin/dicts/update', data, { params: { dictId } }),
  dictDelete: (dictId: number) =>
    http.post<{ deleted: boolean }>('/admin/dicts/delete', {}, { params: { dictId } }),

  // 审计日志
  auditLogList: (params: { page?: number; pageSize?: number; keyword?: string } = {}) =>
    http.post<{ list: AuditLogItem[]; total: number }>('/admin/audit-logs/list', params),
}
