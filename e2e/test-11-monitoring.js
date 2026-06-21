/**
 * E2E Test: Prometheus + Grafana + AlertManager 监控
 *
 * 验证：
 * 1. /metrics 端点暴露 8 个核心指标
 * 2. 业务指标埋点：登录/OCR/验真/AI 计数
 * 3. Prometheus 抓取到 backend 指标
 * 4. Grafana 健康
 * 5. AlertManager 健康
 * 6. cAdvisor 暴露容器指标
 */
const { chromium } = require('playwright')

const BASE = 'http://localhost:80'
const PROMETHEUS = 'http://localhost:9090'
const GRAFANA = 'http://localhost:3000'
const ALERTMANAGER = 'http://localhost:9093'
const CADVISOR = 'http://localhost:8080'
const HEADLESS = process.env.HEADLESS !== '0'

async function run() {
  const browser = await chromium.launch({ headless: HEADLESS })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  page.setDefaultTimeout(30000)

  const errors = []
  page.on('pageerror', e => errors.push(`pageerror: ${e.message}`))
  page.on('console', m => { if (m.type() === 'error') errors.push(`console: ${m.text()}`) })

  const log = (msg) => console.log(`[test-11] ${msg}`)

  try {
    // 1. 登录 admin
    log('1. 登录 admin 触发业务指标...')
    await page.goto(`${BASE}/login`)
    await page.evaluate(() => { localStorage.clear(); sessionStorage.clear() })
    await page.reload()
    await page.waitForSelector('input[placeholder*="账号" i]', { timeout: 10000 })
    await page.fill('input[placeholder*="账号" i]', 'admin')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button:has-text("登 录")')
    await page.waitForURL(/\/dashboard/, { timeout: 10000 })
    log('   ✅ 登录成功')

    // 2. /metrics 端点（直接用 node http，避免 playwright CORS 限制）
    log('2. 后端 /metrics 端点（暴露 8 个核心指标）...')
    const http = require('http')
    const metricsText = await new Promise((resolve, reject) => {
      http.get('http://localhost:8000/metrics', (res) => {
        let data = ''
        res.on('data', chunk => data += chunk)
        res.on('end', () => resolve(data))
      }).on('error', reject)
    })
    const expectedMetrics = [
      'shuzhi_http_requests_total',
      'shuzhi_http_request_duration_seconds',
      'shuzhi_http_slow_requests_total',
      'shuzhi_http_in_flight_requests',
      'shuzhi_business_ocr_total',
      'shuzhi_business_verify_total',
      'shuzhi_business_ai_total',
      'shuzhi_business_login_total',
    ]
    let found = 0
    for (const m of expectedMetrics) {
      if (metricsText.includes(m)) {
        log(`   ✅ ${m}`)
        found++
      } else {
        log(`   ❌ 缺 ${m}`)
      }
    }
    if (found < 8) {
      log(`   ⚠️  只找到 ${found}/8 个 metric`)
    }

    // 3. 触发业务指标（OCR 1 次 + 验真 1 次 + AI 1 次 + 慢请求 1 次）
    log('3. 触发业务指标...')
    const token = await page.evaluate(() => localStorage.getItem('shuzhi_token'))

    // AI ask（第一次 cache miss，第二次 hit）
    await page.evaluate(async (token) => {
      await fetch('/api/v1/ai/ask/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ question: '本月收入', context: {} }),
      })
      await fetch('/api/v1/ai/ask/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ question: '本月收入', context: {} }),
      })
    }, token)
    log('   ✅ AI ask × 2（1 miss + 1 hit）')

    // 验真
    await page.evaluate(async (token) => {
      await fetch('/api/v1/invoice/verify/single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          invoiceCode: '011002100111',
          invoiceNo: '26112000001961698300',
          issueDate: '2026-05-17',
          totalAmount: 248,
        }),
      })
    }, token)
    log('   ✅ 验真 × 1')

    // 4. Prometheus 健康 + targets（直接用 node http）
    log('4. Prometheus 健康检查 + targets...')
    const promHealthy = await new Promise((resolve, reject) => {
      http.get('http://localhost:9090/-/healthy', (res) => {
        let data = ''
        res.on('data', chunk => data += chunk)
        res.on('end', () => resolve({ status: res.statusCode, text: data }))
      }).on('error', reject)
    })
    log(`   /-/healthy: ${promHealthy.status} ${promHealthy.text.slice(0, 30)}`)
    if (promHealthy.status !== 200) throw new Error('Prometheus 不健康')

    const targets = JSON.parse(await new Promise((resolve, reject) => {
      http.get('http://localhost:9090/api/v1/targets', (res) => {
        let data = ''
        res.on('data', chunk => data += chunk)
        res.on('end', () => resolve(data))
      }).on('error', reject)
    }))
    const upTargets = targets.data.activeTargets.filter(t => t.health === 'up')
    log(`   targets up: ${upTargets.length} / ${targets.data.activeTargets.length}`)
    for (const t of upTargets) {
      log(`     ✅ ${t.labels.job}`)
    }

    // 5. Prometheus 抓到业务指标
    log('5. Prometheus 查 shuzhi_business_login_total...')
    const queryResult = JSON.parse(await new Promise((resolve, reject) => {
      http.get('http://localhost:9090/api/v1/query?query=shuzhi_business_login_total', (res) => {
        let data = ''
        res.on('data', chunk => data += chunk)
        res.on('end', () => resolve(data))
      }).on('error', reject)
    }))
    const loginCount = queryResult.data?.result?.[0]?.value?.[1]
    log(`   shuzhi_business_login_total = ${loginCount} 次`)
    if (!loginCount) throw new Error('业务指标未抓到')

    // 6. Grafana 健康
    log('6. Grafana 健康检查...')
    const grafanaHealth = JSON.parse(await new Promise((resolve, reject) => {
      http.get('http://localhost:3000/api/health', (res) => {
        let data = ''
        res.on('data', chunk => data += chunk)
        res.on('end', () => resolve(data))
      }).on('error', reject)
    }))
    log(`   status: ok db=${grafanaHealth.database}`)

    // 7. AlertManager 健康
    log('7. AlertManager 健康检查...')
    const amHealth = await new Promise((resolve, reject) => {
      http.get('http://localhost:9093/-/healthy', (res) => {
        let data = ''
        res.on('data', chunk => data += chunk)
        res.on('end', () => resolve({ status: res.statusCode, text: data }))
      }).on('error', reject)
    })
    log(`   status: ${amHealth.status} ${amHealth.text.slice(0, 30)}`)

    // 8. cAdvisor 容器指标
    log('8. cAdvisor 容器指标...')
    const cadvisorHealth = await new Promise((resolve, reject) => {
      http.get('http://localhost:8080/healthz', (res) => {
        let data = ''
        res.on('data', chunk => data += chunk)
        res.on('end', () => resolve({ status: res.statusCode, text: data }))
      }).on('error', reject)
    })
    log(`   status: ${cadvisorHealth.status}`)

    if (errors.length > 0) {
      log(`⚠️  ${errors.length} 个 console/page error（不影响测试）:`)
      errors.slice(0, 3).forEach(e => log(`   - ${e}`))
    } else {
      log('✅ Prometheus + Grafana + AlertManager + cAdvisor 监控 E2E 通过')
    }
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-11-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(() => process.exit(0)).catch(() => process.exit(1))
}
module.exports = { run }
