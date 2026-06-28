// ============================================================
// 侧栏菜单（与 design/ 严格对齐：总览 / 财务 / 业务 三组）
// ============================================================
import type { Component } from 'vue'

export interface MenuItem {
  index: string
  title: string
  icon?: string // Element Plus icon name（一级必填，二级不需要）
  permission?: string
  children?: MenuItem[]
}

export interface MenuGroup {
  /** 分组标题（design 里的 nav-group-title） */
  title: string
  items: MenuItem[]
}

/**
 * design 设计稿是「总览 / 财务 / 业务」三组；
 * AI 智能中心 → 业务组（业务增值）；
 * 系统管理 → 业务组底部（管理员专属）。
 * 客户管理 → 业务组第一位（业务流源头：客户→项目→合同→费用→回款→发票）。
 */
export const menuGroups: MenuGroup[] = [
  // ========== 总览 ==========
  {
    title: '总览',
    items: [
      { index: '/dashboard', title: '工作台', icon: 'Odometer' },
      { index: '/notice', title: '通知中心', icon: 'Bell' },
    ],
  },
  // ========== 财务 ==========
  {
    title: '财务',
    items: [
      {
        // R8.6: 父菜单 index 指向子菜单（识别主页），避免父菜单自身 404
        // 之前写 /invoice 但路由表没注册这个路径
        index: '/invoice/ocr',
        title: '发票识别',
        icon: 'Document',
        permission: 'invoice:read',
        children: [
          { index: '/invoice/ocr', title: '识别主页', permission: 'invoice:read' },
          { index: '/invoice/ocr/batch', title: '批量上传', permission: 'invoice:upload' },
          { index: '/invoice/ocr/records', title: '识别记录', permission: 'invoice:read' },
          { index: '/invoice/verify', title: '查验真伪', permission: 'invoice:verify' },
        ],
      },
      { index: '/invoice/template', title: '发票模板', icon: 'Files', permission: 'template:read' },
      {
        index: '/expense/list',
        title: '销售费用',
        icon: 'Money',
        permission: 'expense:read',
        children: [
          { index: '/expense/list', title: '费用列表', permission: 'expense:read' },
          { index: '/reimbursement/list', title: '报销中心', permission: 'expense:write' },
          { index: '/reimbursement/templates', title: '模板管理', permission: 'expense:write' },
        ],
      },
    ],
  },
  // ========== 业务 ==========
  {
    title: '业务',
    items: [
      { index: '/client/list', title: '客户管理', icon: 'User', permission: 'contract:read' },
      { index: '/project/list', title: '项目管理', icon: 'Folder', permission: 'project:read' },
      { index: '/contract/list', title: '合同管理', icon: 'Tickets', permission: 'contract:read' },
      { index: '/receivable/list', title: '回款管理', icon: 'Wallet', permission: 'receivable:read' },
      {
        index: '/ai',
        title: 'AI 智能中心',
        icon: 'MagicStick',
        permission: 'ai:extract',
        children: [
          { index: '/ai', title: '总览' },
          { index: '/ai/extract', title: 'AI 抽取', permission: 'ai:extract' },
          { index: '/ai/ask', title: 'AI 智能问答', permission: 'ai:ask' },
          { index: '/ai/risk', title: 'AI 风险扫描', permission: 'ai:risk.scan' },
          { index: '/ai/tasks', title: '任务中心', permission: 'ai:extract' },
          { index: '/ai/alerts', title: '智能预警', permission: 'ai:ask' },
        ],
      },
    ],
  },
  // ========== 系统（管理员）==========
  // 触点 #50：7 个管理入口合并为「系统设置」父菜单 + 6 个子菜单
  // 「系统设置」本身留在父菜单，详情页聚合子模块入口
  {
    title: '系统',
    items: [
      {
        index: '/admin/settings',
        title: '系统设置',
        icon: 'Setting',
        permission: 'admin',
        children: [
          { index: '/admin/user', title: '用户管理', icon: 'UserFilled', permission: 'user:read' },
          { index: '/admin/role', title: '角色权限', icon: 'Lock', permission: 'user:read' },
          { index: '/admin/dept', title: '部门管理', icon: 'OfficeBuilding', permission: 'user:read' },
          { index: '/admin/dict', title: '数据字典', icon: 'Collection', permission: 'user:read' },
          { index: '/admin/approval-template', title: '审批流模板', icon: 'SetUp', permission: 'admin' },
          { index: '/admin/audit-log', title: '审计日志', icon: 'Document', permission: 'audit:read' },
          { index: '/admin/print-template', title: '打印模板', icon: 'Printer', permission: 'print:template:read' },
          { index: '/admin/print-log', title: '打印日志', icon: 'Tickets', permission: 'print:document:read' },
        ],
      },
    ],
  },
]

/** 兼容旧代码（如果还有用 menuConfig 的地方） */
export const menuConfig: MenuItem[] = menuGroups.flatMap(g => g.items)
