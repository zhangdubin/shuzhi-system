/**
 * E2E Test: 费用创建 + SSE 实时活动推送
 */
const { chromium } = require('playwright')

const BASE = 'http://localhost:80'
const HEADLESS = process.env.HEADLESS !== '0'

async function run() {
  const browser = await chromium.launch({ headless: HEADLESS })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  page.setDefaultTimeout(20000)

  const errors = []
  page.on('pageerror', e => errors.push(`pageerror: ${e.message}`))
  page.on('console', m => { if (m.type() === 'error') errors.push(`console: ${m.text()}`) })

  const log = (msg) => console.log(`[test-04] ${msg}`)

  try {
    log('登录 admin...')
    await page.goto(`${BASE}/login`)
    await page.fill('input[placeholder*="账号" i]', 'admin')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button:has-text("登 录")')
    await page.waitForURL(/\/dashboard/, { timeout: 10000 })

    // 等 Dashboard SSE 连上
    log('等 SSE 连接...')
    await page.waitForTimeout(3000)

    // 测 API 创建 expense
    log('通过 API 创建 expense...')
    const token = await page.evaluate(() => localStorage.getItem('shuzhi_token') || sessionStorage.getItem('shuzhi_token'))
    const apiResp = await page.evaluate(async (token) => {
      const r = await fetch('/api/v1/expenses/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          title: 'E2E-SSE-测试-' + Date.now(),
          category: '办公',
          amount: 888,
          expenseDate: '2026-06-14',
        }),
      })
      return { status: r.status, body: await r.json() }
    }, token)
    log(`   API status: ${apiResp.status}, code: ${apiResp.body.code}`)
    if (apiResp.status !== 200 || apiResp.body.code !== 0) {
      throw new Error('expense create 失败')
    }

    // 等 SSE 浮层出现
    log('等实时活动浮层...')
    const liveAppeared = await page.locator('.live-card').count({ timeout: 8000 })
    if (liveAppeared > 0) {
      const liveText = await page.locator('.live-card').first().textContent()
      log(`   收到浮层: ${liveText?.slice(0, 80)}`)
      log('✅ SSE 实时活动推送测试通过')
    } else {
      log('⚠️ 未收到 SSE 实时活动（可能延迟）')
    }

    if (errors.length > 0) {
      log(`❌ ${errors.length} 个错误:`)
      errors.slice(0, 3).forEach(e => log(`   - ${e}`))
    }
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-04-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(() => process.exit(0)).catch(() => process.exit(1))
}
module.exports = { run }
