# Repository instructions for coding agents

This is a public, safety-sensitive firmware reverse-engineering repository.
These instructions apply to the entire repository.

The human-readable technical method is documented in
`docs/porting-to-other-firmware.md`. Use
`docs/templates/porting-record.yaml` for a new firmware investigation.

## Repository boundary

- Keep this checkout limited to the public fan-control project.
- Do not add MPPT or other unpublished research, private logs, device serial
  numbers, vendor firmware, modified firmware, or full vendor disassemblies.
- Keep private research in a separate clone with a separate `.git` directory.
- Candidate BIN generation and physical-device installation are separate
  actions. Never write firmware to a device without explicit approval for the
  exact device and candidate.

## Analysis contract

When analyzing another firmware image or related product, you MUST:

1. preserve an immutable pristine source and record model, hardware revision,
   firmware label, source origin, byte size, and SHA-256;
2. determine architecture, image layout, address unit, endianness, and load
   mapping independently instead of inheriting them from V8.16.9;
3. recover the fan output, temperature input, demand arbitration, persistence,
   smoothing, and lock/fault paths as one control system;
4. classify each conclusion as `confirmed-static`, `strongly-supported`,
   `runtime-observed`, `hypothesis`, or `not-established`;
5. stop before candidate generation when any evidence gate below is unmet;
6. propose the smallest semantic change and preserve unrelated protection,
   fault, inverter, charging, and MPPT paths;
7. verify original bytes, exact changed offsets, output size, trailer or
   checksum behavior, and output SHA-256;
8. keep static completion, candidate generation, and physical installation as
   distinct approval boundaries.

You MUST NOT:

- reuse V8.16.9 offsets or byte patterns in another image without fresh
  instruction-boundary, control-flow, and data-flow evidence;
- patch the first occurrence of a plausible constant such as `450`, `420`,
  `3333`, or `30.0`;
- treat a signature match, binary similarity score, valid disassembly, clean
  checksum, or filename as hardware-compatibility evidence;
- claim updater acceptance, safe boot, runtime safety, or hardware compatibility
  from static analysis;
- publish or commit a vendor BIN, modified BIN, full disassembly, or unrelated
  proprietary code.

## Mandatory stop conditions

Stop without producing a candidate if any of these conditions applies:

- architecture, endianness, address unit, or load mapping is unresolved;
- only constants, signatures, or similarity scores match;
- temperature units are inferred from magnitude alone;
- the fan PWM channel or physical output cannot be established;
- start, stop, curve origin, arbitration, smoothing, or fault handling cannot be
  separated;
- a proposed edit crosses an uncertain instruction boundary;
- source hash, size, original bytes, trailer, or checksum behavior is unknown;
- more bytes change than the reviewed patch plan predicts;
- the target uses a materially different control structure;
- available evidence contradicts the proposed interpretation.

Report the failed evidence gate and the next read-only experiment. Do not guess.

## Candidate and repository checks

Before proposing a candidate, record:

- the exact source identity and requested behavior;
- instruction addresses, file offsets, complete original instructions and bytes;
- replacement instructions and independently verified encodings;
- why every changed instruction is necessary;
- nearby control and protection paths intentionally left unchanged;
- the expected exact changed-byte set and unresolved assumptions.

For changes to this repository:

- do not edit `profiles/profiles.json` directly; update `spec/` and run
  `python3 tools/generate_manifest.py`;
- keep all existing candidate byte streams and hashes unchanged unless the task
  explicitly authorizes a new reviewed profile or firmware target;
- run `python3 tools/generate_manifest.py --check`;
- run `python3 -m unittest discover -s tests -v`;
- run `node --test tests/test_web_patcher.mjs`;
- when the pristine local source is available, run the Node suite with
  `SRNE_SOURCE_BIN` and run `tools/release_validate.py`;
- run `git diff --check` and confirm no BIN or private research is staged.

## Required handoff

For a new firmware investigation, complete
`docs/templates/porting-record.yaml`. The final report must clearly separate:

- source and executable mapping;
- confirmed static findings;
- strongly supported interpretations;
- hypotheses and unresolved items;
- runtime observations;
- patch authorization state and exact proposed offsets;
- what was not tested, especially updater acceptance and physical-device behavior.

Attach only concise evidence excerpts, hashes, tool versions, and reproducible
commands. Do not attach the source firmware or a full vendor disassembly.
