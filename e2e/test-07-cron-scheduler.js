/**
 * E2E Test: 定时任务调度器
 * 验证 /cron/jobs API 返回 3 个任务
 */
const { chromium } = require('playwright')

const BASE = 'http://localhost:80'
const HEADLESS = process.env.HEADLESS !== '0'

async function run() {
  const browser = await chromium.launch({ headless: HEADLESS })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  page.setDefaultTimeout(15000)

  const errors = []
  page.on('pageerror', e => errors.push(`pageerror: ${e.message}`))
  page.on('console', m => { if (m.type() === 'error') errors.push(`console: ${m.text()}`) })

  const log = (msg) => console.log(`[test-07] ${msg}`)

  try {
    log('登录 admin...')
    await page.goto(`${BASE}/login`)
    await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); })
    await page.reload()
    await page.fill('input[placeholder*="账号" i]', 'admin')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button:has-text("登 录")')
    await page.waitForURL(/\/dashboard/, { timeout: 10000 })

    // 直接调 /cron/jobs API
    log('调用 /cron/jobs API...')
    const token = await page.evaluate(() => localStorage.getItem('shuzhi_token'))
    const jobsResp = await page.evaluate(async (token) => {
      const r = await fetch('/api/v1/cron/jobs', { headers: { 'Authorization': `Bearer ${token}` } })
      return { status: r.status, body: await r.json() }
    }, token)
    log(`   status: ${jobsResp.status}`)
    log(`   code: ${jobsResp.body.code}`)

    const data = jobsResp.body.data
    if (!data?.running) {
      throw new Error('scheduler 未运行')
    }
    log(`   running: ${data.running}, jobs: ${data.jobs.length}`)

    // 验证 3 个 job
    const expectedJobs = ['daily_all_checks', 'evening_overdue_check', 'weekly_contract_expiring']
    for (const jid of expectedJobs) {
      const job = data.jobs.find((j) => j.id === jid)
      if (!job) {
        throw new Error(`缺少 job: ${jid}`)
      }
      if (!job.nextRun) {
        throw new Error(`job ${jid} 无 nextRun`)
      }
      log(`   ✅ ${jid} | next: ${job.nextRun}`)
    }

    // 触发 /cron/all 看是否还正常
    log('触发 /cron/all ...')
    const allResp = await page.evaluate(async (token) => {
      const r = await fetch('/api/v1/cron/all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: '{}',
      })
      return { status: r.status, body: await r.json() }
    }, token)
    log(`   total: ${allResp.body.data?.total}, msg: ${allResp.body.message?.slice(0, 60)}`)

    if (errors.length > 0) {
      log(`❌ ${errors.length} 个错误:`)
      errors.slice(0, 3).forEach(e => log(`   - ${e}`))
    } else {
      log('✅ 定时任务调度器测试通过')
    }
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-07-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(() => process.exit(0)).catch(() => process.exit(1))
}
module.exports = { run }
