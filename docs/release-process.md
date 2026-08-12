# Release process

Releases are immutable evidence checkpoints; GitHub Pages remains the convenient
delivery UI. A release must not contain a vendor or modified firmware image.

## Required checks

1. Start from a clean branch based on protected `main`.
2. Run `python3 tools/generate_manifest.py --check`.
3. Run the Python and Node test suites.
4. With the pristine local source, run:

   ```bash
   python3 tools/release_validate.py \
     --source /path/to/ASF48100SU200_V8.16.9.bin \
     --output release-validation.json
   ```

5. Confirm that the report contains exactly 14 profiles and that every candidate
   hash matches `spec/fan_profiles.json`.
6. Review `git diff --check`, the exact changed files, and the Pages preview.
7. Merge only after required checks pass.
8. Create a signed tag and GitHub release containing source code, release notes,
   `release-validation.json`, and no BIN files.

## Change classification

- Documentation-only: no manifest regeneration required unless generated tables change.
- UI-only: synthetic browser tests and Pages preview required.
- Profile/spec/encoder change: independent C28x encoding evidence, regenerated
  manifest, pristine-source validation, and a new release required.
- New firmware or hardware revision: a fresh analysis and evidence record is
  required; do not reuse V8.16.9 offsets.
