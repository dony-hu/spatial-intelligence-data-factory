#!/usr/bin/env python3
from __future__ import annotations

import json

from dashboard_data_lib import append_event, parse_args_for_event, refresh_by_event, write_outputs


def main() -> int:
    args = parse_args_for_event()
    try:
        payload = json.loads(args.payload_json)
        if not isinstance(payload, dict):
            payload = {"raw": args.payload_json}
    except json.JSONDecodeError:
        payload = {"raw": args.payload_json}

    event = append_event(
        event_type=args.event_type,
        workpackage_id=args.workpackage_id,
        summary=args.summary,
        operator=args.operator,
        payload=payload,
    )
    outputs = refresh_by_event(args.event_type)
    write_outputs(outputs)

    print(
        json.dumps(
            {
                "ok": True,
                "event": event,
                "refreshed_files": sorted(outputs.keys()),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
