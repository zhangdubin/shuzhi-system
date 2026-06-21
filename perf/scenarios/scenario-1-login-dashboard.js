// perf/scenarios/scenario-1-login-dashboard.js
// 场景 1：登录 + dashboard 拉数据（验证鉴权 + 缓存命中）
// 阶梯负载：10 → 50 → 100 → 200 RPS
import http from 'k6/http';
import { check } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

const loginDuration = new Trend('login_duration', true);
const dashboardDuration = new Trend('dashboard_duration', true);
const errorRate = new Rate('errors');

export const options = {
  scenarios: {
    login_dashboard: {
      executor: 'ramping-arrival-rate',
      startRate: 5,
      timeUnit: '1s',
      preAllocatedVUs: 20,
      maxVUs: 50,
      stages: [
        { duration: '10s', target: 10 },   // 10 RPS
        { duration: '15s', target: 30 },   // 30 RPS
        { duration: '15s', target: 50 },   // 50 RPS（基线峰值）
        { duration: '15s', target: 0 },    // 收尾
      ],
    },
  },
  thresholds: {
    'http_req_duration{scenario:login_dashboard}': ['p(95)<500', 'p(99)<1000'],
    'errors': ['rate<0.05'],
  },
};

const BASE = 'http://localhost:8000';

export default function () {
  // 1. 登录
  const loginRes = http.post(
    `${BASE}/api/v1/auth/login`,
    JSON.stringify({ account: 'admin', password: 'admin123' }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  loginDuration.add(loginRes.timings.duration);
  const loginOk = check(loginRes, {
    'login status 200': (r) => r.status === 200,
    'login has token': (r) => {
      try {
        return !!JSON.parse(r.body).token;
      } catch {
        return false;
      }
    },
  });
  if (!loginOk) {
    errorRate.add(1);
    return;
  }

  const token = JSON.parse(loginRes.body).token;
  const authHeader = { headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } };

  // 2. dashboard summary
  const summaryRes = http.post(`${BASE}/api/v1/dashboard/summary`, '{}', authHeader);
  dashboardDuration.add(summaryRes.timings.duration);
  const dashOk = check(summaryRes, {
    'dashboard status 200': (r) => r.status === 200,
    'dashboard code 0': (r) => {
      try {
        return JSON.parse(r.body).code === 0;
      } catch {
        return false;
      }
    },
  });
  if (!dashOk) errorRate.add(1);

  // 3. dashboard activities
  const actRes = http.post(`${BASE}/api/v1/dashboard/activities`, '{"limit":10}', authHeader);
  check(actRes, {
    'activities status 200': (r) => r.status === 200,
  });
}
