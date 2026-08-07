from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from common import apply_profile, load_manifest, resolve_profile  # noqa: E402


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest()

    def test_manifest_is_valid_json_and_has_two_profiles(self) -> None:
        parsed = json.loads((ROOT / "profiles" / "profiles.json").read_text())
        self.assertEqual(parsed["format_version"], 1)
        self.assertEqual(
            set(parsed["profiles"]), {"fan35C_off32C", "fan40C_off37C"}
        )

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


if __name__ == "__main__":
    unittest.main()
