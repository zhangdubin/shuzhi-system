/**
 * E2E Test: 真实 PaddleOCR 识别增值税发票
 * 验证：上传真实发票图（茶馆餐饮 ¥248）→ PaddleOCR 识别 → 字段对得上
 *
 * 测试发票：e2e/fixtures/invoice-茶馆-20260517.png
 * 真实字段：
 *   invoiceNo = 26112000001961698396
 *   issueDate = 2026-05-17
 *   buyerName = 中科世通亨奇（北京）科技有限公司
 *   sellerName = 北京逐鹿茶艺有限责任公司西直门店
 *   totalAmount = 248.00
 *   taxAmount = 14.04
 *   amount = 233.96
 *   taxRate = 0.06
 */
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE = 'http://localhost:80'
const HEADLESS = process.env.HEADLESS !== '0'
const FIXTURE = path.join(__dirname, 'fixtures', 'invoice-茶馆-20260517.png')

async function run() {
  const browser = await chromium.launch({ headless: HEADLESS })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  page.setDefaultTimeout(30000)

  const errors = []
  page.on('pageerror', e => errors.push(`pageerror: ${e.message}`))
  page.on('console', m => { if (m.type() === 'error') errors.push(`console: ${m.text()}`) })

  const log = (msg) => console.log(`[test-08] ${msg}`)

  // 检查 fixture 存在
  if (!fs.existsSync(FIXTURE)) {
    throw new Error(`测试发票不存在: ${FIXTURE}`)
  }
  const stat = fs.statSync(FIXTURE)
  log(`📁 测试发票: ${FIXTURE} (${stat.size} bytes)`)

  try {
    // 1. 登录拿 token
    log('1. 登录 admin...')
    await page.goto(`${BASE}/login`)
    await page.evaluate(() => { localStorage.clear(); sessionStorage.clear() })
    await page.reload()
    await page.waitForSelector('input[placeholder*="账号" i]', { timeout: 10000 })
    await page.fill('input[placeholder*="账号" i]', 'admin')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button:has-text("登 录")')
    await page.waitForURL(/\/dashboard/, { timeout: 10000 })

    const token = await page.evaluate(() => localStorage.getItem('shuzhi_token'))
    if (!token) throw new Error('未拿到 token')
    log(`   token: ${token.slice(0, 30)}...`)

    // 2. 上传 + 识别
    log('2. 上传真实发票给 PaddleOCR 服务...')
    // 先把 fixture 转成 base64，通过 fetch 上传
    const fileBase64 = fs.readFileSync(FIXTURE, 'base64')

    const uploadResp = await page.evaluate(async ({ token, fileBase64 }) => {
      // 把 base64 转成 Blob
      const bin = atob(fileBase64)
      const bytes = new Uint8Array(bin.length)
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
      const blob = new Blob([bytes], { type: 'image/png' })
      const form = new FormData()
      form.append('file', blob, 'invoice-茶馆-20260517.png')
      form.append('type', 'invoice')

      const r = await fetch('/api/v1/invoice/ocr/upload', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: form,
      })
      return { status: r.status, body: await r.json() }
    }, { token, fileBase64 })

    log(`   HTTP: ${uploadResp.status}`)
    log(`   ocrStatus: ${uploadResp.body.data?.ocrStatus}`)
    log(`   confidence: ${uploadResp.body.data?.confidence}`)

    if (uploadResp.body.code !== 0) {
      throw new Error(`上传失败: ${uploadResp.body.message}`)
    }
    if (uploadResp.body.data?.ocrStatus !== 'success') {
      throw new Error(`OCR 识别失败: ${uploadResp.body.data?.error}`)
    }

    const fields = uploadResp.body.data.fields
    log(`   invoiceId: ${uploadResp.body.data.invoiceId}`)

    // 3. 字段校验
    // 后端 service 把 OCR 响应 flatten，fields 顶层就是 value
    log('3. 字段校验...')
    const checks = [
      { field: 'invoiceNo', expected: '26112000001961698396' },
      { field: 'issueDate', expected: '2026-05-17' },
      { field: 'buyerName', expected: '中科世通亨奇（北京）科技有限公司' },
      { field: 'sellerName', expected: '北京逐鹿茶艺有限责任公司西直门店' },
      { field: 'totalAmount', expected: 248.0, tolerance: 0.01 },
      { field: 'taxAmount', expected: 14.04, tolerance: 0.01 },
      { field: 'taxRate', expected: 0.06, tolerance: 0.001 },
    ]

    for (const c of checks) {
      // fields 在上传响应里是 flatten 后的，value 直接是 fields.xxx
      const val = fields[c.field]
      if (val === undefined || val === null) {
        log(`   ❌ 缺字段: ${c.field}`)
        throw new Error(`缺字段: ${c.field}`)
      }
      if (typeof c.expected === 'number') {
        if (Math.abs(val - c.expected) > (c.tolerance || 0.001)) {
          log(`   ❌ ${c.field}: 期望 ${c.expected}, 实际 ${val}`)
          throw new Error(`${c.field} 不对: ${val} vs ${c.expected}`)
        }
      } else {
        if (val !== c.expected) {
          log(`   ❌ ${c.field}: 期望 ${c.expected}, 实际 ${val}`)
          throw new Error(`${c.field} 不对`)
        }
      }
      log(`   ✅ ${c.field} = ${val}`)
    }

    // 4. 置信度检查（> 0.85）
    const conf = uploadResp.body.data.confidence
    if (conf < 0.85) {
      log(`   ⚠️ 综合置信度偏低: ${conf}`)
    } else {
      log(`   ✅ 综合置信度: ${conf}`)
    }

    // 5. 速度检查
    // elapsedMs 在后端 service 里有，但 ocr/recognize API 没直接返
    // 跳过

    if (errors.length > 0) {
      log(`⚠️  ${errors.length} 个 console/page error（不影响测试）:`)
      errors.slice(0, 3).forEach(e => log(`   - ${e}`))
    } else {
      log('✅ PaddleOCR 真实识别 E2E 通过')
    }
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-08-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(() => process.exit(0)).catch(() => process.exit(1))
}
module.exports = { run }
