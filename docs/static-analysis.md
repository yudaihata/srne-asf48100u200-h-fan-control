# Static-analysis findings

## Scope and identification

The reviewed image is `ASF48100SU200_V8.16.9.bin`, 475,136 bytes, SHA-256:

```text
d4b4f4590689ae2effedf40e3999da8d4b9dfdcac7a1eff4635d0eca6d644600
```

It was identified as a raw TI TMS320C28x/C2000 DSP image. C28x word address
`0x84000` maps to file offset zero for this image.

These findings apply only to that exact image. A second image labeled version
8.16 has SHA-256
`43b1debe1135216a35841a3936d69223f9c893e731b71d0804a39b3104398d25`;
the offsets in this repository must not be applied to it without a fresh
analysis.

## Recovered fan path

Static analysis recovered the following behavior:

- ePWM4B continuously generates fan PWM with period 3333 counts.
- Stock temperature gate is approximately 45 °C on and 42 °C off.
- Start and stop persistence are approximately 2 seconds and 10 seconds.
- Minimum commanded duty is approximately 30%.
- Temperature demand is arbitrated with load, charge, and discharge demand.
- The command passes through smoothing before PWM output.
- GPIO67 is used as an active-low fan-lock input, with roughly 5-second
  fault/recovery persistence.

The profile changes intentionally leave PWM generation, minimum duty, demand
arbitration, smoothing, GPIO67 lock detection, fan-error handling, inverter
control, and MPPT logic untouched.

## Minimal patch locations

| File offset | Stock bytes | Meaning |
|---:|---:|---|
| `0x24A04` | `c2 01` | `CMP AR6,#450`, start threshold in deci-°C |
| `0x24A12` | `a4 01` | `CMP AR6,#420`, stop threshold in deci-°C |
| `0x24B7E` | `49 f8` | `ADDF32` temperature-curve origin, −450.0 |

For both documented profiles, only four bytes differ from stock:
`0x24A04`, `0x24A12`, `0x24B7E`, and `0x24B7F`.

## Instruction-encoding verification

Replacement encodings were independently assembled with TI C2000 CGT 25.11.1
using:

```bash
cl2000 -v28 -ml -mt --float_support=fpu32 \
  --asm_listing analysis/verify_fan_patch.asm
dis2000 verify_fan_patch.obj
```

The decoded instructions were:

```text
CMP AR6,#350
CMP AR6,#320
ADDF32 R1H,#-350.0,R1H

CMP AR6,#400
CMP AR6,#370
ADDF32 R1H,#-400.0,R1H
```

## Candidate identities

| Profile | Candidate SHA-256 |
|---|---|
| `fan35C_off32C` | `39b3c5cff7f6063e588f7e3f39ddba974e1c2a976df1a31dd239599d9ab35b1c` |
| `fan40C_off37C` | `97c527aa10bb4c1db72f1bb6d125e152b915d9f493cf9fdcf99828de85f7f2b4` |

Both candidates retain the 475,136-byte size and trailer marker
`23016745ab89efcddcfe98ba00000000`.

## Confidence boundary

Hashes, exact diffs, and valid C28x instruction decoding establish what bytes
changed. They do not establish vendor-updater acceptance, boot safety, runtime
safety, or compatibility with another hardware or firmware revision.
