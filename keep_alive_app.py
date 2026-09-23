#!/usr/bin/env python3
"""
TickTask Keep-Alive & Automated Reminder Pinger Daemon
------------------------------------------------------
This lightweight standalone application continuously pings the TickTask Vercel portal
to prevent serverless container cold-starts and ensure automated shift email reminders
trigger on time (18:30, 18:45, 19:00) 24/7 without requiring active web page usage.

Usage:
    python keep_alive_app.py
    python keep_alive_app.py --url https://ticktask-silk.vercel.app --interval 60
"""

import sys
import time
import argparse
import datetime
import urllib.request
import urllib.parse
import json

DEFAULT_URL = "https://ticktask-silk.vercel.app/api/keep-alive"

def ping_server(url: str) -> dict:
    start_time = time.time()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TickTask-KeepAlive-Daemon/2.0 (+https://ticktask-silk.vercel.app)"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            raw_data = resp.read().decode("utf-8")
            try:
                data = json.loads(raw_data)
            except Exception:
                data = {"raw": raw_data[:100]}
            return {
                "success": True,
                "status_code": resp.status,
                "latency_ms": latency_ms,
                "data": data
            }
    except Exception as err:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": False,
            "error": str(err),
            "latency_ms": latency_ms
        }

def main():
    parser = argparse.ArgumentParser(description="TickTask Keep-Alive & Reminder Daemon")
    parser.add_argument("--url", default=DEFAULT_URL, help="Target portal URL or keep-alive endpoint")
    parser.add_argument("--interval", type=int, default=60, help="Ping interval in seconds (default: 60s)")
    args = parser.parse_args()

    target_url = args.url.strip()
    if not target_url.endswith("/api/keep-alive") and not target_url.endswith("/api/health"):
        if target_url.endswith("/"):
            target_url += "api/keep-alive"
        else:
            target_url += "/api/keep-alive"

    print("=" * 80)
    print("🚀 TICKTASK SERVERLESS KEEP-ALIVE & AUTOMATED REMINDER DAEMON")
    print("=" * 80)
    print(f"• Target Portal Endpoint : {target_url}")
    print(f"• Ping Interval          : Every {args.interval} seconds (1 minute)")
    print(f"• Purpose                : Zero Cold Starts & 100% On-Time Shift Reminders")
    print(f"• Press Ctrl+C to stop at any time.")
    print("=" * 80 + "\n")

    ping_count = 0
    success_count = 0

    while True:
        ping_count += 1
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        res = ping_server(target_url)

        if res["success"]:
            success_count += 1
            data_msg = res["data"].get("message") or res["data"].get("status") or "OK"
            users_cnt = res["data"].get("active_users", "N/A")
            print(f"[{now_str}] [# {ping_count:04d}] ✅ Status {res['status_code']} | Latency: {res['latency_ms']}ms | Active Users: {users_cnt} | Msg: {data_msg}")
        else:
            print(f"[{now_str}] [# {ping_count:04d}] ⚠️ Ping Error ({res['latency_ms']}ms): {res['error']}")

        time.sleep(args.interval)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[DAEMON STOPPED] TickTask Keep-Alive daemon terminated by user.")
        sys.exit(0)
