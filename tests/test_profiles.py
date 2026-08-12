from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from common import (  # noqa: E402
    VerificationError,
    apply_profile,
    build_custom_profile,
    load_manifest,
    materialize_custom_profile,
    resolve_profile,
)


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest()

    def test_manifest_is_valid_json_and_has_all_reviewed_profiles(self) -> None:
        parsed = json.loads((ROOT / "profiles" / "profiles.json").read_text())
        self.assertEqual(parsed["format_version"], 1)
        expected = {
            f"fan{start}C_max{maximum}C_off{start - 3}C"
            for start in (35, 40, 45)
            for maximum in (50, 55, 60, 65, 70)
            if maximum - start >= 10
        }
        self.assertEqual(set(parsed["profiles"]), expected)
        self.assertEqual(len(expected), 14)
        self.assertNotIn("fan45C_max50C_off42C", expected)

    def test_patch_definitions_change_only_declared_offsets(self) -> None:
        size = self.manifest["source"]["size"]
        for name in self.manifest["profiles"]:
            profile = resolve_profile(name, self.manifest)
            source = bytearray(size)
            for patch in profile["patches"]:
                offset = int(patch["offset"], 0)
                expected = bytes.fromhex(patch["expected_hex"])
                source[offset : offset + len(expected)] = expected
            candidate, changed = apply_profile(bytes(source), profile)
            self.assertEqual(
                changed, [int(value, 0) for value in profile["changed_offsets"]]
            )
            self.assertEqual(len(candidate), size)

    def test_hysteresis_is_three_degrees(self) -> None:
        for profile in self.manifest["profiles"].values():
            self.assertEqual(profile["start_c"] - profile["stop_c"], 3)
            self.assertEqual(profile["curve_origin_c"], profile["start_c"])

    def test_minimum_start_to_maximum_span_is_ten_degrees(self) -> None:
        minimum = self.manifest["constraints"]["minimum_span_c"]
        self.assertEqual(minimum, 10)
        for profile in self.manifest["profiles"].values():
            self.assertGreaterEqual(profile["max_c"] - profile["start_c"], minimum)

    def test_temperature_curve_reaches_100_at_fan_maximum(self) -> None:
        for profile in self.manifest["profiles"].values():
            span_deci_c = (profile["max_c"] - profile["start_c"]) * 10
            request = 30 + span_deci_c * profile["slope_f32"]
            self.assertAlmostEqual(request, 100, places=5)

    def test_legacy_profile_aliases_resolve_to_existing_candidates(self) -> None:
        self.assertIs(
            resolve_profile("fan35C_off32C", self.manifest),
            self.manifest["profiles"]["fan35C_max60C_off32C"],
        )
        self.assertIs(
            resolve_profile("fan40C_off37C", self.manifest),
            self.manifest["profiles"]["fan40C_max65C_off37C"],
        )

    def test_custom_profile_encodes_non_manifest_temperatures(self) -> None:
        profile = build_custom_profile(38, 58, 35)
        patches = {patch["offset"]: patch for patch in profile["patches"]}
        self.assertEqual(patches["0x24A04"]["replacement_hex"], "7c01")
        self.assertEqual(patches["0x24A12"]["replacement_hex"], "5e01")
        self.assertEqual(patches["0x24B7A"]["replacement_hex"], "9bf5")
        self.assertEqual(patches["0x24B7C"]["replacement_hex"], "b0e889ef")
        self.assertEqual(patches["0x24B80"]["replacement_hex"], "09e89b99")
        self.assertEqual(profile["review_status"], "unreviewed-custom")

    def test_custom_profile_materializes_with_exact_hash_and_diff(self) -> None:
        source = bytearray(self.manifest["source"]["size"])
        stock = build_custom_profile(38, 58, 35)
        for patch in stock["patches"]:
            offset = int(patch["offset"], 0)
            expected = bytes.fromhex(patch["expected_hex"])
            source[offset : offset + len(expected)] = expected
        profile, candidate, changed = materialize_custom_profile(
            bytes(source), 38, 58, 35
        )
        self.assertEqual(profile["changed_offsets"], [f"0x{x:X}" for x in changed])
        self.assertEqual(len(profile["output_sha256"]), 64)
        self.assertEqual(len(candidate), len(source))

    def test_custom_profile_rejects_invalid_ordering(self) -> None:
        with self.assertRaises(VerificationError):
            build_custom_profile(40, 40, 37)
        with self.assertRaises(VerificationError):
            build_custom_profile(40, 60, 40)

    def test_custom_origin_encoder_matches_assembled_boundaries(self) -> None:
        low = {
            patch["offset"]: patch for patch in build_custom_profile(1, 2, 0)["patches"]
        }
        high = {
            patch["offset"]: patch
            for patch in build_custom_profile(50, 100, 0)["patches"]
        }
        self.assertEqual(low["0x24B7C"]["replacement_hex"], "b0e80948")
        self.assertEqual(high["0x24B7C"]["replacement_hex"], "b0e889fe")


if __name__ == "__main__":
    unittest.main()
