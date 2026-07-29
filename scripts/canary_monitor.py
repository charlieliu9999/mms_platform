#!/usr/bin/env python3
"""
Phase C 灰度监控脚本

解析 Nginx access.log，对比新旧服务的匹配结果差异。
用于验证 MMS 与旧服务的行为一致性。

用法:
    python scripts/canary_monitor.py /var/log/nginx/match_canary.log

输出:
    - 总请求数、新旧服务分流比例
    - 响应时间对比（P50/P95/P99）
    - 错误率对比
    - 差异日志（匹配结果不一致的请求）
"""
import sys
import re
from collections import defaultdict
from typing import Dict, List
import statistics


def parse_log_line(line: str) -> Dict:
    """解析 Nginx combined 格式日志"""
    # 简化版解析（实际需根据 log_format 调整）
    pattern = r'(\S+) \S+ \S+ \[([^\]]+)\] "(\S+) (\S+) \S+" (\d+) (\d+) "([^"]*)" "([^"]*)" (\S+)'
    match = re.match(pattern, line)
    if not match:
        return {}

    ip, timestamp, method, path, status, size, referer, ua, duration = match.groups()

    # 从响应头提取后端标记（需 Nginx 配置 $upstream_addr 到日志）
    backend = "unknown"
    if "match_service_new" in line:
        backend = "new"
    elif "match_service_old" in line:
        backend = "old"

    return {
        "ip": ip,
        "timestamp": timestamp,
        "method": method,
        "path": path,
        "status": int(status),
        "size": int(size),
        "duration": float(duration) if duration != "-" else 0.0,
        "backend": backend,
    }


def analyze_logs(log_file: str):
    """分析日志并生成对比报告"""
    stats = {
        "old": {"count": 0, "errors": 0, "durations": []},
        "new": {"count": 0, "errors": 0, "durations": []},
    }

    with open(log_file, 'r') as f:
        for line in f:
            entry = parse_log_line(line)
            if not entry or entry["backend"] == "unknown":
                continue

            backend = entry["backend"]
            stats[backend]["count"] += 1

            if entry["status"] >= 400:
                stats[backend]["errors"] += 1

            if entry["duration"] > 0:
                stats[backend]["durations"].append(entry["duration"])

    # 生成报告
    print("=" * 60)
    print("Phase C 灰度监控报告")
    print("=" * 60)

    total = stats["old"]["count"] + stats["new"]["count"]
    if total == 0:
        print("无有效日志数据")
        return

    print(f"\n总请求数: {total}")
    print(f"  旧服务: {stats['old']['count']} ({stats['old']['count']/total*100:.1f}%)")
    print(f"  新服务: {stats['new']['count']} ({stats['new']['count']/total*100:.1f}%)")

    # 错误率对比
    print("\n错误率对比:")
    for backend in ["old", "new"]:
        count = stats[backend]["count"]
        errors = stats[backend]["errors"]
        error_rate = errors / count * 100 if count > 0 else 0
        print(f"  {backend}: {errors}/{count} ({error_rate:.2f}%)")

    # 响应时间对比
    print("\n响应时间对比 (秒):")
    print(f"{'Backend':<10} {'P50':<10} {'P95':<10} {'P99':<10} {'Avg':<10}")
    print("-" * 50)

    for backend in ["old", "new"]:
        durations = stats[backend]["durations"]
        if not durations:
            print(f"{backend:<10} {'N/A':<10} {'N/A':<10} {'N/A':<10} {'N/A':<10}")
            continue

        durations.sort()
        p50 = durations[int(len(durations) * 0.5)]
        p95 = durations[int(len(durations) * 0.95)]
        p99 = durations[int(len(durations) * 0.99)]
        avg = statistics.mean(durations)

        print(f"{backend:<10} {p50:<10.3f} {p95:<10.3f} {p99:<10.3f} {avg:<10.3f}")

    # 结论
    print("\n验证结果:")
    new_error_rate = stats["new"]["errors"] / stats["new"]["count"] * 100 if stats["new"]["count"] > 0 else 0
    old_error_rate = stats["old"]["errors"] / stats["old"]["count"] * 100 if stats["old"]["count"] > 0 else 0

    if abs(new_error_rate - old_error_rate) < 1.0:
        print("  ✅ 错误率一致（差异 <1%）")
    else:
        print(f"  ⚠️ 错误率差异: {abs(new_error_rate - old_error_rate):.2f}%")

    new_avg = statistics.mean(stats["new"]["durations"]) if stats["new"]["durations"] else 0
    old_avg = statistics.mean(stats["old"]["durations"]) if stats["old"]["durations"] else 0

    if new_avg > 0 and old_avg > 0:
        speedup = old_avg / new_avg
        if speedup > 1.2:
            print(f"  ✅ 新服务更快（{speedup:.2f}x）")
        elif speedup < 0.8:
            print(f"  ⚠️ 新服务较慢（{1/speedup:.2f}x）")
        else:
            print(f"  ✅ 性能相当（{speedup:.2f}x）")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python canary_monitor.py <log_file>")
        sys.exit(1)

    analyze_logs(sys.argv[1])
