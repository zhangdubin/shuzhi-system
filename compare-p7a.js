/**
 * 截 P7A 5 页 design vs 实际对比
 * - AiCenter 有 design/ai-center.html
 * - AiAsk/AiRisk/AiTasks/AiAlerts 无 design
 */
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE_FRONTEND = 'http://localhost:80'
const BASE_DESIGN = 'http://localhost:8090'

async function run() {
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1100 } })
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

  const pages = [
    { name: 'p7a-ai-center',  realPath: '/ai',         designFile: 'ai-center.html' },
    { name: 'p7a-ai-ask',     realPath: '/ai/ask',     designFile: 'none' },
    { name: 'p7a-ai-risk',    realPath: '/ai/risk',    designFile: 'none' },
    { name: 'p7a-ai-tasks',   realPath: '/ai/tasks',   designFile: 'none' },
    { name: 'p7a-ai-alerts',  realPath: '/ai/alerts',  designFile: 'none' },
  ]

  for (const p of pages) {
    console.log(`[compare] 截实际: ${p.name}`)
    await page.goto(`${BASE_FRONTEND}${p.realPath}`)
    await page.waitForTimeout(2000)
    await page.screenshot({ path: path.join(outDir, `2-real-${p.name}.png`), fullPage: true })

    if (p.designFile !== 'none') {
      try {
        const res = await page.goto(`${BASE_DESIGN}/${p.designFile}`)
        if (res && res.status() === 200) {
          await page.waitForTimeout(800)
          await page.screenshot({ path: path.join(outDir, `1-design-${p.name}.png`), fullPage: true })
          console.log(`  ✅ design saved`)
        }
      } catch (e) {
        console.log(`  ⚠️ design skip: ${e.message}`)
      }
    } else {
      console.log(`  ⚠️ no design (自造)`)
    }
  }

  await browser.close()
  console.log('[compare] ✅ P7A 5 页对比图完成')
}

run().catch(e => { console.error(e); process.exit(1) })
