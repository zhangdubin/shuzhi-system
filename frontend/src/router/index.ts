// ============================================================
// 路由配置
// ============================================================
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { title: '登录', public: true, layout: 'blank' },
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    redirect: '/dashboard',
    children: [
      // Dashboard
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/Dashboard.vue'), meta: { title: '工作台' } },

      // 项目
      { path: 'project/list', name: 'ProjectList', component: () => import('@/views/project/ProjectList.vue'), meta: { title: '项目列表' } },
      { path: 'project/kanban', name: 'ProjectKanban', component: () => import('@/views/project/ProjectKanban.vue'), meta: { title: '项目看板' } },
      { path: 'project/create', name: 'ProjectCreate', component: () => import('@/views/project/ProjectCreate.vue'), meta: { title: '项目立项' } },
      { path: 'project/:id/edit', name: 'ProjectEdit', component: () => import('@/views/project/ProjectCreate.vue'), meta: { title: '编辑项目' } },
      { path: 'project/:id', name: 'ProjectDetail', component: () => import('@/views/project/ProjectDetail.vue'), meta: { title: '项目详情' } },

      // 合同
      { path: 'contract/list', name: 'ContractList', component: () => import('@/views/contract/ContractList.vue'), meta: { title: '合同列表' } },
      { path: 'contract/create', name: 'ContractCreate', component: () => import('@/views/contract/ContractCreate.vue'), meta: { title: '新建合同' } },
      { path: 'contract/template', name: 'ContractTemplate', component: () => import('@/views/contract/ContractTemplate.vue'), meta: { title: '合同模板' } },
      { path: 'contract/:id/edit', name: 'ContractEdit', component: () => import('@/views/contract/ContractCreate.vue'), meta: { title: '编辑合同' } },
      { path: 'contract/:id', name: 'ContractDetail', component: () => import('@/views/contract/ContractDetail.vue'), meta: { title: '合同详情' } },

      // 销售费用（eager load 消除 SPA 导航空白）
      { path: 'expense/list', name: 'ExpenseList', component: () => import('@/views/expense/ExpenseList.vue'), meta: { title: '费用列表' } },
      // 报销中心（独立子服务 /api/v1/reimbursements）
      { path: 'reimbursement/list', name: 'ReimburseList', component: () => import('@/views/reimbursement/ReimburseList.vue'), meta: { title: '报销中心' } },
      { path: 'reimbursement/create', name: 'ReimburseCreate', component: () => import('@/views/reimbursement/ReimburseCreate.vue'), meta: { title: '新建报销单' } },
      { path: 'reimbursement/:id', name: 'ReimburseDetail', component: () => import('@/views/reimbursement/ReimburseDetail.vue'), meta: { title: '报销单详情' } },
      { path: 'reimbursement/templates', name: 'ReimburseTemplates', component: () => import('@/views/reimbursement/TemplateManager.vue'), meta: { title: '模板管理' } },
      { path: 'expense/create', name: 'ExpenseCreate', component: () => import('@/views/expense/ExpenseCreate.vue'), meta: { title: '新建费用' } },
      { path: 'expense/:id', name: 'ExpenseDetail', component: () => import('@/views/expense/ExpenseDetail.vue'), meta: { title: '费用详情' } },

      // 回款
      { path: 'receivable/list', name: 'ReceivableList', component: () => import('@/views/receivable/ReceivableList.vue'), meta: { title: '回款列表' } },
      { path: 'receivable/create', name: 'ReceivableCreate', component: () => import('@/views/receivable/ReceivableCreate.vue'), meta: { title: '新建回款' } },
      { path: 'receivable/:id', name: 'ReceivableDetail', component: () => import('@/views/receivable/ReceivableDetail.vue'), meta: { title: '回款详情' } },

      // 客户
      { path: 'client/list', name: 'ClientList', component: () => import('@/views/client/ClientList.vue'), meta: { title: '客户列表' } },
      { path: 'client/create', name: 'ClientCreate', component: () => import('@/views/client/ClientCreate.vue'), meta: { title: '新建客户' } },
      { path: 'client/:id/edit', name: 'ClientEdit', component: () => import('@/views/client/ClientCreate.vue'), meta: { title: '编辑客户' } },
      { path: 'client/:id', name: 'ClientDetail', component: () => import('@/views/client/ClientDetail.vue'), meta: { title: '客户详情' } },

      // 发票
      { path: 'invoice/create', name: 'InvoiceCreate', component: () => import('@/views/invoice/InvoiceCreate.vue'), meta: { title: '手动新增发票' } },
      { path: 'invoice/ocr', name: 'InvoiceOcr', component: () => import('@/views/invoice/InvoiceOcr.vue'), meta: { title: '发票识别' } },
      // R8.7: batch/records 改 redirect 到 InvoiceOcr?tab=xx
      // 注意：/invoice/verify 仍是独立路由（不放在 /invoice/ocr/ 下，避免与 :id 冲突）
      // 菜单里"查验真伪"是父菜单的子项，路径 /invoice/verify，InvoiceOcr 里也有 verify tab
      { path: 'invoice/ocr/batch', redirect: '/invoice/ocr?tab=batch' },
      { path: 'invoice/ocr/records', redirect: '/invoice/ocr?tab=records' },
      // 注意：/invoice/ocr/:id 必须在所有 /invoice/ocr/xxx 字面路径之后，否则动态路由会吞掉
      { path: 'invoice/ocr/:id', name: 'InvoiceOcrDetail', component: () => import('@/views/invoice/InvoiceDetail.vue'), meta: { title: '识别记录详情' } },
      { path: 'invoice/print-studio', name: 'InvoicePrintStudio', component: () => import('@/views/invoice/print-studio/InvoicePrintStudio.vue'), meta: { title: '发票打印工作台', permission: 'print:document:read' } },
      { path: 'invoice/verify', name: 'InvoiceVerify', component: () => import('@/views/invoice/InvoiceVerify.vue'), meta: { title: '发票查验' } },
      { path: 'invoice/template', name: 'InvoiceTemplate', component: () => import('@/views/invoice/InvoiceTemplateList.vue'), meta: { title: '发票模板' } },
      { path: 'invoice/template/:id', name: 'InvoiceTemplateDetail', component: () => import('@/views/invoice/InvoiceTemplateDetail.vue'), meta: { title: '模板详情' } },
      { path: 'invoice/template/:id/edit', name: 'InvoiceTemplateEdit', component: () => import('@/views/invoice/InvoiceTemplateEdit.vue'), meta: { title: '编辑模板' } },

      // AI
      { path: 'ai', name: 'AiCenter', component: () => import('@/views/ai/AiCenter.vue'), meta: { title: 'AI 智能中心' } },
      { path: 'ai/extract', name: 'AiExtract', component: () => import('@/views/ai/AiExtract.vue'), meta: { title: 'AI 抽取' } },
      { path: 'ai/ask', name: 'AiAsk', component: () => import('@/views/ai/AiAsk.vue'), meta: { title: 'AI 智能问答' } },
      { path: 'ai/risk', name: 'AiRisk', component: () => import('@/views/ai/AiRisk.vue'), meta: { title: 'AI 风险扫描' } },
      { path: 'ai/tasks', name: 'AiTasks', component: () => import('@/views/ai/AiTasks.vue'), meta: { title: '任务中心' } },
      { path: 'ai/alerts', name: 'AiAlerts', component: () => import('@/views/ai/AiAlerts.vue'), meta: { title: '智能预警' } },
      { path: 'ai/settings', name: 'AiSettings', component: () => import('@/views/ai/ModelSettings.vue'), meta: { title: 'AI 模型设置', requiresAdmin: true } },
      // 通知中心
      { path: 'notice', name: 'NoticeCenter', component: () => import('@/views/notice/NoticeCenter.vue'), meta: { title: '通知中心' } },
      // AI 分析面板（独立路由页，与抽屉共用 AiDrawer 组件）
      { path: 'ai/panel/project', name: 'AiPanelProject', component: () => import('@/views/ai/AiPanelProject.vue'), meta: { title: '项目 AI 分析' } },
      { path: 'ai/panel/contract', name: 'AiPanelContract', component: () => import('@/views/ai/AiPanelContract.vue'), meta: { title: '合同 AI 体检' } },
      { path: 'ai/panel/contract/drawer', name: 'AiPanelContractDrawer', component: () => import('@/views/ai/AiPanelContractDrawer.vue'), meta: { title: 'AI 体检抽屉' } },

      // Admin（占位）
      { path: 'admin/user', name: 'AdminUser', component: () => import('@/views/admin/AdminUser.vue'), meta: { title: '用户管理', permission: 'user:read' } },
      { path: 'admin/role', name: 'AdminRole', component: () => import('@/views/admin/AdminRole.vue'), meta: { title: '角色权限', permission: 'role:read' } },
      { path: 'admin/dept', name: 'AdminDept', component: () => import('@/views/admin/AdminDept.vue'), meta: { title: '部门管理', permission: 'dept:read' } },
            { path: 'admin/approval-template', name: 'AdminApprovalTemplate', component: () => import('@/views/admin/AdminApprovalTemplate.vue'), meta: { title: '审批流模板', requireAdmin: true } },
      { path: 'admin/dict', name: 'AdminDict', component: () => import('@/views/admin/AdminDict.vue'), meta: { title: '数据字典', permission: 'dict:read' } },
      { path: 'admin/settings', name: 'SystemSettings', component: () => import('@/views/admin/SystemSettings.vue'), meta: { title: '系统设置', requireAdmin: true } },
      { path: 'admin/audit-log', name: 'AdminAuditLog', component: () => import('@/views/admin/AdminAuditLog.vue'), meta: { title: '审计日志', permission: 'audit:read' } },
      // UDPE 统一单据打印引擎（M2 阶段 7：补前端模块入口）
      { path: 'admin/print-template', name: 'AdminPrintTemplate', component: () => import('@/views/admin/AdminPrintTemplate.vue'), meta: { title: '打印模板', permission: 'print:template:read' } },
      { path: 'admin/print-template/editor/:id?', name: 'AdminPrintTemplateEditor', component: () => import('@/views/admin/AdminPrintTemplateEditor.vue'), meta: { title: '模板编辑器', permission: 'print:template:write' } },
      { path: 'admin/print-log', name: 'AdminPrintLog', component: () => import('@/views/admin/AdminPrintLog.vue'), meta: { title: '打印日志', permission: 'print:document:read' } },
    ],
  },
  // 错误页
  { path: '/403', name: 'Error403', component: () => import('@/views/error/Error403.vue'), meta: { public: true, layout: 'blank' } },
  { path: '/404', name: 'Error404', component: () => import('@/views/error/Error404.vue'), meta: { public: true, layout: 'blank' } },
  { path: '/500', name: 'Error500', component: () => import('@/views/error/Error500.vue'), meta: { public: true, layout: 'blank' } },
  { path: '/network', name: 'ErrorNetwork', component: () => import('@/views/error/ErrorNetwork.vue'), meta: { public: true, layout: 'blank' } },
  { path: '/:pathMatch(.*)*', redirect: '/404' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()
  if (to.meta.public) {
    next()
  } else if (!userStore.isLoggedIn) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else {
    // 权限检查
    // requireAdmin 判定：isAdmin=true OR permissions 含 * OR role 名称包含「超级」
    // R18 修复：localStorage 缓存可能没 isAdmin 字段（老数据）→ 重新拉一次
    if (to.meta.requireAdmin && userStore.userInfo && userStore.userInfo.isAdmin === undefined) {
      userStore.fetchMe().catch(() => {})
    }
    const isSuperAdmin = !!userStore.userInfo?.isAdmin
      || (userStore.permissions || []).includes('*')
      || /超级|超管/i.test(String(userStore.userInfo?.role || ''))
    if (to.meta.requireAdmin && !isSuperAdmin) {
      ElMessage.error('无权访问：仅超级管理员可访问该页面')
      next({ path: '/dashboard' })
    } else {
      const required = to.meta.permission as string | undefined
      if (required && !userStore.hasPerm(required)) {
        ElMessage.error(`无权访问：${required}`)
        next({ path: '/dashboard' })
      } else {
        next()
      }
    }
  }
})

router.afterEach((to) => {
  const baseTitle = '数智化管理系统'
  document.title = to.meta.title ? `${to.meta.title} · ${baseTitle}` : baseTitle
})

export default router
