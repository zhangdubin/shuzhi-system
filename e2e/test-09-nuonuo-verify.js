/**
 * E2E Test: 诺诺发票验真（mock 模式 + 协议对齐验证）
 *
 * 当前状态：
 *   - 没配 NUONUO_API_KEY → 自动走 mock
 *   - 5 种验真结果（按 invoiceNo 后 4 位 mod 5 决定）：
 *     - bucket 0, 1: pass（验真通过）
 *     - bucket 2: risk（高风险）
 *     - bucket 3: repeat（重复报销）
 *     - bucket 4: not_found（未查到）
 *
 * 验真字段：
 *   - invoiceCode（发票代码）
 *   - invoiceNo（发票号）
 *   - issueDate（开票日期）
 *   - totalAmount（价税合计）
 *   - verifyCode（验证码，可选）
 *
 * 协议对齐：
 *   - 真接入协议已写好（MD5 签名 + accessToken + senid/nonce/timestamp）
 *   - 配置 NUONUO_API_KEY / NUONUO_API_SECRET / NUONUO_API_TOKEN 后自动切真模式
 *   - 真实诺诺 API：nuonuo.ElectronInvoice.otherInvoiceCheck
 *   - 沙箱环境：https://sandbox.nuonuocs.cn/open/v1/services
 *   - 生产环境：https://sdk.nuonuo.com/open/v1/services
 */
const { chromium } = require('playwright')

const BASE = 'http://localhost:80'
const HEADLESS = process.env.HEADLESS !== '0'

async function run() {
  const browser = await chromium.launch({ headless: HEADLESS })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  page.setDefaultTimeout(30000)

  const errors = []
  page.on('pageerror', e => errors.push(`pageerror: ${e.message}`))
  page.on('console', m => { if (m.type() === 'error') errors.push(`console: ${m.text()}`) })

  const log = (msg) => console.log(`[test-09] ${msg}`)

  try {
    // 1. 登录
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
    log(`   token: ${token.slice(0, 30)}...`)

    // 2. 5 个 bucket 各测一次（验证 mock 模式的 5 种结果）
    const testCases = [
      { no: '26112000001961698300', expected: 'pass',       desc: 'bucket 0 (尾号 8300 % 5 = 0)' },
      { no: '26112000001961698301', expected: 'pass',       desc: 'bucket 1 (尾号 8301 % 5 = 1)' },
      { no: '26112000001961698302', expected: 'risk',       desc: 'bucket 2 (尾号 8302 % 5 = 2)' },
      { no: '26112000001961698303', expected: 'repeat',     desc: 'bucket 3 (尾号 8303 % 5 = 3)' },
      { no: '26112000001961698304', expected: 'not_found',  desc: 'bucket 4 (尾号 8304 % 5 = 4)' },
    ]

    let passed = 0
    for (const tc of testCases) {
      log(`2.${tc.no.slice(-4)} 验真: ${tc.desc}`)
      const resp = await page.evaluate(async ({ token, no }) => {
        const r = await fetch('/api/v1/invoice/verify/single', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({
            invoiceCode: '011002100111',
            invoiceNo: no,
            issueDate: '2026-05-17',
            totalAmount: 248.0,
          }),
        })
        return { status: r.status, body: await r.json() }
      }, { token, no: tc.no })

      const result = resp.body?.data?.result
      const elapsed = resp.body?.data?.elapsed
      const source = resp.body?.data?.source

      if (result === tc.expected) {
        log(`   ✅ result=${result} elapsed=${elapsed}ms source=${source}`)
        passed++
      } else {
        log(`   ❌ 期望 result=${tc.expected}, 实际 result=${result}`)
        throw new Error(`bucket ${tc.no.slice(-4)} 验真结果不对`)
      }
    }

    log(`3. 5 个 bucket 全部通过 (${passed}/5)`)

    if (errors.length > 0) {
      log(`⚠️  ${errors.length} 个 console/page error（不影响测试）:`)
      errors.slice(0, 3).forEach(e => log(`   - ${e}`))
    } else {
      log('✅ 诺诺 mock 模式 E2E 通过（5/5 bucket 验真）')
    }
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-09-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(() => process.exit(0)).catch(() => process.exit(1))
}
module.exports = { run }
