const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1500, height: 1000 } });
  const page = await context.newPage();
  page.on('pageerror', e => console.log('PAGE ERROR:', e.message));

  await page.goto('http://localhost/login');
  await page.waitForTimeout(500);
  await page.fill('input[placeholder*="账号"]', 'admin');
  await page.fill('input[placeholder*="密码"]', 'admin123');
  await page.click('button:has-text("登 录")');
  await page.waitForTimeout(2000);

  // 新建模式
  await page.goto('http://localhost/admin/print-template/editor');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/m3s4_new.png', fullPage: true });

  // 点"导入 Excel"按钮
  await page.click('text=📥 导入 Excel');
  await page.waitForTimeout(1500);
  await page.screenshot({ path: '/tmp/m3s4_dialog.png', fullPage: true });

  // 上传文件
  const fileInput = await page.$('input[type=file]');
  if (fileInput) {
    await fileInput.setInputFiles('/Users/trisome/Desktop/开发/数智化系统new/user_reimbursement.xlsx');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: '/tmp/m3s4_uploaded.png', fullPage: true });
    console.log('File selected');
  }

  // 点"解析"
  await page.click('button:has-text("解析")');
  await page.waitForTimeout(5000);
  await page.screenshot({ path: '/tmp/m3s4_parsed.png', fullPage: true });
  console.log('Parsed');

  // 切到第二步: 命名
  await page.click('button:has-text("下一步")');
  await page.waitForTimeout(1500);
  await page.screenshot({ path: '/tmp/m3s4_name.png', fullPage: true });

  // 点确认导入
  await page.click('button:has-text("确认导入")');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/m3s4_saved.png', fullPage: true });
  console.log('Saved');

  // 看 URL 跳转到编辑模式
  console.log('Final URL:', page.url());

  await browser.close();
})();
