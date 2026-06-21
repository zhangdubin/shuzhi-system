/**
 * E2E Test: 通知中心 + 一键检查 cron
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

  const log = (msg) => console.log(`[test-06] ${msg}`)

  try {
    log('登录 admin...')
    await page.goto(`${BASE}/login`)
    await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); })
    await page.reload()
    await page.fill('input[placeholder*="账号" i]', 'admin')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button:has-text("登 录")')
    await page.waitForURL(/\/dashboard/, { timeout: 10000 })

    // 一键检查
    log('点击"立即检查"...')
    await page.waitForTimeout(2000)
    const checkBtn = page.locator('button:has-text("立即检查")')
    if (await checkBtn.count() > 0) {
      await checkBtn.click()
      await page.waitForTimeout(2000)
      log('   ✅ 一键检查触发')
    } else {
      log('   ⚠️ 找不到"立即检查"按钮')
    }

    // 进入通知中心
    log('进入通知中心...')
    await page.goto(`${BASE}/notice`)
    await page.waitForTimeout(2000)

    const noticeCount = await page.locator('.notice-item').count()
    log(`   通知条数: ${noticeCount}`)

    // 等 SSE 推过来
    log('等 SSE 推送（最多 10s）...')
    await page.waitForTimeout(8000)
    const newCount = await page.locator('.notice-item').count()
    log(`   通知条数（8s 后）: ${newCount}`)

    // 触发 API 创建 expense 看实时推
    log('API 创建 expense 触发实时...')
    const token = await page.evaluate(() => localStorage.getItem('shuzhi_token') || sessionStorage.getItem('shuzhi_token'))
    const apiResp = await page.evaluate(async (token) => {
      const r = await fetch('/api/v1/expenses/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          title: 'E2E-TEST-06-' + Date.now(),
          category: '差旅',
          amount: 666,
          expenseDate: '2026-06-14',
        }),
      })
      return { status: r.status, body: await r.json() }
    }, token)
    log(`   API status: ${apiResp.status}, code: ${apiResp.body.code}`)

    // 等 SSE 推过来
    await page.waitForTimeout(5000)
    const finalCount = await page.locator('.notice-item').count()
    log(`   通知条数（最终）: ${finalCount}`)

    if (finalCount > 0) {
      log('✅ 通知中心测试通过')
    } else {
      log('⚠️ 通知未到达')
    }

    if (errors.length > 0) {
      log(`❌ ${errors.length} 个错误:`)
      errors.slice(0, 3).forEach(e => log(`   - ${e}`))
    }
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-06-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(() => process.exit(0)).catch(() => process.exit(1))
}
module.exports = { run }
