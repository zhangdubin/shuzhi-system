const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  // 监听 ElMessageBox 弹窗
  let messageBoxShown = 0;
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0,200)); });

  // 1. 模拟 localStorage 有过期 token
  await page.goto('http://localhost/');
  await page.waitForTimeout(1500);
  await page.evaluate(() => {
    // 写入一个明显过期的 token
    localStorage.setItem('shuzhi_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxMDAwLCJ0eXBlIjoiYWNjZXNzIn0.invalidsig');
    localStorage.setItem('shuzhi_user', JSON.stringify({
      userId: 1, name: '旧用户', role: '用户', permissions: [], isAdmin: false,
    }));
  });

  // 2. 访问 dashboard（带过期 token）
  console.log('=== 测试 1: 访问 dashboard 触发 401 ===');
  await page.goto('http://localhost/dashboard');
  await page.waitForTimeout(3000);
  // 看看有没有弹窗
  const messageBox = await page.$('.el-message-box');
  console.log('  弹窗存在:', !!messageBox);
  if (messageBox) {
    const title = await messageBox.$eval('.el-message-box__title', el => el.textContent).catch(() => '?');
    console.log('  弹窗标题:', title);
  }
  console.log('  当前 URL:', page.url());

  // 3. 访问 login（带过期 token）— 关键测试
  console.log('\n=== 测试 2: 访问 /login 带过期 token ===');
  await page.goto('http://localhost/login');
  await page.waitForTimeout(3000);
  // 注意：这里之前会触发 fetchMe → 401 → 弹窗
  const messageBox2 = await page.$('.el-message-box');
  console.log('  弹窗存在:', !!messageBox2, '（修复后应该是 false）');
  console.log('  当前 URL:', page.url());
  // 看看 token 是否被清了
  const tokenAfter = await page.evaluate(() => localStorage.getItem('shuzhi_token'));
  console.log('  localStorage token:', tokenAfter);

  // 4. 在 /login 页面拦截 401 看看会不会弹
  console.log('\n=== 测试 3: 在 login 页面手动触发 401 ===');
  // 用一个无效 token 调 API
  const resp = await page.evaluate(async () => {
    const r = await fetch('/api/v1/auth/me', {
      headers: { Authorization: 'Bearer invalid' },
    });
    return { status: r.status };
  });
  console.log('  API 响应:', resp);
  await page.waitForTimeout(1500);
  const messageBox3 = await page.$('.el-message-box');
  console.log('  弹窗存在:', !!messageBox3, '（修复后应该是 false）');

  console.log('\n=== 错误 ===');
  console.log('Console errors:', errors.length);
  errors.forEach(e => console.log('  - ' + e));
  await browser.close();
})();
