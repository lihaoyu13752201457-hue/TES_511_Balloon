#!/usr/bin/env python3
"""Exec Cosima after applying controller-owned per-file resource limits."""

from __future__ import annotations

import argparse
import os
import resource


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file-size-limit-bytes", type=int, required=True)
    parser.add_argument("--cosima", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    if args.file_size_limit_bytes <= 0:
        parser.error("--file-size-limit-bytes must be positive")
    resource.setrlimit(
        resource.RLIMIT_FSIZE,
        (args.file_size_limit_bytes, args.file_size_limit_bytes),
    )
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.execv(args.cosima, [args.cosima, "-s", str(args.seed), args.source])


if __name__ == "__main__":
    main()
