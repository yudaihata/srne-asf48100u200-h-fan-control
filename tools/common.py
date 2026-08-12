#!/usr/bin/env python3
"""Shared guarded firmware-patching helpers."""

from __future__ import annotations

import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "profiles" / "profiles.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EVIDENCE_VALUES = {
    "static_encoding": {"confirmed-static"},
    "candidate_identity": {"confirmed-static", "stock-equivalent"},
    "runtime": {"runtime-observed", "not-established"},
}


class VerificationError(ValueError):
    """Raised when an image does not match the reviewed firmware definition."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    return manifest


def _require_sha256(value: object, label: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise VerificationError(f"Invalid SHA-256 for {label}")


def validate_manifest(manifest: dict[str, Any]) -> None:
    """Validate all safety-relevant manifest structure and patch invariants."""
    if manifest.get("format_version") != 2:
        raise VerificationError("Unsupported manifest format_version")
    source = manifest.get("source")
    constraints = manifest.get("constraints")
    profiles = manifest.get("profiles")
    if not isinstance(source, dict) or not isinstance(constraints, dict) or not isinstance(profiles, dict):
        raise VerificationError("Manifest is missing source, constraints, or profiles")
    _require_sha256(source.get("sha256"), "source")
    if not isinstance(source.get("size"), int) or source["size"] <= 0:
        raise VerificationError("Invalid source size")
    try:
        trailer = bytes.fromhex(source["trailer_hex"])
    except (KeyError, TypeError, ValueError) as exc:
        raise VerificationError("Invalid source trailer") from exc
    if not trailer or len(trailer) > source["size"]:
        raise VerificationError("Invalid source trailer length")

    expected_names = {
        f"fan{start}C_max{maximum}C_off{start - constraints['stop_delta_c']}C"
        for start in constraints["allowed_start_c"]
        for maximum in constraints["allowed_max_c"]
        if maximum - start >= constraints["minimum_span_c"]
    }
    if set(profiles) != expected_names:
        raise VerificationError("Reviewed profile set does not match constraints")

    for name, profile in profiles.items():
        _require_sha256(profile.get("output_sha256"), name)
        if profile.get("stop_c") != profile.get("start_c") - constraints["stop_delta_c"]:
            raise VerificationError(f"Invalid hysteresis for {name}")
        if profile.get("max_c") - profile.get("start_c") < constraints["minimum_span_c"]:
            raise VerificationError(f"Invalid temperature span for {name}")
        evidence = profile.get("evidence")
        if not isinstance(evidence, dict):
            raise VerificationError(f"Missing evidence metadata for {name}")
        for key, allowed in EVIDENCE_VALUES.items():
            if evidence.get(key) not in allowed:
                raise VerificationError(f"Invalid {key} evidence for {name}")
        if evidence["runtime"] == "runtime-observed" and not evidence.get("runtime_document"):
            raise VerificationError(f"Missing runtime evidence document for {name}")

        covered: set[int] = set()
        computed_changed: list[int] = []
        for patch in profile.get("patches", []):
            try:
                offset = int(patch["offset"], 0)
                expected = bytes.fromhex(patch["expected_hex"])
                replacement = bytes.fromhex(patch["replacement_hex"])
            except (KeyError, TypeError, ValueError) as exc:
                raise VerificationError(f"Invalid patch encoding in {name}") from exc
            if not expected or len(expected) != len(replacement):
                raise VerificationError(f"Patch length mismatch in {name} at {offset:#x}")
            if offset < 0 or offset + len(expected) > source["size"]:
                raise VerificationError(f"Patch outside source in {name} at {offset:#x}")
            positions = set(range(offset, offset + len(expected)))
            if covered & positions:
                raise VerificationError(f"Overlapping patches in {name} at {offset:#x}")
            covered |= positions
            computed_changed.extend(
                offset + index
                for index, (before, after) in enumerate(zip(expected, replacement))
                if before != after
            )
        declared = [int(value, 0) for value in profile.get("changed_offsets", [])]
        if declared != sorted(computed_changed):
            raise VerificationError(f"Invalid changed_offsets for {name}")

    aliases = manifest.get("profile_aliases", {})
    if not isinstance(aliases, dict) or any(target not in profiles for target in aliases.values()):
        raise VerificationError("Invalid profile aliases")


def resolve_profile(name: str, manifest: dict[str, Any]) -> dict[str, Any]:
    name = manifest.get("profile_aliases", {}).get(name, name)
    try:
        return manifest["profiles"][name]
    except KeyError as exc:
        choices = ", ".join(sorted(manifest["profiles"]))
        raise VerificationError(f"Unknown profile {name!r}; choose: {choices}") from exc


def _word_bytes(value: int) -> str:
    return struct.pack("<H", value).hex()


def _float32_bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def _encode_addf32_r1h_immediate(value: float) -> str:
    bits = _float32_bits(value)
    if bits & 0xFFFF:
        raise VerificationError(
            f"ADDF32 immediate {value} is not exactly representable by this encoding"
        )
    immediate = bits >> 16
    first_word = 0xE880 | ((immediate >> 10) & 0x3F)
    second_word = ((immediate & 0x03FF) << 6) | 0x0009
    return _word_bytes(first_word) + _word_bytes(second_word)


def _encode_moviz_r3_high(immediate: int) -> str:
    return _word_bytes(((immediate & 0xFFFF) << 3 & 0xFFFF) | 0x0003)


def _encode_movxi_r3h_low(immediate: int) -> str:
    first_word = 0xE808 | ((immediate >> 13) & 0x0007)
    second_word = ((immediate & 0x1FFF) << 3) | 0x0003
    return _word_bytes(first_word) + _word_bytes(second_word)


def build_custom_profile(start_c: int, max_c: int, stop_c: int) -> dict[str, Any]:
    """Build an unreviewed integer-C profile for advanced CLI use."""
    if not 1 <= start_c <= 50 or not start_c < max_c <= 100:
        raise VerificationError(
            "Custom temperatures must satisfy 1 <= start <= 50 C and start < max <= 100 C"
        )
    if not 0 <= stop_c < start_c:
        raise VerificationError("Custom stop temperature must satisfy 0 <= stop < start C")
    if max_c - start_c < 10:
        raise VerificationError("Custom start-to-maximum span must be at least 10 C")

    start_deci_c = start_c * 10
    stop_deci_c = stop_c * 10
    slope = struct.unpack(
        "<f", struct.pack("<f", 70.0 / ((max_c - start_c) * 10))
    )[0]
    slope_bits = _float32_bits(slope)
    slope_high = slope_bits >> 16
    slope_low = slope_bits & 0xFFFF

    return {
        "start_c": start_c,
        "max_c": max_c,
        "stop_c": stop_c,
        "curve_origin_c": start_c,
        "slope_f32": slope,
        "review_status": "unreviewed-custom",
        "patches": [
            {
                "offset": "0x24A04",
                "expected_hex": "c201",
                "replacement_hex": _word_bytes(start_deci_c),
                "meaning": f"CMP AR6: 450 to {start_deci_c} deci-C",
            },
            {
                "offset": "0x24A12",
                "expected_hex": "a401",
                "replacement_hex": _word_bytes(stop_deci_c),
                "meaning": f"CMP AR6: 420 to {stop_deci_c} deci-C",
            },
            {
                "offset": "0x24B7A",
                "expected_hex": "7bf4",
                "replacement_hex": _encode_moviz_r3_high(slope_high),
                "meaning": f"MOVIZ curve slope high half for {slope}",
            },
            {
                "offset": "0x24B7C",
                "expected_hex": "b0e849f8",
                "replacement_hex": _encode_addf32_r1h_immediate(-float(start_deci_c)),
                "meaning": f"ADDF32 curve origin: -450.0 to -{start_deci_c}.0 deci-C",
            },
            {
                "offset": "0x24B80",
                "expected_hex": "0ae84be1",
                "replacement_hex": _encode_movxi_r3h_low(slope_low),
                "meaning": f"MOVXI curve slope low half for {slope}",
            },
        ],
    }


def materialize_custom_profile(
    source: bytes, start_c: int, max_c: int, stop_c: int
) -> tuple[dict[str, Any], bytes, list[int]]:
    profile = build_custom_profile(start_c, max_c, stop_c)
    candidate, changed = apply_profile(source, profile)
    profile["changed_offsets"] = [f"0x{offset:X}" for offset in changed]
    profile["output_sha256"] = sha256(candidate)
    return profile, candidate, changed


def validate_source(data: bytes, manifest: dict[str, Any]) -> None:
    spec = manifest["source"]
    actual_hash = sha256(data)
    if actual_hash != spec["sha256"]:
        raise VerificationError(
            f"Unexpected source SHA-256: {actual_hash} != {spec['sha256']}"
        )
    if len(data) != spec["size"]:
        raise VerificationError(
            f"Unexpected source size: {len(data)} != {spec['size']}"
        )
    trailer = bytes.fromhex(spec["trailer_hex"])
    if not data.endswith(trailer):
        raise VerificationError("Unexpected firmware trailer")


def apply_profile(
    source: bytes, profile: dict[str, Any]
) -> tuple[bytes, list[int]]:
    candidate = bytearray(source)
    for patch in profile["patches"]:
        offset = int(patch["offset"], 0)
        expected = bytes.fromhex(patch["expected_hex"])
        replacement = bytes.fromhex(patch["replacement_hex"])
        actual = bytes(candidate[offset : offset + len(expected)])
        if actual != expected:
            raise VerificationError(
                f"Unexpected bytes at {offset:#x}: {actual.hex()} != {expected.hex()}"
            )
        if len(expected) != len(replacement):
            raise VerificationError(f"Patch length mismatch at {offset:#x}")
        candidate[offset : offset + len(expected)] = replacement
    result = bytes(candidate)
    changed = [i for i, pair in enumerate(zip(source, result)) if pair[0] != pair[1]]
    return result, changed


def validate_candidate(
    candidate: bytes,
    profile: dict[str, Any],
    manifest: dict[str, Any],
    source: bytes | None = None,
) -> list[int] | None:
    spec = manifest["source"]
    if len(candidate) != spec["size"]:
        raise VerificationError(
            f"Unexpected candidate size: {len(candidate)} != {spec['size']}"
        )
    trailer = bytes.fromhex(spec["trailer_hex"])
    if not candidate.endswith(trailer):
        raise VerificationError("Unexpected candidate trailer")
    actual_hash = sha256(candidate)
    if actual_hash != profile["output_sha256"]:
        raise VerificationError(
            f"Unexpected candidate SHA-256: {actual_hash} != "
            f"{profile['output_sha256']}"
        )
    if source is None:
        return None
    validate_source(source, manifest)
    expected_candidate, expected_changed = apply_profile(source, profile)
    if candidate != expected_candidate:
        raise VerificationError("Candidate bytes differ from the reviewed profile")
    declared = [int(value, 0) for value in profile["changed_offsets"]]
    if expected_changed != declared:
        raise VerificationError(
            f"Changed offsets {expected_changed} do not match manifest {declared}"
        )
    return expected_changed
