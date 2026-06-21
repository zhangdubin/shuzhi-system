// perf/scenarios/scenario-2-business-core.js
// 场景 2：业务核心 5 接口混合（合同/项目/费用/回款/发票）
// 模拟真实用户：80% 列表查询 + 20% 创建/详情
import http from 'k6/http';
import { check } from 'k6';
import { Trend, Rate } from 'k6/metrics';

const listDuration = new Trend('list_duration', true);
const detailDuration = new Trend('detail_duration', true);
const createDuration = new Trend('create_duration', true);
const errorRate = new Rate('errors');

export const options = {
  scenarios: {
    business_core: {
      executor: 'constant-arrival-rate',
      rate: 20,        // 80 RPS 稳态（中等负载）
      timeUnit: '1s',
      duration: '60s',
      preAllocatedVUs: 30,
      maxVUs: 100,
    },
  },
  thresholds: {
    'http_req_duration{scenario:business_core}': ['p(95)<800', 'p(99)<1500'],
    'errors': ['rate<0.05'],
  },
};

const BASE = 'http://localhost:8000';

// 缓存 token（每个 VU 登录一次）
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

  // 80% 列表 + 20% 详情
  const r = Math.random();
  if (r < 0.8) {
    // 列表（5 个 domain 随机）
    const domain = ['contracts', 'projects', 'expenses', 'receivables'][Math.floor(Math.random() * 4)];
    const res = http.post(
      `${BASE}/api/v1/${domain}/list`,
      JSON.stringify({ page: 1, pageSize: 20 }),
      authHeader
    );
    listDuration.add(res.timings.duration);
    const ok = check(res, { [`${domain}/list 200`]: (r) => r.status === 200 });
    if (!ok) errorRate.add(1);
  } else {
    // 详情（取列表第一条 id）
    const domain = ['contracts', 'projects', 'expenses', 'receivables'][Math.floor(Math.random() * 4)];
    const listRes = http.post(
      `${BASE}/api/v1/${domain}/list`,
      JSON.stringify({ page: 1, pageSize: 1 }),
      authHeader
    );
    if (listRes.status !== 200) { errorRate.add(1); return; }
    const list = JSON.parse(listRes.body).data?.list || [];
    if (list.length === 0) return;
    // 主键的 query 参数名（contractId / projectId / expenseId / receivableId）
    const idKey = domain.replace(/s$/, 'Id');  // contracts→contractId, projects→projectId
    // 不同 domain 主键位置不同：contracts/expenses 用 domain+Id，projects/receivables 用 id
    let id = list[0][idKey];
    if (id === undefined) id = list[0].id;
    // 详情接口用 query 参数 ?<idKey>=<id>（按 openapi 规范）
    const res = http.post(
      `${BASE}/api/v1/${domain}/detail?${idKey}=${id}`,
      null,
      authHeader
    );
    detailDuration.add(res.timings.duration);
    const ok = check(res, { [`${domain}/detail 200`]: (r) => r.status === 200 });
    if (!ok) errorRate.add(1);
  }
}
