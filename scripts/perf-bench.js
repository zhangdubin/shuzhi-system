/**
 * 性能基准测试
 * 用法: node scripts/perf-bench.js
 * 输出: 8 个核心端点的 p50/p95/avg 延迟
 */
const BASE = 'http://localhost:8000'

async function login() {
  const r = await fetch(`${BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ account: 'admin', password: 'admin123' }),
  })
  return (await r.json()).token
}

async function bench(name, method, path, body, token, N = 50) {
  const times = []
  for (let i = 0; i < N; i++) {
    const start = Date.now()
    const r = await fetch(`${BASE}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: body ? JSON.stringify(body) : undefined,
    })
    await r.arrayBuffer()
    times.push(Date.now() - start)
  }
  times.sort((a, b) => a - b)
  const p50 = times[Math.floor(N * 0.5)]
  const p95 = times[Math.floor(N * 0.95)]
  const avg = times.reduce((s, t) => s + t, 0) / N
  const min = times[0]
  const max = times[N - 1]
  return { name, N, p50, p95, avg: Math.round(avg), min, max }
}

function fmt(r) {
  return `${r.name.padEnd(35)} N=${r.N}  min=${String(r.min).padStart(3)}ms  p50=${String(r.p50).padStart(3)}ms  p95=${String(r.p95).padStart(3)}ms  avg=${String(r.avg).padStart(3)}ms  max=${String(r.max).padStart(3)}ms`
}

async function main() {
  const token = await login()
  console.log('='.repeat(80))
  console.log('  Performance Benchmark — 数智化管理系统')
  console.log('='.repeat(80))

  const results = []
  results.push(await bench('POST /api/v1/auth/me', 'GET', '/api/v1/auth/me', null, token, 30))
  results.push(await bench('POST /api/v1/dashboard/summary', 'POST', '/api/v1/dashboard/summary', {}, token, 50))
  results.push(await bench('POST /api/v1/contracts/list (50条)', 'POST', '/api/v1/contracts/list', { page: 1, pageSize: 50 }, token, 50))
  results.push(await bench('POST /api/v1/expenses/list (50条)', 'POST', '/api/v1/expenses/list', { page: 1, pageSize: 50 }, token, 50))
  results.push(await bench('POST /api/v1/receivables/list (50条)', 'POST', '/api/v1/receivables/list', { page: 1, pageSize: 50 }, token, 50))
  results.push(await bench('POST /api/v1/projects/list (50条)', 'POST', '/api/v1/projects/list', { page: 1, pageSize: 50 }, token, 50))
  results.push(await bench('POST /api/v1/clients', 'POST', '/api/v1/common/clients', { page: 1, pageSize: 50 }, token, 50))
  results.push(await bench('POST /api/v1/ai/ask/ask', 'POST', '/api/v1/ai/ask/ask', { question: '本月收入' }, token, 30))
  results.push(await bench('POST /api/v1/ai/risk/scan', 'POST', '/api/v1/ai/risk/scan', { objectType: 'contract', objectId: 1 }, token, 30))
  results.push(await bench('POST /api/v1/cron/all', 'POST', '/api/v1/cron/all', {}, token, 10))
  results.push(await bench('GET  /api/v1/admin/users/list', 'POST', '/api/v1/admin/users/list', { page: 1, pageSize: 20 }, token, 20))
  results.push(await bench('GET  /api/v1/admin/roles/list', 'POST', '/api/v1/admin/roles/list', {}, token, 20))

  console.log()
  for (const r of results) {
    console.log(fmt(r))
  }

  // 汇总
  const totalAvg = results.reduce((s, r) => s + r.avg, 0) / results.length
  const slowP95 = results.filter(r => r.p95 > 500)
  console.log()
  console.log('='.repeat(80))
  console.log(`  端点数: ${results.length} | 平均延迟: ${Math.round(totalAvg)}ms | p95 > 500ms: ${slowP95.length}`)
  if (slowP95.length > 0) {
    console.log('  ⚠️  慢端点:')
    for (const r of slowP95) {
      console.log(`    - ${r.name} p95=${r.p95}ms`)
    }
  } else {
    console.log('  ✅ 所有端点 p95 < 500ms')
  }
  console.log('='.repeat(80))
}

main().catch(e => { console.error(e); process.exit(1) })
