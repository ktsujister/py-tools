#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request


TERMINAL_STATES = {"success", "failed", "canceled", "skipped", "manual"}


def run_glab(args):
    result = subprocess.run(
        ["glab", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def get_latest_pipeline_id():
    output = run_glab(["ci", "list"])
    for line in output.splitlines():
        line = line.strip()
        if not line or not line.startswith("("):
            continue

        # Example:
        # (success) • #23753   (#0)  issues/394-some-issue
        parts = line.split("#", 1)
        if len(parts) < 2:
            continue

        rest = parts[1]
        pipeline_num = ""
        for ch in rest:
            if ch.isdigit():
                pipeline_num += ch
            else:
                break

        if pipeline_num:
            return int(pipeline_num)

    raise RuntimeError("Could not determine latest pipeline ID from `glab ci list` output")


def get_pipeline_info(pipeline_id):
    output = run_glab(
        ["ci", "get", "--pipeline-id", str(pipeline_id), "--output", "json"]
    )
    data = json.loads(output)

    # glab JSON shape may vary a bit by version, so tolerate a few possibilities.
    status = (
        data.get("status")
        or data.get("pipeline_status")
        or data.get("state")
    )
    web_url = data.get("web_url") or data.get("url")
    ref = data.get("ref") or data.get("branch")

    if not status:
        raise RuntimeError(f"Could not find pipeline status in JSON: {data}")

    return {
        "status": status,
        "web_url": web_url,
        "ref": ref,
        "raw": data,
    }


def send_slack(webhook_url, text):
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"Slack webhook failed with HTTP {resp.status}")


def main():
    parser = argparse.ArgumentParser(description='CLI tool for monitoring glab pipeline until finished.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("pipeline_id", nargs="?", type=int,
                        help="specify `pipeline_id` to check. uses newest if not specified.")
    parser.add_argument("--interval", type=int, default=30, help="specify `interval` to poll for changes")
    parser.add_argument("--notify-running", action="store_true",
                        help="specify to get notification when status changed.")
    args = parser.parse_args()

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL is not set", file=sys.stderr)
        return 2

    pipeline_id = args.pipeline_id or get_latest_pipeline_id()
    print(f"Monitoring pipeline #{pipeline_id}", flush=True)

    last_status = None

    while True:
        info = get_pipeline_info(pipeline_id)
        status = info["status"]
        ref = info["ref"] or "unknown"
        web_url = info["web_url"] or ""

        if status != last_status:
            print(f"Pipeline #{pipeline_id}: {status}", flush=True)
            if args.notify_running and last_status is not None:
                send_slack(
                    webhook_url,
                    f"GitLab pipeline #{pipeline_id} on `{ref}` changed to `{status}`\n{web_url}",
                )
            last_status = status

        if status in TERMINAL_STATES:
            send_slack(
                webhook_url,
                f"GitLab pipeline #{pipeline_id} on `{ref}` finished with `{status}`\n{web_url}",
            )
            return 0 if status == "success" else 1

        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
