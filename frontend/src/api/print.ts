/**
 * UDPE 统一单据打印引擎 — 前端 SDK
 *
 * 设计文档：plans/udpe-design/design.md §十
 * 后端端点：/api/v1/print/preview | /api/v1/print/pdf | /api/v1/print/log
 *           /api/v1/admin/print-templates | /api/v1/admin/print-templates/{tid}
 *
 * 用法：
 *   import { printApi } from '@/api/print'
 *   await printApi.pdf({ templateCode: 'invoice_v1', data: { _resolver: invoiceId } })
 */
import { http } from '@/utils/request'
import type { AxiosRequestConfig } from 'axios'

/** 打印请求选项。 */
export interface PrintOptions {
  /** 渲染模式：'pdf'（下载/预览 PDF）或 'html'（返回 HTML 字符串） */
  renderMode?: 'pdf' | 'pdf-preview' | 'html'
  /** 打印份数（V1 暂未实现真多份，仅记日志） */
  copies?: number
  /** 水印文字（V1 简化） */
  watermark?: string
  /** 纸张（V1 暂未消费） */
  paper?: string
  /** 来源模块名（合同/报销/发票/费用），用于审计 */
  sourceModule?: string
  /** 来源业务单据 ID */
  sourceId?: string | number
}

/** 业务数据。约定：含 `_resolver` 字段时由后端走对应 Resolver 取数。 */
export type PrintData = Record<string, any>

/** 模板元信息。 */
export interface PrintTemplateInfo {
  id: number
  code: string
  name: string
  docType: string
  paper: string
  status: string
  isDefault: boolean
  version: number
  description?: string | null
}

/** 预览响应。 */
export interface BatchStats {
  total: number
  success: number
  failed: number
  elapsedMs: number
}

export interface PrintPreviewResponse {
  html: string
  templateId: number
  logId: number
  templateCode: string
  templateName: string
  elapsedMs: number
}

/** 日志行。 */
export interface PrintLogRow {
  id: number
  templateId: number | null
  templateCode: string
  docType: string
  action: string
  status: string
  operatorId: number | null
  operatorName: string | null
  sourceModule: string | null
  sourceId: string | null
  elapsedMs: number | null
  errorMsg: string | null
  pdfSize: number | null
  createdAt: string | null
}

/** 通过 blob URL 触发浏览器下载。 */
function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  setTimeout(() => {
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, 500)
}

export const printApi = {
  /**
   * 导出 PDF：返回 Blob，调用方决定是触发下载 / window.open / iframe 预览。
   *
   * 默认行为：通过临时 a[download] 触发下载，文件名 = {templateCode}.pdf
   *
   * 用法：
   *   await printApi.pdf({ templateCode: 'invoice_v1', data: { _resolver: id } })
   *   // 仅拿 blob：
   *   const blob = await printApi.pdfBlob({ templateCode, data })
   */
  async pdf(args: { templateCode: string; data?: PrintData; options?: PrintOptions; silent?: boolean }): Promise<void> {
    const blob = await this.pdfBlob(args)
    const filename = `${args.templateCode}.pdf`
    triggerDownload(blob, filename)
  },

  /** M3 阶段 1: 编辑器实时预览, 不写日志, 直接传 schemaJson.
   *  用于 AdminPrintTemplateEditor.vue 三栏布局的右侧预览. */
  async previewSchema(args: {
    docType: string
    schemaJson: any
    data?: any
    options?: PrintOptions
  }): Promise<{ html: string; elapsedMs: number }> {
    const r = (await http.post<{ html: string; elapsedMs: number }>('/print/preview-schema', {
      docType: args.docType,
      schemaJson: args.schemaJson,
      data: args.data || {},
      options: { renderMode: 'html', ...(args.options || {}) },
    })) as { html: string; elapsedMs: number }
    return r
  },

  /** 批量打印: 同一模板 + 多个业务主键 -> 合并 PDF 流 (M2 阶段 9).
   *  返回 Promise<{ blob, stats }> 包含 PDF blob 和统计 (total/success/failed/elapsedMs). */
  async batchPdfBlob(args: {
    templateCode: string
    items: Array<string | number>
    options?: PrintOptions
    silent?: boolean
  }): Promise<{ blob: Blob; stats: BatchStats }> {
    const config: AxiosRequestConfig = {
      responseType: 'blob',
      silent: args.silent,
    }
    const resp = (await http.post<Blob>('/print/batch', {
      templateCode: args.templateCode,
      items: args.items.map(id => ({ id })),
      options: { renderMode: 'pdf', ...(args.options || {}) },
    }, config)) as Blob
    const stats: BatchStats = {
      total: args.items.length,
      success: args.items.length,
      failed: 0,
      elapsedMs: 0,
    }
    return { blob: resp, stats }
  },

  /** 批量打印并触发浏览器下载. */
  async batchPdf(args: {
    templateCode: string
    items: Array<string | number>
    options?: PrintOptions
    silent?: boolean
  }): Promise<BatchStats> {
    const { blob } = await this.batchPdfBlob(args)
    const filename = `batch_${args.templateCode}_${Date.now()}.pdf`
    triggerDownload(blob, filename)
    return {
      total: args.items.length,
      success: args.items.length,
      failed: 0,
      elapsedMs: 0,
    }
  },

  /** 仅拿 Blob，不触发下载。 */
  async pdfBlob(args: { templateCode: string; data?: PrintData; options?: PrintOptions; silent?: boolean }): Promise<Blob> {
    const config: AxiosRequestConfig = {
      responseType: 'blob',
      silent: args.silent,
    }
    const blob = (await http.post<Blob>('/print/pdf', {
      templateCode: args.templateCode,
      data: args.data || {},
      options: { renderMode: 'pdf', ...(args.options || {}) },
    }, config)) as Blob
    return blob
  },

  /** 预览：返回 HTML 字符串。 */
  async preview(args: { templateCode: string; data?: PrintData; options?: PrintOptions }): Promise<PrintPreviewResponse> {
    return (await http.post<PrintPreviewResponse>('/print/preview', {
      templateCode: args.templateCode,
      data: args.data || {},
      options: { renderMode: 'html', ...(args.options || {}) },
    })) as PrintPreviewResponse
  },

  /** 列出模板（管理后台用）。 */
  async listTemplates(params: { docType?: string; status?: string; page?: number; pageSize?: number } = {}): Promise<{ list: PrintTemplateInfo[]; total: number }> {
    return (await http.get('/admin/print-templates', { params })) as { list: PrintTemplateInfo[]; total: number }
  },

  /** 查日志。 */
  async listLogs(payload: { page?: number; pageSize?: number; templateCode?: string; operatorId?: number } = {}): Promise<{ list: PrintLogRow[]; total: number }> {
    return (await http.post('/print/log', payload)) as { list: PrintLogRow[]; total: number }
  },

  /** 模板详情。 */
  async getTemplate(tid: number): Promise<PrintTemplateInfo> {
    return (await http.get(`/admin/print-templates/${tid}`)) as PrintTemplateInfo
  },

  /** 发布模板。 */
  async publishTemplate(id: number): Promise<PrintTemplateInfo> {
    return (await http.post('/admin/print-templates/publish', { id })) as PrintTemplateInfo
  },

  /** 归档模板。 */
  async archiveTemplate(id: number): Promise<PrintTemplateInfo> {
    return (await http.post('/admin/print-templates/archive', { id })) as PrintTemplateInfo
  },

  /** 创建模板。 */
  async createTemplate(payload: any): Promise<PrintTemplateInfo> {
    return (await http.post('/admin/print-templates', payload)) as PrintTemplateInfo
  },

  /** 删除模板（仅 draft/archived 状态可删）。 */
  async deleteTemplate(id: number): Promise<void> {
    await http.post('/admin/print-templates/delete', { id })
  },

  /** 更新模板. M3 阶段 1.1 修复: 后端端点用 ?tid= 而不是 body {id} */
  async updateTemplate(tid: number, payload: any): Promise<PrintTemplateInfo> {
    return (await http.post(`/admin/print-templates/update?tid=${tid}`, payload)) as PrintTemplateInfo
  },
}

export default printApi

// ===== M3 阶段 4: Excel 模板导入 =====

export interface ExcelImportSheet {
  name: string
  rowCount: number
  colCount: number
  mergedCount: number
  schemaJson: { body: any[] }
  placeholders: string[]
  html: string
}

export interface ExcelImportPreview {
  filename: string
  totalSheets: number
  sheets: ExcelImportSheet[]
}

export const excelImportApi = {
  /** 上传 xlsx → 解析每个 sheet 为 schemaJson + 预览 HTML (不写库) */
  async preview(file: File): Promise<ExcelImportPreview> {
    const form = new FormData()
    form.append('file', file)
    const r = await http.post<ExcelImportPreview>('/admin/print-templates/import/excel/preview', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return r as ExcelImportPreview
  },

  /** 把解析后的 schemaJson 保存为新模板 */
  async confirm(payload: {
    code: string
    name: string
    docType: string
    paper?: string
    orientation?: string
    schemaJson: { body: any[] }
    sourceFile?: string
    sourceSheet?: string
  }): Promise<PrintTemplateInfo> {
    return (await http.post('/admin/print-templates/import/excel/confirm', payload)) as PrintTemplateInfo
  },
}

// ===== M3 阶段 4 下半: Word 模板导入 =====

export interface DocxImportPreview {
  filename: string
  totalElements: number
  schemaJson: { body: any[] }
  placeholders: string[]
  warnings: string[]
  html: string
}

export const docxImportApi = {
  /** 上传 docx → 解析为 grid schemaJson + 预览 HTML (不写库) */
  async preview(file: File): Promise<DocxImportPreview> {
    const form = new FormData()
    form.append('file', file)
    const r = await http.post<DocxImportPreview>('/admin/print-templates/import/docx/preview', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return r as DocxImportPreview
  },

  /** 把解析后的 schemaJson 保存为新模板 */
  async confirm(payload: {
    code: string
    name: string
    docType: string
    paper?: string
    orientation?: string
    schemaJson: { body: any[] }
    sourceFile?: string
  }): Promise<PrintTemplateInfo> {
    return (await http.post('/admin/print-templates/import/docx/confirm', payload)) as PrintTemplateInfo
  },
}
