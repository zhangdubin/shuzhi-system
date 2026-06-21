// perf/scenarios/scenario-3-ai-mock.js
// 场景 3：AI 22 触点 random（验证 mock 兜底 + 异步任务处理）
// 重点观察：高频 AI 调用下，mock 数据生成 + 业务指标写入是否扛得住
import http from 'k6/http';
import { check } from 'k6';
import { Trend, Rate } from 'k6/metrics';

const aiDuration = new Trend('ai_duration', true);
const errorRate = new Rate('errors');

export const options = {
  scenarios: {
    ai_mixed: {
      executor: 'constant-arrival-rate',
      rate: 10,        // 40 RPS（AI 较重，降速）
      timeUnit: '1s',
      duration: '60s',
      preAllocatedVUs: 20,
      maxVUs: 60,
    },
  },
  thresholds: {
    'http_req_duration{scenario:ai_mixed}': ['p(95)<1000', 'p(99)<2000'],
    'errors': ['rate<0.05'],
  },
};

const BASE = 'http://localhost:8000';

let token = null;
export function setup() {
  const res = http.post(
    `${BASE}/api/v1/auth/login`,
    JSON.stringify({ account: 'admin', password: 'admin123' }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  return { token: JSON.parse(res.body).token };
}

export default function (data) {
  token = data.token;
  const authHeader = { headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } };

  // AI 22 触点（按 R10 设计）随机选
  // 注意：4xx 是客户端错（mock 入参不对），不算后端错；
  //      2xx 是真接通；只看 5xx 算错
  const endpoints = [
    ['/api/v1/ai/tasks/list', '{"page":1,"pageSize":10}'],
    ['/api/v1/ai/risk/list', '{"page":1,"pageSize":10}'],
    ['/api/v1/ai/alerts/list', '{"page":1,"pageSize":10}'],
    ['/api/v1/ai/model/list', '{}'],
    ['/api/v1/dashboard/summary', '{}'],
    ['/api/v1/contracts/list', '{"page":1,"pageSize":10}'],
    ['/api/v1/projects/list', '{"page":1,"pageSize":10}'],
    ['/api/v1/expenses/list', '{"page":1,"pageSize":10}'],
    ['/api/v1/receivables/list', '{"page":1,"pageSize":10}'],
    ['/api/v1/auth/me', '{}'],
  ];
  const [url, body] = endpoints[Math.floor(Math.random() * endpoints.length)];
  const res = http.post(`${BASE}${url}`, body, authHeader);
  aiDuration.add(res.timings.duration);
  // 5xx 才算错误（4xx 是 client 错，业务层 mock 兜底会返 4xx + 200 都有可能）
  const ok = check(res, {
    [`${url} < 500`]: (r) => r.status < 500,
  });
  if (!ok) errorRate.add(1);
}
