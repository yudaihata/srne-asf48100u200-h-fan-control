# Analyzing and porting fan control to other firmware

This guide explains how to investigate fan control in another firmware image or
a related SRNE product. It is intended for engineers and reviewers performing a
fresh analysis, not as a recipe for copying the V8.16.9 patch.

The central rule is simple: **an offset is not portable evidence**. A matching
temperature constant or byte sequence is only a lead until instruction
boundaries, control flow, data flow, peripheral use, and original bytes all
agree.

An optional record template is available at
[`docs/templates/porting-record.yaml`](templates/porting-record.yaml). It can be
used to keep source details, evidence, open questions, and validation results
together during an investigation. The completed
[`V8.16.9 example`](examples/v8.16.9-porting-record.yaml) shows how known,
inferred, and unrecorded details are kept separate.

The concise V8.16.9 disassembly evidence is in
[`analysis/v8.16.9-fan-control.annotated.asm`](../analysis/v8.16.9-fan-control.annotated.asm).

## What a successful analysis establishes

A useful result identifies the complete fan-control path rather than one
plausible threshold. At minimum, it should explain:

- which peripheral and channel drive the physical fan;
- where the temperature value originates and how it is scaled;
- how start and stop hysteresis are implemented;
- how long each condition must persist;
- how temperature becomes a requested duty or speed;
- which load, charge, or discharge demands compete with temperature demand;
- how the final command is limited and smoothed;
- how fan-lock or tachometer input reaches fault handling.

Only after those pieces agree should patch locations be considered.

## Evidence and confidence

Use consistent language so that static conclusions are not confused with device
observations.

| Label | Meaning |
|---|---|
| `confirmed-static` | Exact instruction and data flow were reproduced from an identified image, with independent encoding checks where needed. |
| `strongly-supported` | Several independent static anchors agree, but a symbol, unit, variable role, or timing source remains inferred. |
| `runtime-observed` | Behavior was observed on an identified device and firmware, with the method and conditions recorded. |
| `hypothesis` | A plausible lead that is not suitable as a patch target. |
| `not-established` | Evidence is missing or contradictory. |

Static completion establishes that an intended image was changed in an intended
way. It does not establish updater acceptance, safe boot, thermal safety, or
compatibility with another hardware revision.

## V8.16.9 as a reference example

The following values describe the reviewed image. They are useful anchors for
understanding the method, but they are not portable constants.

| Property | V8.16.9 reference |
|---|---|
| Source label | `ASF48100SU200_V8.16.9.bin` |
| Size | 475,136 bytes |
| SHA-256 | `d4b4f4590689ae2effedf40e3999da8d4b9dfdcac7a1eff4635d0eca6d644600` |
| Trailer | `23016745ab89efcddcfe98ba00000000` |
| Architecture | TI TMS320C28x/C2000, little-endian 16-bit words |
| Raw-image mapping | file offset zero maps to C28x word address `0x84000` |
| Fan routine | word addresses `0x964B4` through `0x966B6` |
| Fan-routine call site | `LCR 0x0964B4` at `0x9C515` |
| Fan PWM | continuous ePWM4B, period 3333 counts |
| Temperature gate | approximately 45.0 C start / 42.0 C stop |
| Persistence | 20 start cycles / 100 stop cycles, approximately 2 s / 10 s at the recovered cadence |
| Temperature demand | approximately `(temperature_deci_c - 450) * 0.28 + 30` |
| Arbitration | maximum of temperature, load, charge, and discharge-related demands |
| Smoothing | `state += (target - state) / 32` in fixed-point form |
| Lock input | GPIO67, active-low lock indication; no pulse-count RPM measurement |
| Lock persistence | 50 low/high cycles, approximately 5 s at the recovered cadence |

The V8.16.9 threshold instructions begin at word addresses `0x96501` and
`0x96508`. The reviewed patch bytes are in continuation words, which is why
file offsets `0x24A04` and `0x24A12` do not point to the first word of each
instruction. This distinction is important when reviewing exact diffs.

## 1. Preserve and identify the source

Keep an immutable pristine image and work from a copy. Record the source origin,
filename, displayed version, product model, hardware revision if known, byte
size, SHA-256, and final 16 to 64 bytes.

Do not assume the filename proves identity. If the image is extracted or
decoded from a container, record a new hash for every transformation and keep
the original input.

A nearby vendor version is useful for finding relocated blocks, headers, and
update metadata. It is corroborating evidence, not a patch template.

## 2. Establish how bytes become instructions

Before looking for fan constants, establish:

- processor architecture and instruction set;
- byte order and address unit;
- raw image or container layout;
- load base and file-offset mapping;
- checksums, trailers, signatures, or other update metadata.

For a suspected C28x raw image, test little-endian 16-bit word decoding and
distinguish byte offsets from word addresses. A credible load mapping should
produce coherent functions, valid long-call and branch targets, plausible
vectors, and consistent peripheral accesses across a substantial region.

For V8.16.9 the confirmed mapping is:

```text
word_address = 0x84000 + file_offset / 2
file_offset  = (word_address - 0x84000) * 2
```

That equation is invalid for another image until independently established.

One reproducible C28x technique is to convert each little-endian word to a
`.word` in a temporary section, link it at the candidate base, and inspect it
with TI `dis2000 --all --hex --data_as_text`. Record the tool version; V8.16.9
was analyzed with C2000 Code Generation Tools 25.11.1 LTS.

## 3. Find the physical fan output

Hardware-facing anchors are stronger than temperature constants. Begin with PWM
or GPIO initialization, identify every runtime write to the output register, and
trace the command backward through clamps, scaling, smoothing, and selection.

Confirm whether the hardware uses continuous PWM, discrete voltage selection,
simple on/off control, or another method. When several channels exist, establish
which one reaches the physical fan.

In V8.16.9, the period `0x0D05` (3333) and the runtime write through peripheral
base `0x4300`, offset `0x6D`, jointly identify ePWM4B. Neither anchor would be
sufficient by itself.

## 4. Recover every demand source

Trace the value feeding the fan output backward. For each contributing demand,
record its producer, unit, scaling, clamps, enable conditions, and relationship
to the final selector.

V8.16.9 computes four requests, selects the largest, and smooths the result by
1/32. This explains two common mistakes:

- changing only a load-derived path does not create reliable thermal control;
- changing only the temperature gate leaves the temperature-duty curve anchored
  to the old start temperature.

Variable names should follow observed roles. If the evidence does not establish
whether a value represents temperature, load, charge current, or discharge
current, leave it unknown.

## 5. Establish temperature units and hysteresis

A constant resembling `450` is not automatically 45.0 C. Look for several
independent anchors:

- a cross-reference to exported heatsink or internal-temperature telemetry;
- consistent conversion or scaling to deci-degrees C;
- paired start and stop comparisons;
- state transitions and persistence counters;
- a duty curve using the same value;
- runtime correlation between telemetry and fan behavior.

The V8.16.9 state machine can be summarized as:

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

This pseudocode omits mode and override conditions that still need to be traced
in another firmware.

## 6. Recover lock or tachometer handling

Trace the physical status input independently of the PWM output. Determine
whether the firmware counts tachometer pulses, reads a static lock signal, or
does not monitor the fan.

V8.16.9 reads one GPIO bit with 50-cycle persistence. The recovered path has no
edge counter, timer capture, or RPM calculation. The fan wiring and runtime
behavior support interpreting GPIO67 as an active-low lock signal, and monitoring
is disabled while the fan is stopped.

Preserve this path unless fan-fault behavior is itself the subject of a separate,
evidence-backed change.

## 7. Compare another version structurally

When comparing versions, a table like the following helps show which parts of
the control path have actually been identified and which remain unknown:

| Anchor | Evidence to locate | Status |
|---|---|---|
| PWM peripheral and channel | register and address flow | unknown |
| PWM period and duty write | initialization plus runtime writer | unknown |
| Temperature source and unit | producer, scaling, telemetry cross-reference | unknown |
| Start/stop hysteresis | paired comparisons and state transitions | unknown |
| Persistence | counter initialization and terminal tests | unknown |
| Temperature curve | conversion, origin, slope, offset, and clamps | unknown |
| Other demands | inputs and final arbitration | unknown |
| Smoothing | accumulator data flow | unknown |
| Lock and fault path | physical input through error state | unknown |

Patch locations should not be selected while any part of this control path
remains unknown. Before proceeding, each conclusion should have at least
`strongly-supported` evidence, and the proposed patch instructions and their
original bytes need `confirmed-static` evidence.

Similarity or signature scanning can prioritize a region for manual review. It
cannot complete a row by itself. A materially different control structure calls
for a new analysis, not a forced V8.16.9-shaped match.

## 8. Design the smallest coherent change

Write a patch plan before changing bytes. It should contain:

- exact source identity and requested behavior;
- instruction addresses and file offsets;
- complete original instructions and bytes;
- replacement instructions and expected bytes;
- why every edit is necessary;
- nearby paths intentionally left unchanged;
- the expected exact changed-byte set;
- unresolved assumptions.

For a V8.16.9-style lower start temperature, the temperature-curve origin must
move consistently with the gate. PWM setup, minimum duty behavior, arbitration,
smoothing, lock detection, fault handling, and unrelated power-control logic
should remain unchanged.

Use an independent assembler to verify replacement encodings. In particular, do
not treat the displayed words of a multiword C28x floating-point instruction as
a normal contiguous IEEE-754 byte string; assemble and disassemble the complete
instruction.

## 9. Validate the candidate as an artifact

After creating a candidate, verify it independently against the pristine image.
The verification should cover:

- pristine source SHA-256 and size;
- expected trailer, checksum, or container metadata;
- original bytes at every patch location;
- absence of missing, duplicate, overlapping, or out-of-range patches;
- exact changed bytes rather than a broad changed range;
- unchanged output size and required metadata;
- expected output SHA-256;
- valid disassembly of every replacement instruction.

For the V8.16.9 35/60/32 C and 40/65/37 C profiles, the stock slope is retained
and one threshold byte remains unchanged. The actual changed-byte set is:

```text
0x24A04, 0x24A12, 0x24B7E, 0x24B7F
```

Do not include `0x24A05` merely because it belongs to a patched instruction
word. Profiles that change the curve slope also change reviewed `MOVIZ` and
`MOVXI` immediate words; their exact sets are recorded in
[`profiles/profiles.json`](../profiles/profiles.json).

## 10. Plan runtime validation separately

Runtime validation is a new stage with new risks. Record:

- exact test device and hardware revision;
- recovery method and power-bypass arrangement;
- stock and candidate firmware identities;
- internal temperatures, load, charge/discharge, fan state, and alarms;
- ambient or room-temperature context;
- rollback thresholds and who can disconnect power safely.

Physical installation should occur only after the exact device and candidate
have been reviewed and explicitly approved. A successful static review does not
provide that approval.

## When the analysis is not sufficient

Do not produce a candidate when the executable mapping is unresolved, when only
constants or signatures match, when temperature units lack independent support,
or when fan output and fault handling cannot be separated. Also stop if an edit
would cross an uncertain instruction boundary, source metadata is incomplete,
or the resulting diff contains unexpected bytes.

The useful outcome in that situation is a precise statement of the missing
evidence and the next read-only experiment—not a guessed patch.

## Common failure modes

- **Byte/word confusion:** C28x addresses words while ordinary file tools report bytes.
- **Continuation-word confusion:** a file offset may land in the second word of a multiword instruction.
- **False constant match:** values such as 420 or 450 also occur in protection and calibration code.
- **Immediate-decoding error:** extended C28x floating-point words are not always a contiguous IEEE-754 literal.
- **Demand-source omission:** load or current may request fan output below the temperature gate.
- **Fault-path damage:** fan enable changes can unintentionally alter lock monitoring or error recovery.
- **Timing overclaim:** a counter becomes seconds only after the call cadence is established.
- **Hardware-revision overclaim:** a shared firmware label does not prove identical fans, sensors, power stages, or boards.
- **Static-success overclaim:** valid instructions and hashes do not prove a safe device update.

## What can be published

Publish original documentation, pseudocode, hashes, tools, and only the short
instruction excerpts needed to support conclusions. Do not publish source or
modified vendor BINs, full disassemblies, or unrelated proprietary code. The
repository MIT License covers only original project material; see
[`NOTICE.md`](../NOTICE.md).
