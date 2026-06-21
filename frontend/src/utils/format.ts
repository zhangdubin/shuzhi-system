// ============================================================
// 通用格式化工具
// ============================================================

/**
 * 把 confidence 安全转换为 0-100 的数值
 * 兼容 0-1 小数（0.925）和 0-100 整数（92.5）两种后端格式
 */
export function confToPct(raw: any): number {
  const n = Number(raw)
  if (isNaN(n)) return 0
  if (n > 1) return Math.min(100, n)
  return Math.max(0, n * 100)
}

/** "92.5%" 字符串 */
export function fmtConfidence(raw: any): string {
  return confToPct(raw).toFixed(1) + '%'
}

/** 整数百分比字符串 "92%" */
export function fmtConfidenceInt(raw: any): string {
  return Math.round(confToPct(raw)) + '%'
}
