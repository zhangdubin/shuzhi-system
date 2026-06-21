/**
 * 导出工具
 * - exportCsv: 浏览器侧生成 CSV 并触发下载（不依赖后端）
 *   - 自动加 UTF-8 BOM，Excel 中文不乱码
 *   - 字段含 , " 换行 时按 RFC 4180 用双引号包裹 + 转义内部双引号
 */
export type CsvCell = string | number | boolean | null | undefined
export type CsvRow = Record<string, CsvCell>
export interface CsvColumn<T extends CsvRow> {
  /** 表头（中文） */
  label: string
  /** 数据 key（点路径支持 e.g. "user.name"） */
  key: string
  /** 自定义格式化 */
  format?: (row: T) => CsvCell
}

function getByPath(obj: any, path: string): any {
  if (obj == null) return undefined
  if (path.indexOf('.') === -1) return obj[path]
  return path.split('.').reduce((acc, k) => (acc == null ? acc : acc[k]), obj)
}

function escapeCell(v: CsvCell): string {
  if (v == null) return ''
  const s = String(v)
  // RFC 4180: 若包含 , " 换行 则用 " 包裹并将 " 替换为 ""
  if (/[",\r\n]/.test(s)) {
    return '"' + s.replace(/"/g, '""') + '"'
  }
  return s
}

export function rowsToCsv<T extends CsvRow>(rows: T[], columns: CsvColumn<T>[]): string {
  const head = columns.map(c => escapeCell(c.label)).join(',')
  const body = rows.map(r => columns.map(c => {
    const raw = c.format ? c.format(r) : getByPath(r, c.key)
    return escapeCell(raw)
  }).join(',')).join('\r\n')
  // RFC 4180 推荐 CRLF；空数据也要有表头
  return head + (body ? '\r\n' + body : '')
}

/** 触发浏览器下载 */
export function downloadCsv(filename: string, csv: string) {
  // UTF-8 BOM 让 Excel 正确识别中文编码
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function exportCsv<T extends CsvRow>(filename: string, rows: T[], columns: CsvColumn<T>[]) {
  const csv = rowsToCsv(rows, columns)
  downloadCsv(filename, csv)
}
