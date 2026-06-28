/**
 * 预置字段树数据 (M3 阶段 5 数据绑定 UI)
 * 
 * 按业务类型 (docType) 分类，每个业务类型有对应的字段树结构。
 * 字段树用于属性面板中的数据绑定 UI，让用户点选字段即可绑定到组件。
 */

export interface FieldNode {
  key: string          // 字段名 (如 "title")
  path: string         // 完整路径 (如 "form.title")
  label: string        // 显示标签 (如 "标题")
  type: string         // 数据类型 (string / number / date / boolean)
  children?: FieldNode[]  // 子字段
}

/** 合同业务字段树 */
const contractFields: FieldNode[] = [
  {
    key: 'form',
    path: 'form',
    label: '表单数据',
    type: 'object',
    children: [
      { key: 'title', path: 'form.title', label: '合同标题', type: 'string' },
      { key: 'contractNo', path: 'form.contractNo', label: '合同编号', type: 'string' },
      { key: 'customerName', path: 'form.customerName', label: '客户名称', type: 'string' },
      { key: 'amount', path: 'form.amount', label: '合同金额', type: 'number' },
      { key: 'startDate', path: 'form.startDate', label: '开始日期', type: 'date' },
      { key: 'endDate', path: 'form.endDate', label: '结束日期', type: 'date' },
      { key: 'status', path: 'form.status', label: '合同状态', type: 'string' },
      { key: 'remark', path: 'form.remark', label: '备注', type: 'string' },
      { key: 'applicantName', path: 'form.applicantName', label: '申请人', type: 'string' },
      { key: 'department', path: 'form.department', label: '部门', type: 'string' },
    ],
  },
  {
    key: 'print',
    path: 'print',
    label: '打印信息',
    type: 'object',
    children: [
      { key: 'time', path: 'printTime', label: '打印时间', type: 'datetime' },
      { key: 'user', path: 'printUser', label: '打印人', type: 'string' },
    ],
  },
]

/** 发票业务字段树 */
const invoiceFields: FieldNode[] = [
  {
    key: 'form',
    path: 'form',
    label: '表单数据',
    type: 'object',
    children: [
      { key: 'invoiceNo', path: 'form.invoiceNo', label: '发票号码', type: 'string' },
      { key: 'amount', path: 'form.amount', label: '金额', type: 'number' },
      { key: 'taxAmount', path: 'form.taxAmount', label: '税额', type: 'number' },
      { key: 'totalAmount', path: 'form.totalAmount', label: '价税合计', type: 'number' },
      { key: 'buyerName', path: 'form.buyerName', label: '购买方名称', type: 'string' },
      { key: 'sellerName', path: 'form.sellerName', label: '销售方名称', type: 'string' },
      { key: 'invoiceDate', path: 'form.invoiceDate', label: '开票日期', type: 'date' },
      { key: 'status', path: 'form.status', label: '发票状态', type: 'string' },
      { key: 'remark', path: 'form.remark', label: '备注', type: 'string' },
    ],
  },
  {
    key: 'print',
    path: 'print',
    label: '打印信息',
    type: 'object',
    children: [
      { key: 'time', path: 'printTime', label: '打印时间', type: 'datetime' },
      { key: 'user', path: 'printUser', label: '打印人', type: 'string' },
    ],
  },
]

/** 报销单业务字段树 */
const reimbursementFields: FieldNode[] = [
  {
    key: 'form',
    path: 'form',
    label: '表单数据',
    type: 'object',
    children: [
      { key: 'title', path: 'form.title', label: '报销标题', type: 'string' },
      { key: 'totalAmount', path: 'form.totalAmount', label: '报销金额', type: 'number' },
      { key: 'applicantName', path: 'form.applicantName', label: '报销人', type: 'string' },
      { key: 'remark', path: 'form.remark', label: '备注', type: 'string' },
      { key: 'detailCount', path: 'form.detailCount', label: '明细项数', type: 'number' },
      { key: 'department', path: 'form.department', label: '部门', type: 'string' },
      { key: 'applyDate', path: 'form.applyDate', label: '申请日期', type: 'date' },
      { key: 'status', path: 'form.status', label: '报销状态', type: 'string' },
    ],
  },
  {
    key: 'print',
    path: 'print',
    label: '打印信息',
    type: 'object',
    children: [
      { key: 'time', path: 'printTime', label: '打印时间', type: 'datetime' },
      { key: 'user', path: 'printUser', label: '打印人', type: 'string' },
    ],
  },
]

/** 费用业务字段树 */
const expenseFields: FieldNode[] = [
  {
    key: 'form',
    path: 'form',
    label: '表单数据',
    type: 'object',
    children: [
      { key: 'expenseNo', path: 'form.expenseNo', label: '费用编号', type: 'string' },
      { key: 'amount', path: 'form.amount', label: '费用金额', type: 'number' },
      { key: 'category', path: 'form.category', label: '费用类别', type: 'string' },
      { key: 'applicantName', path: 'form.applicantName', label: '申请人', type: 'string' },
      { key: 'applyDate', path: 'form.applyDate', label: '申请日期', type: 'date' },
      { key: 'status', path: 'form.status', label: '费用状态', type: 'string' },
      { key: 'remark', path: 'form.remark', label: '备注', type: 'string' },
    ],
  },
  {
    key: 'print',
    path: 'print',
    label: '打印信息',
    type: 'object',
    children: [
      { key: 'time', path: 'printTime', label: '打印时间', type: 'datetime' },
      { key: 'user', path: 'printUser', label: '打印人', type: 'string' },
    ],
  },
]

/** 通用字段树 (用于未定义 docType 的情况) */
const generalFields: FieldNode[] = [
  {
    key: 'form',
    path: 'form',
    label: '表单数据',
    type: 'object',
    children: [
      { key: 'title', path: 'form.title', label: '标题', type: 'string' },
      { key: 'content', path: 'form.content', label: '内容', type: 'string' },
      { key: 'amount', path: 'form.amount', label: '金额', type: 'number' },
      { key: 'date', path: 'form.date', label: '日期', type: 'date' },
      { key: 'remark', path: 'form.remark', label: '备注', type: 'string' },
    ],
  },
  {
    key: 'print',
    path: 'print',
    label: '打印信息',
    type: 'object',
    children: [
      { key: 'time', path: 'printTime', label: '打印时间', type: 'datetime' },
      { key: 'user', path: 'printUser', label: '打印人', type: 'string' },
    ],
  },
]

/** 字段树映射表 */
export const fieldTreeMap: Record<string, FieldNode[]> = {
  contract: contractFields,
  invoice: invoiceFields,
  reimbursement: reimbursementFields,
  expense: expenseFields,
  general: generalFields,
}

/** 获取指定业务类型的字段树 */
export function getFieldTree(docType: string): FieldNode[] {
  return fieldTreeMap[docType] || fieldTreeMap.general
}

/** 所有可用的 filter */
export const availableFilters = [
  { value: '', label: '(无)' },
  { value: 'money', label: 'money (分→元)' },
  { value: 'chinese_money', label: 'chinese_money (大写)' },
  { value: 'date', label: 'date (日期)' },
  { value: 'datetime', label: 'datetime (日期时间)' },
  { value: 'default', label: 'default (默认值)' },
]
