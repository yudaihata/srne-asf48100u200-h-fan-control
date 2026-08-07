#!/usr/bin/env python3
"""Build a reviewed fan-control candidate from an exact user-supplied image."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    VerificationError,
    apply_profile,
    load_manifest,
    resolve_profile,
    sha256,
    validate_candidate,
    validate_source,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest()
    profile = resolve_profile(args.profile, manifest)
    source = args.source.read_bytes()
    validate_source(source, manifest)
    candidate, changed = apply_profile(source, profile)
    validate_candidate(candidate, profile, manifest, source)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(candidate)
    print(f"profile:          {args.profile}")
    print(f"source sha256:    {sha256(source)}")
    print(f"candidate sha256: {sha256(candidate)}")
    print("changed offsets:  " + ", ".join(f"{offset:#x}" for offset in changed))
    print(f"wrote:            {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, VerificationError) as exc:
        raise SystemExit(f"error: {exc}") from exc
