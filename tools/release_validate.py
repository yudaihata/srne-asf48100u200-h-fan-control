#!/usr/bin/env python3
"""Validate every reviewed profile against the pristine vendor source."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from common import apply_profile, load_manifest, sha256, validate_candidate, validate_source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = load_manifest()
    source = args.source.read_bytes()
    validate_source(source, manifest)
    candidates = []
    for name, profile in manifest["profiles"].items():
        candidate, changed = apply_profile(source, profile)
        validate_candidate(candidate, profile, manifest, source)
        candidates.append(
            {
                "profile": name,
                "sha256": sha256(candidate),
                "changed_offsets": [f"0x{offset:X}" for offset in changed],
                "evidence": profile["evidence"],
            }
        )
    report = {
        "format": "srne-fan-release-validation-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repository": "yudaihata/srne-asf48100u200-h-fan-control",
        "repository_commit": os.environ.get("GITHUB_SHA", "local-working-tree"),
        "source_sha256": sha256(source),
        "profile_count": len(candidates),
        "candidates": candidates,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
