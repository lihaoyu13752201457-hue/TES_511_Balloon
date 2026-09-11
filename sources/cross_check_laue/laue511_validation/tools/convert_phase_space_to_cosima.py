#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.cosima_bridge import convert_phase_space_csv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--history")
    args = parser.parse_args()
    summary = convert_phase_space_csv(args.input, args.output, args.metadata, args.history)
    print(
        json.dumps(
            {
                "n_rows": summary["n_rows"],
                "metadata": args.metadata,
                "history_join": summary["history_join"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
