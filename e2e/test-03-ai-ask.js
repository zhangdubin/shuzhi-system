/**
 * E2E Test: AI 智能问答
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

  const log = (msg) => console.log(`[test-03] ${msg}`)

  try {
    log('登录 admin...')
    await page.goto(`${BASE}/login`)
    await page.fill('input[placeholder*="账号" i]', 'admin')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button:has-text("登 录")')
    await page.waitForURL(/\/dashboard/, { timeout: 10000 })

    // 进入 AI 问答
    log('进入 AI 智能问答...')
    await page.goto(`${BASE}/ai/ask`)
    await page.waitForTimeout(2000)

    // 验证页头
    const title = await page.textContent('.ai-ask-title').catch(() => null)
    log(`   页头: ${title || '(未找到)'}`)

    // 输入问题
    log('输入问题: "本月签了多少合同"...')
    const input = page.locator('.ai-ask-input textarea')
    await input.fill('本月签了多少合同？')
    await page.click('.ai-ask-input button:has-text("发送")')

    // 等 AI 响应
    log('等待 AI 响应...')
    await page.waitForTimeout(5000)

    // 验证响应
    const messages = await page.locator('.msg').count()
    log(`   对话数: ${messages}`)

    const lastAi = await page.locator('.msg.assistant .msg-content').last().textContent().catch(() => null)
    log(`   AI 回答: ${lastAi?.slice(0, 80) || '(无)'}`)

    // 测推荐问题
    const sugCount = await page.locator('.ai-ask-suggestions .suggestion').count()
    log(`   推荐问题数: ${sugCount}`)

    if (messages >= 2 && lastAi) {
      log('✅ AI 问答测试通过')
    } else {
      log(`⚠️ AI 问答不完整`)
    }

    if (errors.length > 0) {
      log(`❌ ${errors.length} 个错误:`)
      errors.slice(0, 3).forEach(e => log(`   - ${e}`))
    }
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-03-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(() => process.exit(0)).catch(() => process.exit(1))
}
module.exports = { run }
