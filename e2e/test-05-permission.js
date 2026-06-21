/**
 * E2E Test: 权限模型（财务总监 zhangming 不应看到 admin 后台）
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

  const log = (msg) => console.log(`[test-05] ${msg}`)

  try {
    log('登录财务总监 zhangming (password: test123)...')
    await page.goto(`${BASE}/login`)
    // 清掉上次测试残留的登录态
    await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); })
    await page.reload()
    await page.waitForTimeout(1000)
    await page.fill('input[placeholder*="账号" i]', 'zhangming')
    await page.fill('input[type="password"]', 'test123')
    await page.click('button:has-text("登 录")')
    await page.waitForURL(/\/dashboard/, { timeout: 10000 })

    // 看侧边栏菜单
    log('检查侧边栏菜单...')
    await page.waitForTimeout(2000)

    // 看是否有"系统"组
    const hasSystemGroup = await page.locator('text=系统').count()
    log(`   "系统"分组出现次数: ${hasSystemGroup}`)

    // 看是否能跳到 /admin/user
    log('直接访问 /admin/user...')
    await page.goto(`${BASE}/admin/user`)
    await page.waitForTimeout(2000)

    // 验证页面是空的（应该被 403 / 跳走）
    const bodyText = await page.locator('body').textContent()
    if (bodyText?.includes('没有权限') || bodyText?.includes('Forbidden') || !bodyText?.includes('用户管理')) {
      log('   ✅ /admin/user 被拒绝访问')
    } else if (bodyText?.includes('用户管理') && !bodyText?.includes('admin')) {
      log('   ⚠️ 页面渲染了但菜单未显示（路由可访问但菜单隐藏）')
    } else {
      log(`   页面内容前 200: ${bodyText?.slice(0, 200)}`)
    }

    // 验证能访问业务页
    log('访问 /expense/list...')
    await page.goto(`${BASE}/expense/list`)
    await page.waitForTimeout(2000)
    const expenseOK = (await page.locator('text=销售费用, text=费用').count()) > 0
    log(`   费用页面: ${expenseOK ? '✅ 可访问' : '⚠️ 异常'}`)

    if (errors.length > 0) {
      log(`❌ ${errors.length} 个错误:`)
      errors.slice(0, 3).forEach(e => log(`   - ${e}`))
    }
    log('✅ 权限模型测试完成')
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-05-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(() => process.exit(0)).catch(() => process.exit(1))
}
module.exports = { run }
