#!/usr/bin/env python3
"""
perf/scripts/gen_report.py
k6 summary JSON → Markdown 报告
用法: python3 gen_report.py <k6_summary.json> <scenario_name> > report.md
"""
import json
import sys
import os
from datetime import datetime


def fmt_ms(v):
    if v is None:
        return "-"
    return f"{v:.1f}"


def gen_report(json_path, scenario_name):
    with open(json_path) as f:
        data = json.load(f)

    metrics = data.get("metrics", {})

    # 提取核心指标（k6 0.49+ 把 values 拍扁了）
    def get(metric_name, *sub_keys):
        m = metrics.get(metric_name, {})
        if not m:
            return None
        # 优先取 values 嵌套（k6 老版本），否则取自身（k6 新版本扁平）
        v = m.get("values", m)
        if not sub_keys:
            return v
        result = v
        for k in sub_keys:
            result = result.get(k) if isinstance(result, dict) else None
            if result is None:
                return None
        return result

    http_reqs = get("http_reqs", "count")
    http_failed = get("http_req_failed", "rate")
    http_duration = get("http_req_duration")
    iterations = get("iterations", "count")

    p50 = http_duration.get("p(50)") if http_duration else None
    p90 = http_duration.get("p(90)") if http_duration else None
    p95 = http_duration.get("p(95)") if http_duration else None
    p99 = http_duration.get("p(99)") if http_duration else None
    avg = http_duration.get("avg") if http_duration else None
    max_d = http_duration.get("max") if http_duration else None

    # 渲染
    md = []
    md.append(f"# 压测报告 - {scenario_name}")
    md.append(f"\n**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**原始数据**：`{os.path.basename(json_path)}`")
    md.append(f"**k6 状态**：{'✅ 通过' if data.get('root_group', {}).get('checks', []) else '⚠️ 需检查'}")

    md.append("\n## 1. 总体指标\n")
    md.append("| 指标 | 值 |")
    md.append("|---|---|")
    md.append(f"| HTTP 总请求数 | {http_reqs or '-'} |")
    md.append(f"| VU 迭代次数 | {iterations or '-'} |")
    md.append(f"| 错误率 | {(http_failed * 100 if http_failed else 0):.2f}% |")
    md.append(f"| 平均响应时间 | {fmt_ms(avg)} ms |")
    md.append(f"| P50 | {fmt_ms(p50)} ms |")
    md.append(f"| P90 | {fmt_ms(p90)} ms |")
    md.append(f"| P95 | {fmt_ms(p95)} ms |")
    md.append(f"| P99 | {fmt_ms(p99)} ms |")
    md.append(f"| 最大响应时间 | {fmt_ms(max_d)} ms |")

    # 阈值检查
    md.append("\n## 2. 阈值检查\n")
    thresholds = data.get("options", {}).get("thresholds", {})
    if thresholds:
        md.append("| 阈值 | 状态 |")
        md.append("|---|---|")
        for t_name, t_value in thresholds.items():
            md.append(f"| `{t_name}` = `{t_value}` | 待人工核对 |")
    else:
        md.append("_无阈值配置_")

    # 自定义指标
    custom = {k: v for k, v in metrics.items() if k not in {
        "http_reqs", "http_req_duration", "http_req_failed", "iterations",
        "data_sent", "data_received", "checks"
    }}
    if custom:
        md.append("\n## 3. 自定义指标\n")
        md.append("| 指标 | 平均 | P95 | 最大 |")
        md.append("|---|---|---|---|")
        for name, m in custom.items():
            v = m.get("values", m) if isinstance(m, dict) else {}
            if "avg" in v:
                md.append(f"| `{name}` | {fmt_ms(v.get('avg'))} ms | {fmt_ms(v.get('p(95)'))} ms | {fmt_ms(v.get('max'))} ms |")

    # check 结果（k6 不同版本 checks 是 list 或 dict）
    checks = data.get("root_group", {}).get("checks", {})
    if isinstance(checks, dict):
        checks = [{"name": k, **v} if isinstance(v, dict) else {"name": k, "passes": 0, "fails": 0} for k, v in checks.items()]
    if checks and isinstance(checks, list):
        md.append("\n## 4. Check 结果\n")
        md.append("| 检查项 | 通过/总次数 | 成功率 |")
        md.append("|---|---|---|")
        for c in checks:
            if not isinstance(c, dict):
                continue
            passes = c.get("passes", 0)
            fails = c.get("fails", 0)
            total = passes + fails
            rate = (passes / total * 100) if total else 0
            md.append(f"| {c.get('name', '-')} | {passes}/{total} | {rate:.1f}% |")

    md.append("\n---\n")
    md.append(f"_本报告由 `perf/scripts/gen_report.py` 自动生成_")
    return "\n".join(md)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 gen_report.py <k6_summary.json> <scenario_name>", file=sys.stderr)
        sys.exit(1)
    print(gen_report(sys.argv[1], sys.argv[2]))
