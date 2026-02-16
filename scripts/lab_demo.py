#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def _http_json(method: str, url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url=url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=90) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"HTTP {exc.code} {url} -> {detail}") from exc


def cmd_optimize(args: argparse.Namespace) -> None:
    payload = {
        "caller": args.caller,
        "sample_spec": "sample",
        "sample_size": args.sample_size,
        "candidate_count": args.candidate_count,
        "records": [
            {"raw_id": f"{args.batch_id}-r1", "raw_text": "深圳市福田区福中三路100号"},
            {"raw_id": f"{args.batch_id}-r2", "raw_text": "深圳市南山区科技园南区1号"},
            {"raw_id": f"{args.batch_id}-r3", "raw_text": "广州市天河区体育东路1号"},
            {"raw_id": f"{args.batch_id}-r4", "raw_text": "杭州市西湖区文三路1号"},
        ],
    }
    result = _http_json("POST", f"{args.api_base}/lab/optimize/{args.batch_id}", payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("")
    print(f"change_id: {result.get('change_id')}")
    print("next:")
    print(f"  python scripts/lab_demo.py approve --change-id {result.get('change_id')} --api-base {args.api_base}")
    print(f"  python scripts/lab_demo.py activate --change-id {result.get('change_id')} --api-base {args.api_base}")


def cmd_approve(args: argparse.Namespace) -> None:
    result = _http_json(
        "POST",
        f"{args.api_base}/change-requests/{args.change_id}/approve",
        {"approver": args.approver, "comment": args.comment},
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_activate(args: argparse.Namespace) -> None:
    change = _http_json("GET", f"{args.api_base}/change-requests/{args.change_id}")
    ruleset_id = str(change.get("to_ruleset_id") or "")
    if not ruleset_id:
        raise RuntimeError("change request missing to_ruleset_id")
    result = _http_json(
        "POST",
        f"{args.api_base}/rulesets/{ruleset_id}/activate",
        {"change_id": args.change_id, "caller": args.caller, "reason": args.reason},
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_replay(args: argparse.Namespace) -> None:
    result = _http_json("GET", f"{args.api_base}/lab/change_requests/{args.change_id}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lab Mode demo commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    optimize = subparsers.add_parser("optimize", help="run lab optimize and create pending change request")
    optimize.add_argument("--api-base", default="http://127.0.0.1:8000/v1/governance")
    optimize.add_argument("--batch-id", required=True)
    optimize.add_argument("--caller", default="lab-admin")
    optimize.add_argument("--sample-size", type=int, default=4)
    optimize.add_argument("--candidate-count", type=int, default=3)
    optimize.set_defaults(func=cmd_optimize)

    approve = subparsers.add_parser("approve", help="approve an existing change request")
    approve.add_argument("--api-base", default="http://127.0.0.1:8000/v1/governance")
    approve.add_argument("--change-id", required=True)
    approve.add_argument("--approver", default="admin-reviewer")
    approve.add_argument("--comment", default="approved in lab demo")
    approve.set_defaults(func=cmd_approve)

    activate = subparsers.add_parser("activate", help="activate ruleset for approved change request")
    activate.add_argument("--api-base", default="http://127.0.0.1:8000/v1/governance")
    activate.add_argument("--change-id", required=True)
    activate.add_argument("--caller", default="admin")
    activate.add_argument("--reason", default="lab demo rollout")
    activate.set_defaults(func=cmd_activate)

    replay = subparsers.add_parser("replay", help="show replay view for change request")
    replay.add_argument("--api-base", default="http://127.0.0.1:8000/v1/governance")
    replay.add_argument("--change-id", required=True)
    replay.set_defaults(func=cmd_replay)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
