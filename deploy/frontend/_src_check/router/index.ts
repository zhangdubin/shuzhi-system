// ============================================================
// 路由配置
// ============================================================
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
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
      { path: 'project/create', name: 'ProjectCreate', component: () => import('@/views/project/ProjectCreate.vue'), meta: { title: '项目立项' } },
      { path: 'project/:id/edit', name: 'ProjectEdit', component: () => import('@/views/project/ProjectCreate.vue'), meta: { title: '编辑项目' } },
      { path: 'project/:id', name: 'ProjectDetail', component: () => import('@/views/project/ProjectDetail.vue'), meta: { title: '项目详情' } },

      // 合同
      { path: 'contract/list', name: 'ContractList', component: () => import('@/views/contract/ContractList.vue'), meta: { title: '合同列表' } },
      { path: 'contract/create', name: 'ContractCreate', component: () => import('@/views/contract/ContractCreate.vue'), meta: { title: '新建合同' } },
      { path: 'contract/template', name: 'ContractTemplate', component: () => import('@/views/contract/ContractTemplate.vue'), meta: { title: '合同模板' } },
      { path: 'contract/:id/edit', name: 'ContractEdit', component: () => import('@/views/contract/ContractCreate.vue'), meta: { title: '编辑合同' } },
      { path: 'contract/:id', name: 'ContractDetail', component: () => import('@/views/contract/ContractDetail.vue'), meta: { title: '合同详情' } },

      // 销售费用
      { path: 'expense/list', name: 'ExpenseList', component: () => import('@/views/expense/ExpenseList.vue'), meta: { title: '费用列表' } },
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
      { path: 'client/:id', name: 'ClientDetail', component: () => import('@/views/client/ClientList.vue'), meta: { title: '客户详情' } },

      // 发票
      { path: 'invoice/ocr', name: 'InvoiceOcr', component: () => import('@/views/invoice/InvoiceOcr.vue'), meta: { title: '发票识别' } },
      // 注意：/invoice/ocr/:id 必须放在 /invoice/ocr 之后，否则动态路由会吞掉字面路径
      { path: 'invoice/ocr/:id', name: 'InvoiceOcrDetail', component: () => import('@/views/invoice/InvoiceDetail.vue'), meta: { title: '识别记录详情' } },
      { path: 'invoice/verify', name: 'InvoiceVerify', component: () => import('@/views/invoice/InvoiceVerify.vue'), meta: { title: '发票查验' } },
      { path: 'invoice/template', name: 'InvoiceTemplate', component: () => import('@/views/invoice/InvoiceTemplateList.vue'), meta: { title: '发票模板' } },
      { path: 'invoice/template/:id', name: 'InvoiceTemplateDetail', component: () => import('@/views/invoice/InvoiceTemplateDetail.vue'), meta: { title: '模板详情' } },
      { path: 'invoice/template/:id/edit', name: 'InvoiceTemplateEdit', component: () => import('@/views/invoice/InvoiceTemplateEdit.vue'), meta: { title: '编辑模板' } },

      // AI
      { path: 'ai/extract', name: 'AiExtract', component: () => import('@/views/ai/AiExtract.vue'), meta: { title: 'AI 抽取' } },
      { path: 'ai/tasks', name: 'AiTasks', component: () => import('@/views/ai/AiTasks.vue'), meta: { title: '任务中心' } },
      { path: 'ai/alerts', name: 'AiAlerts', component: () => import('@/views/ai/AiAlerts.vue'), meta: { title: '智能预警' } },
      // AI 分析面板（独立路由页，与抽屉共用 AiDrawer 组件）
      { path: 'ai/panel/project', name: 'AiPanelProject', component: () => import('@/views/ai/AiPanelProject.vue'), meta: { title: '项目 AI 分析' } },
      { path: 'ai/panel/contract', name: 'AiPanelContract', component: () => import('@/views/ai/AiPanelContract.vue'), meta: { title: '合同 AI 体检' } },

      // Admin（占位）
      { path: 'admin/user', name: 'AdminUser', component: () => import('@/views/admin/AdminUser.vue'), meta: { title: '用户管理' } },
      { path: 'admin/role', name: 'AdminRole', component: () => import('@/views/admin/AdminRole.vue'), meta: { title: '角色权限' } },
      { path: 'admin/dept', name: 'AdminDept', component: () => import('@/views/admin/AdminDept.vue'), meta: { title: '部门管理' } },
      { path: 'admin/dict', name: 'AdminDict', component: () => import('@/views/admin/AdminDict.vue'), meta: { title: '数据字典' } },
    ],
  },
  // 错误页
  { path: '/403', name: 'Error403', component: () => import('@/views/error/Error403.vue'), meta: { public: true, layout: 'blank' } },
  { path: '/404', name: 'Error404', component: () => import('@/views/error/Error404.vue'), meta: { public: true, layout: 'blank' } },
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
    next()
  }
})

router.afterEach((to) => {
  const baseTitle = '数智化管理系统'
  document.title = to.meta.title ? `${to.meta.title} · ${baseTitle}` : baseTitle
})

export default router
