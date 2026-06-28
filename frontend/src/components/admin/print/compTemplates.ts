/**
 * UDPE 组件默认 schema 模板 (M3 阶段 3 设计器 V1)
 * 7 个组件: title / text / spacer / line / grid / table / pagebreak
 * 新增的组件会自动分配临时 id, 保存前剔除.
 */
export type CompType = 'title' | 'text' | 'spacer' | 'line' | 'grid' | 'table' | 'pagebreak' | 'qrcode' | 'barcode'

let _idCounter = 0
const _idPrefix = 'c'
export function newCompId(): string {
  _idCounter += 1
  return `${_idPrefix}${_idCounter}_${Math.random().toString(36).slice(2, 6)}`
}

export interface CompMeta {
  type: CompType
  label: string
  icon: string
  desc: string
  default: () => Record<string, any>
}

export const COMP_PALETTE: CompMeta[] = [
  {
    type: 'title', label: '标题', icon: '🅣', desc: '大字号标题 (h1)',
    default: () => ({ type: 'title', text: '标题文字', fontSize: 20, align: 'center' }),
  },
  {
    type: 'text', label: '文本', icon: '¶', desc: '普通文本 (支持 {{...}} 模板插值)',
    default: () => ({ type: 'text', text: '正文内容 {{ form.title | default("—") }}', fontSize: 12 }),
  },
  {
    type: 'spacer', label: '间距', icon: '↕', desc: '垂直间距 (mm)',
    default: () => ({ type: 'spacer', height: 6 }),
  },
  {
    type: 'line', label: '分割线', icon: '—', desc: '水平分割线',
    default: () => ({ type: 'line', color: '#E5E7EB' }),
  },
  {
    type: 'grid', label: '表格网格', icon: '⊞', desc: 'Excel 风格单元格 (4 列默认)',
    default: () => ({
      type: 'grid', border: true, borderColor: '#000000', borderWidth: 1, colCount: 4,
      rows: [
        { height: 12, cells: [{ text: '标签', span: 1, bold: true, align: 'center' }, { text: '值', span: 3 }] },
      ],
    }),
  },
  {
    type: 'table', label: '数据表', icon: '⊟', desc: '绑定数组数据 (columns + bind)',
    default: () => ({
      type: 'table',
      bind: 'form.details',
      columns: [
        { key: 'title', label: '项目' },
        { key: 'amount', label: '金额', type: 'money' },
      ],
    }),
  },
  {
    type: 'pagebreak', label: '分页', icon: '⤓', desc: '强制分页符',
    default: () => ({ type: 'pagebreak' }),
  },
  {
    type: 'qrcode', label: '二维码', icon: '⊞', desc: 'QR Code (支持 {{...}} 模板插值)',
    default: () => ({ type: 'qrcode', data: '{{ form.code }}', size: 120, label: '' }),
  },
  {
    type: 'barcode', label: '条码', icon: '║║', desc: 'Code128 条形码',
    default: () => ({ type: 'barcode', data: '{{ form.formNo }}', height: 50, label: '' }),
  },
]

/** 复制一个组件 (分配新 id) */
export function cloneComp(meta: CompMeta): Record<string, any> {
  return { id: newCompId(), ...meta.default() }
}

/** 找到 type 对应的 meta */
export function findMeta(type: string): CompMeta | undefined {
  return COMP_PALETTE.find(m => m.type === type)
}
