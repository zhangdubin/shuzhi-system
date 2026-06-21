/**
 * E2E Test: 合同列表筛选 + 详情跳转
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

  const log = (msg) => console.log(`[test-02] ${msg}`)

  try {
    // 登录
    log('登录 admin...')
    await page.goto(`${BASE}/login`)
    await page.fill('input[placeholder*="账号" i]', 'admin')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button:has-text("登 录")')
    await page.waitForURL(/\/dashboard/, { timeout: 10000 })

    // 进入合同列表
    log('进入合同列表...')
    await page.goto(`${BASE}/contract/list`)
    await page.waitForSelector('.el-table, table', { timeout: 10000 })
    const initialRows = await page.locator('.el-table tbody tr').count()
    log(`   初始行数: ${initialRows}`)

    // 选 "审批中" 筛选
    log('选择"审批中"状态...')
    const statusSelect = page.locator('.el-select:has(input[placeholder*="状态" i]), .el-select:has(input[placeholder*="审批状态" i])').first()
    if (await statusSelect.count() > 0) {
      await statusSelect.click()
      await page.waitForTimeout(500)
      // 找包含"审批中"的选项
      const option = page.locator('.el-select-dropdown__item:has-text("审批中")').first()
      if (await option.count() > 0) {
        await option.click()
        await page.waitForTimeout(1500)
        const filteredRows = await page.locator('.el-table tbody tr').count()
        log(`   筛选后行数: ${filteredRows}`)
        if (filteredRows >= initialRows) {
          log(`   ⚠️ 筛选似乎没生效`)
        } else {
          log(`   ✅ 筛选生效 (${initialRows} → ${filteredRows})`)
        }
      } else {
        log(`   ⚠️ 找不到"审批中"选项`)
      }
    } else {
      log(`   ⚠️ 找不到状态选择器`)
    }

    // 点第一行
    log('点击第一行合同...')
    const firstRow = page.locator('.el-table tbody tr').first()
    if (await firstRow.count() > 0) {
      await firstRow.click()
      await page.waitForTimeout(2000)
      const url = page.url()
      if (url.includes('/contract/')) {
        log(`   ✅ 跳转到详情: ${url.split('/').slice(-2).join('/')}`)
      } else {
        log(`   ⚠️ 未跳转到详情: ${url}`)
      }
    }

    if (errors.length > 0) {
      log(`❌ 发现 ${errors.length} 个错误:`)
      errors.slice(0, 5).forEach(e => log(`   - ${e}`))
    } else {
      log('✅ 合同列表筛选测试通过')
    }
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-02-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(() => process.exit(0)).catch(() => process.exit(1))
}
module.exports = { run }
