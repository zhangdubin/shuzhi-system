/**
 * E2E Test: 登录 + Dashboard 关键数据
 * 用法: npx playwright test e2e/test-01-login-dashboard.js
 */
const { chromium } = require('playwright')

const BASE = 'http://localhost:80'
const HEADLESS = process.env.HEADLESS !== '0'
const TIMEOUT = 30000

async function run() {
  const browser = await chromium.launch({ headless: HEADLESS })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  page.setDefaultTimeout(TIMEOUT)

  const errors = []
  page.on('pageerror', e => errors.push(`pageerror: ${e.message}`))
  page.on('console', m => { if (m.type() === 'error') errors.push(`console: ${m.text()}`) })

  const log = (msg) => console.log(`[test-01] ${msg}`)

  try {
    // 1. 打开登录页
    log('1. 打开登录页...')
    await page.goto(`${BASE}/login`)
    await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); })
    await page.reload()
    await page.waitForSelector('input[placeholder*="账号" i]', { timeout: 5000 })

    // 2. 填表 + 登录
    log('2. 输入 admin 凭据...')
    await page.fill('input[placeholder*="账号" i]', 'admin')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button:has-text("登 录")')

    // 3. 等跳转
    log('3. 等待跳转 dashboard...')
    await page.waitForURL(/\/dashboard/, { timeout: 10000 })

    // 4. 验证 Dashboard 关键数据
    log('4. 验证 Dashboard 元素...')
    const greeting = await page.textContent('.welcome h1, .welcome h2, [class*="welcome"] h1, [class*="welcome"] h2').catch(() => null)
    log(`   问候语: ${greeting?.slice(0, 50) || '(未找到)'}`)

    // 检查 KPI 卡
    const kpiCount = await page.locator('[class*="kpi"], [class*="KPI"]').count()
    log(`   KPI 卡数: ${kpiCount}`)

    // 5. 验证 Console 错误
    if (errors.length > 0) {
      log(`❌ 发现 ${errors.length} 个错误:`)
      errors.forEach(e => log(`   - ${e}`))
      throw new Error('Console 错误')
    }

    log('✅ 登录 + Dashboard 测试通过')
    return { success: true, kpiCount }
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-01-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(r => process.exit(0)).catch(e => process.exit(1))
}

module.exports = { run }
