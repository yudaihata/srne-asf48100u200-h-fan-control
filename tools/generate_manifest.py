#!/usr/bin/env python3
"""Generate the public patch manifest from concise reviewed specifications."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, build_custom_profile

FIRMWARE_SPEC = ROOT / "spec" / "firmware.json"
PROFILE_SPEC = ROOT / "spec" / "fan_profiles.json"
OUTPUT = ROOT / "profiles" / "profiles.json"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def generate() -> dict[str, object]:
    source = load_json(FIRMWARE_SPEC)
    profile_spec = load_json(PROFILE_SPEC)
    constraints = profile_spec["constraints"]
    outputs = profile_spec["output_sha256"]
    runtime_evidence = profile_spec["runtime_evidence"]
    profiles: dict[str, object] = {}

    for start_c in constraints["allowed_start_c"]:
        for max_c in constraints["allowed_max_c"]:
            if max_c - start_c < constraints["minimum_span_c"]:
                continue
            stop_c = start_c - constraints["stop_delta_c"]
            name = f"fan{start_c}C_max{max_c}C_off{stop_c}C"
            profile = build_custom_profile(start_c, max_c, stop_c)
            profile.pop("review_status")
            changed_offsets: list[str] = []
            for patch in profile["patches"]:
                offset = int(patch["offset"], 0)
                expected = bytes.fromhex(patch["expected_hex"])
                replacement = bytes.fromhex(patch["replacement_hex"])
                changed_offsets.extend(
                    f"0x{offset + index:X}"
                    for index, (before, after) in enumerate(zip(expected, replacement))
                    if before != after
                )
            profile["changed_offsets"] = changed_offsets
            profile["output_sha256"] = outputs[name]
            profile["evidence"] = {
                "static_encoding": "confirmed-static",
                "candidate_identity": (
                    "stock-equivalent"
                    if outputs[name] == source["sha256"]
                    else "confirmed-static"
                ),
                "runtime": (
                    "runtime-observed" if name in runtime_evidence else "not-established"
                ),
                "runtime_document": runtime_evidence.get(name),
            }
            profiles[name] = profile

    if set(outputs) != set(profiles):
        missing = sorted(set(profiles) - set(outputs))
        extra = sorted(set(outputs) - set(profiles))
        raise ValueError(f"output hash set mismatch; missing={missing}, extra={extra}")

    return {
        "format_version": 2,
        "generated_from": ["spec/firmware.json", "spec/fan_profiles.json"],
        "source": source,
        "constraints": constraints,
        "profile_aliases": profile_spec["profile_aliases"],
        "profiles": profiles,
    }


def rendered_manifest() -> str:
    return json.dumps(generate(), ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = rendered_manifest()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit("profiles/profiles.json is stale; run tools/generate_manifest.py")
        print("profiles/profiles.json is up to date")
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
