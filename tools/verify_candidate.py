#!/usr/bin/env python3
"""Verify a reviewed or explicitly unreviewed fan-control candidate."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    VerificationError,
    load_manifest,
    materialize_custom_profile,
    resolve_profile,
    sha256,
    validate_candidate,
    validate_source,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--profile")
    parser.add_argument("--start-c", type=int)
    parser.add_argument("--max-c", type=int)
    parser.add_argument("--stop-c", type=int)
    parser.add_argument(
        "--acknowledge-unreviewed",
        action="store_true",
        help="required for custom temperatures not in the reviewed manifest",
    )
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    custom_requested = args.start_c is not None or args.max_c is not None or args.stop_c is not None
    if bool(args.profile) == custom_requested:
        parser.error("choose either --profile or custom --start-c/--max-c values")
    if custom_requested and (args.start_c is None or args.max_c is None):
        parser.error("custom mode requires --start-c and --max-c")
    if custom_requested and not args.acknowledge_unreviewed:
        parser.error("custom mode requires --acknowledge-unreviewed")
    if custom_requested and args.source is None:
        parser.error("custom verification requires --source")
    return args


def main() -> int:
    args = parse_args()
    manifest = load_manifest()
    candidate = args.candidate.read_bytes()
    source = args.source.read_bytes() if args.source else None

    if args.profile:
        profile = resolve_profile(args.profile, manifest)
        mode = f"reviewed profile {args.profile}"
    else:
        stop_c = args.stop_c if args.stop_c is not None else args.start_c - 3
        validate_source(source, manifest)
        profile, expected_candidate, _ = materialize_custom_profile(
            source, args.start_c, args.max_c, stop_c
        )
        if candidate != expected_candidate:
            raise VerificationError("Candidate bytes differ from the custom settings")
        mode = f"UNREVIEWED custom {args.start_c}/{args.max_c}/{stop_c} C"

    changed = validate_candidate(candidate, profile, manifest, source)
    print(f"candidate sha256: {sha256(candidate)}")
    print(f"mode:             {mode}")
    if not args.profile:
        print("warning:          custom temperatures are not pre-reviewed or runtime-validated")
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
