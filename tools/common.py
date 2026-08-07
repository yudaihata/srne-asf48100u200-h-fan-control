#!/usr/bin/env python3
"""Shared guarded firmware-patching helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "profiles" / "profiles.json"


class VerificationError(ValueError):
    """Raised when an image does not match the reviewed firmware definition."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_profile(name: str, manifest: dict[str, Any]) -> dict[str, Any]:
    try:
        return manifest["profiles"][name]
    except KeyError as exc:
        choices = ", ".join(sorted(manifest["profiles"]))
        raise VerificationError(f"Unknown profile {name!r}; choose: {choices}") from exc


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
