import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import {
  PatcherError,
  buildCandidate,
  inspectSource,
  outputFileName,
  validateManifest,
} from "../web/patcher-core.mjs";

const manifest = validateManifest(JSON.parse(await fs.readFile(new URL("../profiles/profiles.json", import.meta.url), "utf8")));
const sourcePath = process.env.SRNE_SOURCE_BIN;

test("manifest exposes only the two reviewed fan profiles", () => {
  assert.deepEqual(Object.keys(manifest.profiles).sort(), ["fan35C_off32C", "fan40C_off37C"]);
});

test("output names are deterministic", () => {
  assert.equal(outputFileName("fan40C_off37C"), "ASF48100SU200_V8.16.9_fan40C_off37C.bin");
});

test("wrong-size source is rejected before patching", async () => {
  await assert.rejects(
    () => inspectSource(new Uint8Array(64), manifest),
    (error) => error instanceof PatcherError && error.code === "SOURCE_SIZE",
  );
});

test("reviewed source produces exact candidate hashes", { skip: !sourcePath }, async () => {
  const source = new Uint8Array(await fs.readFile(sourcePath));
  for (const [name, profile] of Object.entries(manifest.profiles)) {
    const result = await buildCandidate(source, manifest, name);
    assert.equal(result.sha256, profile.output_sha256);
    assert.deepEqual(result.changedOffsets, profile.changed_offsets.map((value) => Number.parseInt(value, 16)));
    const reviewed = new Uint8Array(await fs.readFile(path.join(path.dirname(sourcePath), outputFileName(name))));
    assert.deepEqual(result.bytes, reviewed);
  }
});
