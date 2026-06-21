/**
 * 截 P7C 1 页（AiExtract）+ design 对比
 */
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE_FRONTEND = 'http://localhost:80'
const BASE_DESIGN = 'http://localhost:8090'

async function run() {
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1400 } })
  const page = await ctx.newPage()
  page.setDefaultTimeout(20000)

  await page.goto(`${BASE_FRONTEND}/login`)
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear() })
  await page.reload()
  await page.waitForSelector('input[placeholder*="账号" i]', { timeout: 10000 })
  await page.fill('input[placeholder*="账号" i]', 'admin')
  await page.fill('input[type="password"]', 'admin123')
  await page.click('button:has-text("登 录")')
  await page.waitForURL(/\/dashboard/, { timeout: 10000 })

  const outDir = '/Users/trisome/Desktop/开发/数智化系统new/docs/screenshots/compare'
  fs.mkdirSync(outDir, { recursive: true })

  console.log('[compare] 截实际: p7c-ai-extract')
  await page.goto(`${BASE_FRONTEND}/ai/extract`)
  await page.waitForTimeout(2000)
  await page.screenshot({ path: path.join(outDir, '2-real-p7c-ai-extract.png'), fullPage: true })

  // 点击"开始 AI 抽取"按钮（如果存在），让 demo fields 渲染出来
  try {
    const extractBtn = page.locator('button:has-text("开始 AI 抽取")')
    if (await extractBtn.isVisible({ timeout: 1000 })) {
      await extractBtn.click()
      await page.waitForTimeout(2500) // 等 demo fields 加载
      await page.screenshot({ path: path.join(outDir, '2-real-p7c-ai-extract-result.png'), fullPage: true })
      console.log('  ✅ 抽取结果截图')
    }
  } catch {}

  try {
    const res = await page.goto(`${BASE_DESIGN}/ai-extract-demo.html`)
    if (res && res.status() === 200) {
      await page.waitForTimeout(800)
      await page.screenshot({ path: path.join(outDir, '1-design-p7c-ai-extract.png'), fullPage: true })
      console.log('  ✅ design saved')
    }
  } catch (e) {
    console.log(`  ⚠️ design skip: ${e.message}`)
  }

  await browser.close()
  console.log('[compare] ✅ P7C 截图完成')
}

run().catch(e => { console.error(e); process.exit(1) })
