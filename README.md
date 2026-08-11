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
off in addition to load, charge, and discharge demands. Two minimal-difference
profiles are documented:

| Profile | Start | Stop | Curve origin | Intended use |
|---|---:|---:|---:|---|
| `fan40C_off37C` | 40 °C | 37 °C | 40 °C | 5 °C below stock; increased fan runtime/noise possible |
| `fan35C_off32C` | 35 °C | 32 °C | 35 °C | Larger temperature reduction; more fan runtime/noise/wear possible |

No vendor firmware or patched firmware is distributed. The builder refuses to
operate unless the user supplies the exact known source image and all hash,
size, trailer, and original-byte checks pass.

## Browser patcher

For a guided, command-free workflow, use the
[ASF48100U200-H browser patcher](https://yudaihata.github.io/srne-asf48100u200-h-fan-control/).
The selected BIN never leaves the browser. The page validates the exact source
SHA-256, size, trailer, original instruction bytes, changed offsets, and final
candidate SHA-256 before enabling download.

## Quick start

Requires Python 3.11 or later.

```bash
python3 tools/build_candidate.py \
  --source /path/to/ASF48100SU200_V8.16.9.bin \
  --profile fan40C_off37C \
  --output /path/to/ASF48100SU200_V8.16.9_fan40C_off37C.bin

python3 tools/verify_candidate.py \
  --candidate /path/to/ASF48100SU200_V8.16.9_fan40C_off37C.bin \
  --profile fan40C_off37C \
  --source /path/to/ASF48100SU200_V8.16.9.bin
```

The expected source SHA-256 is
`d4b4f4590689ae2effedf40e3999da8d4b9dfdcac7a1eff4635d0eca6d644600`.

## Repository contents

- [`docs/static-analysis.md`](docs/static-analysis.md): recovered control path,
  offsets, instructions, and confidence boundaries.
- [`docs/porting-to-other-firmware.md`](docs/porting-to-other-firmware.md):
  evidence-gated re-analysis workflow for AI agents and human reviewers working
  on another firmware image.
- [`analysis/v8.16.9-fan-control.annotated.asm`](analysis/v8.16.9-fan-control.annotated.asm):
  minimal annotated disassembly excerpts supporting the V8.16.9 findings.
- [`docs/runtime-validation.md`](docs/runtime-validation.md): Home Assistant
  log method and the observed cooling effect of the 35/32 °C profile.
- [`docs/safety.md`](docs/safety.md): deployment risks and recovery checklist.
- [`profiles/profiles.json`](profiles/profiles.json): machine-readable source and
  profile definitions.
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
