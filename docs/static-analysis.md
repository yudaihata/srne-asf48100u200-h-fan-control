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
| `0x24B7A` | `7b f4` | high half of the stock 0.28 temperature-curve slope |
| `0x24B7E` | `49 f8` | `ADDF32` temperature-curve origin, −450.0 |
| `0x24B80` | `0a e8 4b e1` | `MOVXI` low half of the stock 0.28 slope |

Each reviewed profile changes between zero and nine bytes. The 35/60/32 °C and
40/65/37 °C profiles retain the stock 0.28 slope and therefore still change
only `0x24A04`, `0x24A12`, `0x24B7E`, and `0x24B7F`. The 45/70/42 °C profile
is byte-for-byte identical to stock.

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

MOVIZ/MOVXI R3H: 0.2
MOVIZ/MOVXI R3H: 0.233333334
MOVIZ/MOVXI R3H: 0.28
MOVIZ/MOVXI R3H: 0.35
MOVIZ/MOVXI R3H: 0.466666669
MOVIZ/MOVXI R3H: 0.7
```

These are the six unique binary32 slopes required by the 14 allowed
start/maximum combinations. The requested curve is normalized as:

```text
request = 30 + (temperature_deci_c - start_c * 10) * slope
slope   = 70 / ((max_c - start_c) * 10)
```

The minimum allowed start-to-maximum span is 10 °C. The excluded 45/50 °C
combination would require the separately assembled 1.4 slope but is not present
in the public manifest.

The advanced CLI can construct an unreviewed integer-C profile outside this
manifest. It encodes the two `CMP` immediates, the complete `ADDF32` curve
origin, and the `MOVIZ`/`MOVXI` binary32 slope, then verifies the candidate by
exact source diff. Independent assembly samples for −10.0, −380.0, and −500.0
are included in `analysis/verify_fan_patch.asm` to cover the custom origin
encoder across its documented range. This encoding verification does not make
a custom thermal profile reviewed or safe.

## Candidate identities

| Profile | Candidate SHA-256 |
|---|---|
| `fan35C_max60C_off32C` | `39b3c5cff7f6063e588f7e3f39ddba974e1c2a976df1a31dd239599d9ab35b1c` |
| `fan40C_max65C_off37C` | `97c527aa10bb4c1db72f1bb6d125e152b915d9f493cf9fdcf99828de85f7f2b4` |
| `fan45C_max70C_off42C` | `d4b4f4590689ae2effedf40e3999da8d4b9dfdcac7a1eff4635d0eca6d644600` (stock-equivalent) |

All 14 candidate identities and exact changed-offset sets are recorded in
[`profiles/profiles.json`](../profiles/profiles.json). Every candidate retains
the 475,136-byte size and trailer marker `23016745ab89efcddcfe98ba00000000`.

## Confidence boundary

Hashes, exact diffs, and valid C28x instruction decoding establish what bytes
changed. They do not establish vendor-updater acceptance, boot safety, runtime
safety, or compatibility with another hardware or firmware revision.
