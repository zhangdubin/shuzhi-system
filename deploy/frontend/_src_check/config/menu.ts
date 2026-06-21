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
    ],
  },
  // ========== 财务 ==========
  {
    title: '财务',
    items: [
      {
        index: '/invoice',
        title: '发票识别',
        icon: 'Document',
        children: [
          { index: '/invoice/ocr', title: '识别主页' },
          { index: '/invoice/ocr/batch', title: '批量上传' },
          { index: '/invoice/ocr/records', title: '识别记录' },
          { index: '/invoice/verify', title: '查验真伪' },
        ],
      },
      { index: '/invoice/template', title: '发票模板', icon: 'Files' },
      { index: '/expense/list', title: '销售费用', icon: 'Money' },
    ],
  },
  // ========== 业务 ==========
  {
    title: '业务',
    items: [
      { index: '/client/list', title: '客户管理', icon: 'User' },
      { index: '/project/list', title: '项目管理', icon: 'Folder' },
      { index: '/contract/list', title: '合同管理', icon: 'Tickets' },
      { index: '/receivable/list', title: '回款管理', icon: 'Wallet' },
      {
        index: '/ai',
        title: 'AI 智能中心',
        icon: 'MagicStick',
        children: [
          { index: '/ai/extract', title: 'AI 抽取' },
          { index: '/ai/tasks', title: '任务中心' },
          { index: '/ai/alerts', title: '智能预警' },
        ],
      },
    ],
  },
  // ========== 系统（管理员）==========
  {
    title: '系统',
    items: [
      { index: '/admin/user', title: '用户管理', icon: 'UserFilled', permission: 'admin' },
      { index: '/admin/role', title: '角色权限', icon: 'Lock', permission: 'admin' },
      { index: '/admin/dept', title: '部门管理', icon: 'OfficeBuilding', permission: 'admin' },
      { index: '/admin/dict', title: '数据字典', icon: 'Collection', permission: 'admin' },
    ],
  },
]

/** 兼容旧代码（如果还有用 menuConfig 的地方） */
export const menuConfig: MenuItem[] = menuGroups.flatMap(g => g.items)
