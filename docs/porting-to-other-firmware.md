# Analyzing and porting fan control to other firmware

This document is a re-analysis guide for another firmware image or a related
SRNE product. It is written primarily as an execution contract for an AI agent,
but every required decision and artifact is also intended to be reviewable by a
human.

"Porting" does **not** mean copying the V8.16.9 offsets or byte patterns. The
target firmware must be analyzed independently. A structural or constant match
is only a lead until control flow, data flow, peripheral use, and original bytes
all agree.

The V8.16.9 reference excerpts are in
[`analysis/v8.16.9-fan-control.annotated.asm`](../analysis/v8.16.9-fan-control.annotated.asm).

## Agent contract

An agent following this guide MUST:

1. keep the source image immutable and identify it by model, firmware label,
   byte size, and SHA-256;
2. determine the target architecture, image layout, address unit, endianness,
   and load mapping instead of inheriting them from V8.16.9;
3. recover the fan output, temperature input, demand arbitration, persistence,
   smoothing, and lock/fault paths as one control system;
4. label every conclusion as confirmed, strongly supported, hypothesis, or
   runtime-observed;
5. stop before creating a candidate if any mandatory evidence gate below is
   unmet;
6. propose the smallest semantic change and preserve unrelated protection,
   fault, inverter, charging, and MPPT paths;
7. validate original bytes, exact changed offsets, output size, trailer or
   checksum, and output SHA-256;
8. treat candidate generation and physical-device installation as separate
   approvals.

An agent MUST NOT:

- reuse `0x24A04`, `0x24A12`, `0x24B7E`, or any other V8.16.9 offset in a
  different image without fresh instruction-boundary and data-flow proof;
- patch the first occurrence of `450`, `420`, `3333`, `30.0`, or a similar
  constant;
- treat a signature scan, binary similarity score, valid disassembly, or clean
  checksum as evidence of hardware compatibility;
- publish or redistribute a vendor BIN or a large contiguous disassembly;
- claim updater acceptance, safe boot, or runtime safety from static analysis.

## Required input record

Create this record before analyzing code. Use `unknown`, not a guess.

```yaml
target:
  manufacturer: SRNE
  product_model: unknown
  hardware_revision: unknown
  firmware_label: unknown
  source_filename: unknown
  source_origin: unknown
  byte_size: unknown
  sha256: unknown
  trailer_or_container: unknown
analysis:
  architecture: unknown
  endianness: unknown
  address_unit_bytes: unknown
  load_base: unknown
  disassembler: unknown
  disassembler_version: unknown
runtime_context:
  fan_model: unknown
  fan_wiring: unknown
  observed_stock_behavior: unknown
  temperature_telemetry_source: unknown
  recovery_method: unknown
```

Record a second hash after every extraction or container-decoding step. Never
silently replace the source path with a decoded or patched image.

## Evidence vocabulary

Use these terms consistently in notes and reports:

| Label | Meaning |
|---|---|
| `confirmed-static` | Exact instruction/data flow was reproduced from the identified image, normally with an independent assembler check where encoding matters. |
| `strongly-supported` | Multiple independent static anchors agree, but a symbol, variable meaning, or timing source is inferred. |
| `runtime-observed` | Behavior was observed on an identified device and firmware, with the observation method recorded. |
| `hypothesis` | Plausible lead that must not be used as a patch target. |
| `not-established` | Evidence is absent or contradictory. |

Do not collapse static and runtime evidence into a single "verified" label.

## V8.16.9 reference facts

These facts are reference anchors, not portable constants.

| Property | V8.16.9 reference |
|---|---|
| Source label | `ASF48100SU200_V8.16.9.bin` |
| Size | 475,136 bytes |
| SHA-256 | `d4b4f4590689ae2effedf40e3999da8d4b9dfdcac7a1eff4635d0eca6d644600` |
| Trailer | `23016745ab89efcddcfe98ba00000000` |
| Architecture | TI TMS320C28x/C2000, little-endian 16-bit words |
| Raw-image mapping | file offset 0 maps to C28x word address `0x84000` |
| Fan routine | word addresses `0x964B4` through `0x966B6` |
| Fan-routine call site | `LCR 0x0964B4` at `0x9C515` |
| Fan PWM | continuous ePWM4B, period 3333 counts |
| Temperature gate | approximately 45.0 C start / 42.0 C stop |
| Persistence | 20 start cycles / 100 stop cycles; approximately 2 s / 10 s at the recovered 100 ms cadence |
| Temperature demand | approximately `(temperature_deci_c - 450) * 0.28 + 30` |
| Arbitration | maximum of temperature, load, charge, and discharge-related demands |
| Smoothing | `state += (target - state) / 32` in fixed-point form |
| Lock input | GPIO67, active-low lock indication, no pulse-count speed measurement |
| Lock persistence | 50 low/high cycles; approximately 5 s at the recovered cadence |

The V8.16.9 threshold instructions begin at word addresses `0x96501` and
`0x96508`. The bytes changed by the current profiles are in continuation words,
which is why file offsets `0x24A04` and `0x24A12` do not point to the first word
of each instruction.

## Workflow

### 1. Preserve and identify the source

1. Work from a copy while retaining a read-only pristine image.
2. Calculate SHA-256 and byte size.
3. Save the final 16 to 64 bytes and determine whether they are a marker,
   checksum, signature, padding, or unknown data.
4. Search for model/version strings, but treat filenames and strings only as
   labels.
5. If two vendor images are available, diff them to identify stable regions,
   relocated blocks, headers, and update metadata. A nearby version is useful
   corroboration, not a patch template.

### 2. Establish the executable mapping

Do not start with a fan signature. First establish how bytes become
instructions.

For a suspected C28x raw image:

- test little-endian 16-bit word decoding;
- distinguish byte offsets from C28x word addresses;
- test candidate load bases against reset/entry vectors, long-call targets,
  branch destinations, peripheral access, and sustained valid control flow;
- require many coherent functions, not one plausible instruction sequence.

For V8.16.9 the mapping is:

```text
word_address = 0x84000 + file_offset / 2
file_offset  = (word_address - 0x84000) * 2
```

This equation is invalid for another image until independently established.

One reproducible C28x technique is to convert every little-endian 16-bit word
to a `.word` in a temporary `.firmware` section, assemble it, link that section
at the candidate base, and run TI `dis2000 --all --hex --data_as_text`. Record
the TI C2000 Code Generation Tools version. V8.16.9 was analyzed with 25.11.1
LTS.

### 3. Find the fan output from hardware-facing anchors

Prefer peripheral and data-flow anchors over temperature constants.

1. Identify PWM peripheral initialization and period writes.
2. Trace every runtime write to the corresponding compare/duty register.
3. Work backward from the compare write to clamps, scaling, smoothing, and
   demand selection.
4. Confirm whether the output is continuous PWM, discrete voltage selection,
   GPIO on/off control, or another method.
5. Identify all channels and confirm which channel reaches the physical fan.

In V8.16.9, the period value `0x0D05` (3333) and the runtime write through
base `0x4300`, offset `0x6D`, jointly identify ePWM4B. Either anchor by itself
would be insufficient.

### 4. Recover all demand sources

Trace the value feeding PWM backward. Name variables by role only after their
use supports the name.

For each candidate demand, record:

- raw source location and producing function;
- unit and scaling evidence;
- minimum/maximum clamps;
- enable or mode gates;
- relationship to the final maximum or selector;
- whether the value is temperature, load, charge current, discharge current,
  or still unknown.

V8.16.9 computes four requests, selects the largest, and smooths it by 1/32.
Changing only a load-derived path would therefore not create reliable thermal
control, and changing only a temperature threshold without its curve origin
would shift the on/off gate but leave a mismatched duty curve.

### 5. Prove the temperature unit and hysteresis state machine

A threshold is not a temperature threshold merely because it resembles one.
Require at least three of these independent anchors:

- cross-reference to the value exported as internal/heatsink temperature;
- consistent conversion or scaling into deci-degrees C;
- paired thresholds forming plausible hysteresis;
- persistence counters tied to an on/off state bit;
- a temperature-dependent duty curve using the same value;
- runtime correlation between telemetry and fan behavior.

Recover both branches and their state transitions. For V8.16.9:

```text
inactive and temperature >= 450 for 20 cycles:
    temperature_gate_active = true
    persistence_counter = 100

active and temperature <= 420:
    decrement persistence_counter
    when it expires:
        temperature_gate_active = false
        filtered_request = 0
```

This is simplified pseudocode. Other mode/override conditions in the routine
must still be traced before editing another firmware.

### 6. Recover fan-lock or tachometer handling

Trace the physical status input independently of the PWM output. Determine
whether firmware measures pulse frequency, reads a static lock signal, or does
not monitor the fan.

V8.16.9 tests one GPIO bit and uses 50-cycle persistence. There is no
edge-counting, timer capture, or RPM calculation in the recovered path. The
physical fan's third wire and runtime behavior support interpreting GPIO67 as
an active-low lock signal. Monitoring is gated off while the fan is stopped.

Preserve this path unless the requested change explicitly concerns fan-fault
handling and has separate evidence.

### 7. Cross-version matching

Build an evidence table before declaring a matching function:

| Anchor | Target evidence | Status |
|---|---|---|
| PWM peripheral and channel | address/register flow | unknown |
| PWM period and duty write | initialization plus runtime writer | unknown |
| Temperature source and unit | producer, scaling, telemetry cross-reference | unknown |
| Start/stop hysteresis | paired compares plus state transitions | unknown |
| Persistence | counter initialization and terminal tests | unknown |
| Temperature curve | conversion, origin, slope, offset, clamps | unknown |
| Other demand sources | inputs and final arbitration | unknown |
| Smoothing | accumulator data flow | unknown |
| Lock input and fault path | GPIO/timer input through error state | unknown |

All rows must be at least `strongly-supported`; the proposed patch
instructions and original bytes must be `confirmed-static`.

Binary similarity or a structural scan may prioritize a region for review, but
must never satisfy a row by itself. If a related product rearranges or replaces
the control structure, continue manual data-flow analysis instead of forcing a
V8.16.9-shaped match.

### 8. Design the smallest candidate

Before modifying bytes, write a patch plan containing:

- source identity;
- requested behavior;
- instruction addresses and file offsets;
- full original instructions and bytes;
- replacement instructions and expected bytes;
- reason every changed instruction is necessary;
- nearby paths explicitly left unchanged;
- expected changed-byte set;
- unresolved assumptions.

If lowering the V8.16.9-style temperature gate, update the temperature-curve
origin consistently. Preserve PWM setup, lower-duty behavior, arbitration,
smoothing, lock detection, fault handling, and unrelated power-control logic.

Use an independent assembler to verify replacement instruction encodings. Do
not derive a multiword C28x floating-point immediate by treating its displayed
words as a normal IEEE-754 byte string; reassemble the complete instruction.

### 9. Validate the candidate as an artifact

The builder and an independent verifier should both enforce:

- exact pristine source SHA-256;
- exact source size;
- expected trailer/container metadata;
- expected original bytes at every patch location;
- failure if any expected location is absent or duplicated;
- exact changed-byte set, not only a changed range;
- unchanged output size and required trailer/checksum;
- expected output SHA-256;
- successful disassembly of each replacement instruction.

For multiword C28x instructions, count actual changed bytes. In the V8.16.9
profiles, the upper byte of one continuation word is unchanged, so the exact
changed-byte set is:

```text
0x24A04, 0x24A12, 0x24B7E, 0x24B7F
```

Do not incorrectly include `0x24A05` merely because it belongs to the patched
instruction word.

### 10. Separate static completion from runtime validation

Static completion establishes only that the intended image was changed in the
intended way. It does not establish that the vendor updater accepts the image,
that the device boots, or that the thermal result is safe.

A runtime plan should separately identify:

- exact test device and hardware revision;
- recovery and power-bypass arrangements;
- stock and candidate firmware identities;
- internal temperature, load, charge/discharge, fan status, and alarm logs;
- ambient or room-temperature context where available;
- rollback thresholds and an observer able to disconnect power safely.

Do not perform a physical write without explicit approval for that exact
device and candidate.

## Mandatory stop conditions

Stop without producing a candidate if any of the following is true:

- architecture, endianness, address unit, or load mapping is unresolved;
- only constants or byte signatures match;
- the temperature unit is inferred from magnitude alone;
- the fan PWM channel or physical output cannot be established;
- start, stop, curve origin, arbitration, or fault handling cannot be separated;
- a proposed edit crosses an uncertain instruction boundary;
- source hash, size, original bytes, trailer, or checksum behavior is unknown;
- more bytes change than the reviewed patch plan predicts;
- the target uses a materially different control structure;
- available evidence contradicts the proposed interpretation.

Report the blocked evidence gate and the next read-only experiment instead of
guessing.

## Required agent handoff

An agent's final analysis report should contain:

```yaml
result: matched | not_matched | blocked
source:
  model: ...
  firmware_label: ...
  size: ...
  sha256: ...
mapping:
  architecture: ...
  endianness: ...
  address_unit_bytes: ...
  load_base: ...
fan_control:
  pwm_channel: ...
  pwm_period: ...
  temperature_unit: ...
  start_threshold: ...
  stop_threshold: ...
  persistence: ...
  demand_sources: ...
  smoothing: ...
  lock_input: ...
evidence:
  confirmed_static: []
  strongly_supported: []
  hypotheses: []
  runtime_observed: []
patch_plan:
  authorized: false
  changes: []
  exact_changed_offsets: []
unresolved: []
```

Attach concise annotated excerpts, hashes, tool versions, and commands needed
to reproduce the conclusions. Do not attach the source firmware or a full
vendor disassembly.

## Common failure modes

- **Byte/word confusion:** C28x addresses words while ordinary file tools
  report bytes.
- **Continuation-word confusion:** a patch offset may land in the second word
  of a multiword instruction.
- **False constant match:** temperatures such as 420 or 450 can appear in
  unrelated protection and calibration code.
- **Immediate-decoding error:** C28x extended floating-point instruction words
  cannot always be read as a contiguous IEEE-754 literal.
- **Demand-source omission:** the fan may respond to load or current even when
  the temperature gate is inactive.
- **Fault-path damage:** changing fan enable behavior can unintentionally alter
  lock monitoring or error recovery.
- **Timing overclaim:** counter values become seconds only after the call cadence
  is established.
- **Hardware-revision overclaim:** the same firmware label does not prove the
  same fan, sensor placement, power stage, or control board.
- **Static-success overclaim:** correct hashes and instructions do not prove a
  safe device update.

## Publication boundary

Publish original documentation, pseudocode, hashes, tools, and only the short
instruction excerpts necessary to support conclusions. Do not publish source
or modified vendor BINs, full disassemblies, or unrelated proprietary code.
The repository MIT License applies only to original project material; see
[`NOTICE.md`](../NOTICE.md).
