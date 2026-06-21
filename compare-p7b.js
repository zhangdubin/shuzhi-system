/**
 * 截 P7B 4 页 admin 截图
 */
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE_FRONTEND = 'http://localhost:80'

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
    { name: 'p7b-admin-user',  realPath: '/admin/user' },
    { name: 'p7b-admin-role',  realPath: '/admin/role' },
    { name: 'p7b-admin-dict',  realPath: '/admin/dict' },
    { name: 'p7b-admin-dept',  realPath: '/admin/dept' },
  ]

  for (const p of pages) {
    console.log(`[compare] 截实际: ${p.name}`)
    await page.goto(`${BASE_FRONTEND}${p.realPath}`)
    await page.waitForTimeout(2000)
    await page.screenshot({ path: path.join(outDir, `2-real-${p.name}.png`), fullPage: true })
  }

  await browser.close()
  console.log('[compare] ✅ P7B 4 页截图完成')
}

run().catch(e => { console.error(e); process.exit(1) })
