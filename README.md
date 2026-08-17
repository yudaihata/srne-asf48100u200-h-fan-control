# Unofficial SRNE ASF48100U200-H Fan Control

[日本語](README.ja.md)

> [!WARNING]
> This is an independent, unofficial research project. It is not affiliated
> with, endorsed by, or supported by SRNE Solar Co., Ltd. Modified firmware can
> damage equipment and create electrical, fire, warranty, or regulatory risks.

Reverse-engineering notes and reproducible tools for the fan-control path in
the SRNE `ASF48100U200-H` / firmware image labeled
`ASF48100SU200_V8.16.9.bin`.

The stock image was found to use a temperature gate around 45 °C on / 42 °C
off in addition to load, charge, and discharge demands. Fourteen statically
reviewed combinations are available:

- fan start: 35, 40, or 45 °C;
- fan maximum: 50, 55, 60, 65, or 70 °C;
- fan stop: start minus 3 °C;
- minimum start-to-maximum span: 10 °C.

"Fan maximum" is the temperature at which the temperature-derived fan request
reaches approximately 100%. It is not an over-temperature protection setting.
The stock-equivalent combination is 45/70/42 °C. Lower settings can increase
fan runtime, noise, dust intake, and wear.

No vendor firmware or patched firmware is distributed. The builder refuses to
operate unless the user supplies the exact known source image and all hash,
size, trailer, and original-byte checks pass.

## Quick start

For normal use, open the
[ASF48100U200-H browser patcher](https://yudaihata.github.io/srne-asf48100u200-h-fan-control/).
The selected BIN never leaves the browser. The page validates the exact source
SHA-256, size, trailer, original instruction bytes, changed offsets, and final
candidate SHA-256 before enabling download.

The V8.16.9 requirement identifies the pristine source BIN selected for
patching; it does not describe the firmware version currently installed on the
inverter.

## Manual CLI and reproducibility

The CLI is intended for offline use, automation, independent reproduction, and
advanced custom analysis. It requires Python 3.11 or later.

### Reviewed profile

Generate one of the same statically reviewed candidates exposed by the browser.
The builder also writes a provenance JSON sidecar containing source and
candidate hashes, changed offsets, repository identity, and evidence level:

```bash
python3 tools/build_candidate.py \
  --source /path/to/ASF48100SU200_V8.16.9.bin \
  --profile fan40C_max65C_off37C \
  --output /path/to/ASF48100SU200_V8.16.9_fan40C_max65C_off37C.bin
```

To independently reproduce and verify the candidate hash and exact source
diff:

```bash
python3 tools/verify_candidate.py \
  --candidate /path/to/ASF48100SU200_V8.16.9_fan40C_max65C_off37C.bin \
  --profile fan40C_max65C_off37C \
  --source /path/to/ASF48100SU200_V8.16.9.bin
```

The former names `fan35C_off32C` and `fan40C_off37C` remain accepted as aliases
for the unchanged 35/60/32 °C and 40/65/37 °C candidates.

### Advanced custom temperatures

Advanced users can specify integer-C temperatures outside the browser's
reviewed 14-combination allowlist. Stop defaults to start minus 3 °C when
omitted:

```bash
python3 tools/build_candidate.py \
  --source /path/to/ASF48100SU200_V8.16.9.bin \
  --start-c 38 --max-c 58 --stop-c 35 \
  --acknowledge-unreviewed \
  --output /path/to/ASF48100SU200_V8.16.9_custom_38_58_35.bin

python3 tools/verify_candidate.py \
  --candidate /path/to/ASF48100SU200_V8.16.9_custom_38_58_35.bin \
  --source /path/to/ASF48100SU200_V8.16.9.bin \
  --start-c 38 --max-c 58 --stop-c 35 \
  --acknowledge-unreviewed
```

Custom mode requires `1 <= start <= 50 °C`, `start < max <= 100 °C`, and
`0 <= stop < start °C`. The start limit keeps every integer-C curve origin
exactly representable by the C28x immediate encoding. Custom mode enforces the
same 10 °C minimum span as the browser. These candidates have no
pre-reviewed output hash or runtime
validation; the tools instead derive the C28x instructions, report the exact
changed bytes and candidate hash, and require the same settings plus pristine
source for verification. The acknowledgement flag prevents accidental use of
this advanced path.

The expected source SHA-256 is
`d4b4f4590689ae2effedf40e3999da8d4b9dfdcac7a1eff4635d0eca6d644600`.

## Repository contents

- [`docs/static-analysis.md`](docs/static-analysis.md): recovered control path,
  offsets, instructions, and confidence boundaries.
- [`docs/porting-to-other-firmware.md`](docs/porting-to-other-firmware.md):
  human-readable evidence-gated method for analyzing another firmware image.
- [`docs/examples/v8.16.9-porting-record.yaml`](docs/examples/v8.16.9-porting-record.yaml):
  completed evidence record for the analyzed V8.16.9 image.
- [`analysis/v8.16.9-fan-control.annotated.asm`](analysis/v8.16.9-fan-control.annotated.asm):
  minimal annotated disassembly excerpts supporting the V8.16.9 findings.
- [`docs/runtime-validation.md`](docs/runtime-validation.md): Home Assistant
  log method and the observed cooling effect of the 35/32 °C profile.
- [`docs/safety.md`](docs/safety.md): deployment risks and recovery checklist.
- [`profiles/profiles.json`](profiles/profiles.json): machine-readable source and
  profile definitions.
- [`spec/`](spec/): concise canonical inputs used to generate the manifest.
- [`docs/evidence-levels.md`](docs/evidence-levels.md): precise separation of
  static identity and runtime observations.
- [`docs/release-process.md`](docs/release-process.md): reproducible publication gate.
- [`tools/build_candidate.py`](tools/build_candidate.py): guarded candidate
  builder.
- [`tools/verify_candidate.py`](tools/verify_candidate.py): independent image
  and exact-diff verifier.
- [`tools/analyze_history.py`](tools/analyze_history.py): repeatable comparison
  of two Home Assistant history CSV exports.
- [`analysis/verify_fan_patch.asm`](analysis/verify_fan_patch.asm): minimal TI
  assembler input used to verify C28x instruction encodings.

## Important boundary

This is independent research, not vendor documentation. Static disassembly and
hash verification do not prove updater compatibility, safe boot, electrical
safety, thermal safety, or suitability for a particular hardware revision.
Firmware installation can brick the inverter and may create fire, shock,
warranty, regulatory, or equipment risks. See [`docs/safety.md`](docs/safety.md).

## License

Tools and original documentation in this repository are MIT licensed. SRNE
firmware, product names, trademarks, and derivative firmware images are not
licensed by this repository and remain the property of their respective owner.
See [`NOTICE.md`](NOTICE.md).
