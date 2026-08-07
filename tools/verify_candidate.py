#!/usr/bin/env python3
"""Verify candidate hash, structure, and optionally its exact source diff."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    VerificationError,
    load_manifest,
    resolve_profile,
    sha256,
    validate_candidate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--source", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest()
    profile = resolve_profile(args.profile, manifest)
    candidate = args.candidate.read_bytes()
    source = args.source.read_bytes() if args.source else None
    changed = validate_candidate(candidate, profile, manifest, source)
    print(f"candidate sha256: {sha256(candidate)}")
    print(f"profile:          {args.profile}")
    if changed is None:
        print("source diff:      not checked (pass --source for exact-diff verification)")
    else:
        print("changed offsets:  " + ", ".join(f"{offset:#x}" for offset in changed))
    print("result:           verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, VerificationError) as exc:
        raise SystemExit(f"error: {exc}") from exc
