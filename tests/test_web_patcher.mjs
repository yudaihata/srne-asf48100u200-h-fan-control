import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import {
  PatcherError,
  buildProvenance,
  buildCandidate,
  inspectSource,
  outputFileName,
  profileNameForTemperatures,
  sha256Hex,
  validateManifest,
} from "../web/patcher-core.mjs";

const manifest = validateManifest(JSON.parse(await fs.readFile(new URL("../profiles/profiles.json", import.meta.url), "utf8")));
const sourcePath = process.env.SRNE_SOURCE_BIN;

async function syntheticFixture() {
  const source = new Uint8Array(256);
  source.set([0x23, 0x01, 0x67, 0x45], source.length - 4);
  const constraints = {
    allowed_start_c: [35, 40, 45],
    allowed_max_c: [50, 55, 60, 65, 70],
    minimum_span_c: 10,
    stop_delta_c: 3,
  };
  const profiles = {};
  let offset = 8;
  for (const start of constraints.allowed_start_c) {
    for (const maximum of constraints.allowed_max_c) {
      if (maximum - start < constraints.minimum_span_c) continue;
      const stop = start - constraints.stop_delta_c;
      const name = `fan${start}C_max${maximum}C_off${stop}C`;
      const candidate = source.slice();
      candidate[offset] = offset;
      profiles[name] = {
        start_c: start,
        max_c: maximum,
        stop_c: stop,
        curve_origin_c: start,
        slope_f32: 70 / ((maximum - start) * 10),
        output_sha256: await sha256Hex(candidate),
        patches: [{ offset: `0x${offset.toString(16)}`, expected_hex: "00", replacement_hex: offset.toString(16).padStart(2, "0") }],
        changed_offsets: [`0x${offset.toString(16)}`],
        evidence: {
          static_encoding: "confirmed-static",
          candidate_identity: "confirmed-static",
          runtime: "not-established",
          runtime_document: null,
        },
      };
      offset += 1;
    }
  }
  return {
    source,
    manifest: validateManifest({
      format_version: 2,
      source: { label: "synthetic.bin", sha256: await sha256Hex(source), size: source.length, trailer_hex: "23016745" },
      constraints,
      profile_aliases: {},
      profiles,
    }),
  };
}

test("manifest exposes exactly the 14 reviewed fan profiles", () => {
  assert.equal(Object.keys(manifest.profiles).length, 14);
  assert.equal(profileNameForTemperatures(manifest, 35, 50), "fan35C_max50C_off32C");
  assert.equal(profileNameForTemperatures(manifest, 45, 50), undefined);
  assert.equal(profileNameForTemperatures(manifest, 45, 55), "fan45C_max55C_off42C");
});

test("output names are deterministic", () => {
  assert.equal(
    outputFileName("fan40C_max65C_off37C"),
    "ASF48100SU200_V8.16.9_fan40C_max65C_off37C.bin",
  );
});

test("wrong-size source is rejected before patching", async () => {
  await assert.rejects(
    () => inspectSource(new Uint8Array(64), manifest),
    (error) => error instanceof PatcherError && error.code === "SOURCE_SIZE",
  );
});

test("synthetic source exercises every reviewed browser profile without vendor firmware", async () => {
  const fixture = await syntheticFixture();
  for (const name of Object.keys(fixture.manifest.profiles)) {
    const result = await buildCandidate(fixture.source, fixture.manifest, name);
    assert.equal(result.changedOffsets.length, 1);
  }
});

test("provenance records source, candidate, evidence, and repository commit", async () => {
  const fixture = await syntheticFixture();
  const name = Object.keys(fixture.manifest.profiles)[0];
  const result = await buildCandidate(fixture.source, fixture.manifest, name);
  const provenance = buildProvenance(
    fixture.manifest,
    name,
    result,
    { repository: "owner/repo", commit: "abc123" },
    "2026-08-12T00:00:00.000Z",
  );
  assert.equal(provenance.repository_commit, "abc123");
  assert.equal(provenance.source.sha256, fixture.manifest.source.sha256);
  assert.equal(provenance.candidate.sha256, result.sha256);
  assert.equal(provenance.profile.evidence.runtime, "not-established");
});

test("reviewed source produces exact candidate hashes", { skip: !sourcePath }, async () => {
  const source = new Uint8Array(await fs.readFile(sourcePath));
  for (const [name, profile] of Object.entries(manifest.profiles)) {
    const result = await buildCandidate(source, manifest, name);
    assert.equal(result.sha256, profile.output_sha256);
    assert.deepEqual(result.changedOffsets, profile.changed_offsets.map((value) => Number.parseInt(value, 16)));
  }

  const legacyCandidates = new Map([
    ["fan35C_max60C_off32C", "ASF48100SU200_V8.16.9_fan35C_off32C.bin"],
    ["fan40C_max65C_off37C", "ASF48100SU200_V8.16.9_fan40C_off37C.bin"],
  ]);
  for (const [name, filename] of legacyCandidates) {
    const result = await buildCandidate(source, manifest, name);
    const reviewed = new Uint8Array(await fs.readFile(path.join(path.dirname(sourcePath), filename)));
    assert.deepEqual(result.bytes, reviewed);
  }
});
