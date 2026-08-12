export class PatcherError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "PatcherError";
    this.code = code;
  }
}

export function bytesFromHex(value) {
  if (typeof value !== "string" || value.length % 2 !== 0 || !/^[0-9a-f]*$/i.test(value)) {
    throw new PatcherError("MANIFEST", `Invalid hexadecimal value: ${value}`);
  }
  return Uint8Array.from(value.match(/.{2}/g) ?? [], (pair) => Number.parseInt(pair, 16));
}

export function hexFromBytes(bytes) {
  return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
}

export async function sha256Hex(bytes) {
  if (!globalThis.crypto?.subtle) {
    throw new PatcherError("BROWSER", "Web Crypto API is unavailable");
  }
  const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  const data = view.buffer.slice(view.byteOffset, view.byteOffset + view.byteLength);
  return hexFromBytes(new Uint8Array(await globalThis.crypto.subtle.digest("SHA-256", data)));
}

function assertBytesAt(image, offset, expected, code) {
  const actual = image.slice(offset, offset + expected.length);
  if (actual.length !== expected.length || actual.some((value, index) => value !== expected[index])) {
    throw new PatcherError(
      code,
      `Unexpected bytes at 0x${offset.toString(16).toUpperCase()}: ${hexFromBytes(actual)}`,
    );
  }
}

export function validateManifest(manifest) {
  if (manifest?.format_version !== 2 || !manifest.source || !manifest.profiles || !manifest.constraints) {
    throw new PatcherError("MANIFEST", "Unsupported or incomplete profile manifest");
  }
  if (!/^[0-9a-f]{64}$/.test(manifest.source.sha256) || !Number.isInteger(manifest.source.size)) {
    throw new PatcherError("MANIFEST", "Invalid source identity");
  }

  const constraints = manifest.constraints;
  const expected = [];
  for (const start of constraints.allowed_start_c ?? []) {
    for (const maximum of constraints.allowed_max_c ?? []) {
      if (maximum - start < constraints.minimum_span_c) continue;
      const stop = start - constraints.stop_delta_c;
      expected.push(`fan${start}C_max${maximum}C_off${stop}C`);
    }
  }

  const actual = Object.keys(manifest.profiles).sort();
  if (expected.length !== 14 || actual.join("\n") !== expected.sort().join("\n")) {
    throw new PatcherError("MANIFEST", "Reviewed fan profile set is incomplete");
  }

  for (const name of expected) {
    const profile = manifest.profiles[name];
    if (!profile?.patches?.length || !profile?.output_sha256 || !profile?.changed_offsets) {
      throw new PatcherError("MANIFEST", `Missing reviewed profile: ${name}`);
    }
    if (
      profile.stop_c !== profile.start_c - constraints.stop_delta_c
      || profile.max_c - profile.start_c < constraints.minimum_span_c
      || profile.curve_origin_c !== profile.start_c
    ) {
      throw new PatcherError("MANIFEST", `Invalid reviewed temperatures: ${name}`);
    }
    if (
      profile.evidence?.static_encoding !== "confirmed-static"
      || !["confirmed-static", "stock-equivalent"].includes(profile.evidence?.candidate_identity)
      || !["runtime-observed", "not-established"].includes(profile.evidence?.runtime)
      || (profile.evidence.runtime === "runtime-observed" && !profile.evidence.runtime_document)
    ) {
      throw new PatcherError("MANIFEST", `Invalid evidence metadata: ${name}`);
    }

    const changed = [];
    const covered = new Set();
    for (const patch of profile.patches) {
      const offset = Number.parseInt(patch.offset, 16);
      const before = bytesFromHex(patch.expected_hex);
      const after = bytesFromHex(patch.replacement_hex);
      if (!Number.isInteger(offset) || offset < 0 || offset + before.length > manifest.source.size || before.length !== after.length) {
        throw new PatcherError("MANIFEST", `Invalid patch bounds: ${name}`);
      }
      for (let index = 0; index < before.length; index += 1) {
        const position = offset + index;
        if (covered.has(position)) throw new PatcherError("MANIFEST", `Overlapping patches: ${name}`);
        covered.add(position);
        if (before[index] !== after[index]) changed.push(position);
      }
    }
    const declared = profile.changed_offsets.map((value) => Number.parseInt(value, 16));
    if (changed.length !== declared.length || changed.some((value, index) => value !== declared[index])) {
      throw new PatcherError("MANIFEST", `Invalid changed offsets: ${name}`);
    }
  }
  return manifest;
}

export function profileNameForTemperatures(manifest, startC, maxC) {
  validateManifest(manifest);
  const stopC = startC - manifest.constraints.stop_delta_c;
  const name = `fan${startC}C_max${maxC}C_off${stopC}C`;
  return manifest.profiles[name] ? name : undefined;
}

export async function inspectSource(source, manifest) {
  validateManifest(manifest);
  const image = source instanceof Uint8Array ? source : new Uint8Array(source);
  const spec = manifest.source;

  if (image.length !== spec.size) {
    throw new PatcherError("SOURCE_SIZE", `Unexpected source size: ${image.length}`);
  }

  const digest = await sha256Hex(image);
  if (digest !== spec.sha256) {
    throw new PatcherError("SOURCE_HASH", `Unexpected source SHA-256: ${digest}`);
  }

  const trailer = bytesFromHex(spec.trailer_hex);
  assertBytesAt(image, image.length - trailer.length, trailer, "SOURCE_TRAILER");

  return { size: image.length, sha256: digest, label: spec.label };
}

export async function buildCandidate(source, manifest, profileName) {
  const image = source instanceof Uint8Array ? source : new Uint8Array(source);
  await inspectSource(image, manifest);
  const profile = manifest.profiles[profileName];
  if (!profile) {
    throw new PatcherError("PROFILE", `Unknown profile: ${profileName}`);
  }

  const candidate = image.slice();
  for (const patch of profile.patches) {
    const offset = Number.parseInt(patch.offset, 16);
    const expected = bytesFromHex(patch.expected_hex);
    const replacement = bytesFromHex(patch.replacement_hex);
    if (expected.length !== replacement.length) {
      throw new PatcherError("MANIFEST", `Patch length mismatch at ${patch.offset}`);
    }
    assertBytesAt(candidate, offset, expected, "SOURCE_BYTES");
    candidate.set(replacement, offset);
  }

  const changed = [];
  for (let index = 0; index < image.length; index += 1) {
    if (image[index] !== candidate[index]) changed.push(index);
  }
  const expectedChanged = profile.changed_offsets.map((value) => Number.parseInt(value, 16));
  if (changed.length !== expectedChanged.length || changed.some((value, index) => value !== expectedChanged[index])) {
    throw new PatcherError("CHANGED_OFFSETS", `Unexpected changed offsets: ${changed.join(",")}`);
  }

  const digest = await sha256Hex(candidate);
  if (digest !== profile.output_sha256) {
    throw new PatcherError("OUTPUT_HASH", `Unexpected output SHA-256: ${digest}`);
  }

  return { bytes: candidate, sha256: digest, changedOffsets: changed };
}

export function outputFileName(profileName) {
  return `ASF48100SU200_V8.16.9_${profileName}.bin`;
}

export function buildProvenance(manifest, profileName, result, buildInfo = {}, createdAt = new Date().toISOString()) {
  const profile = manifest.profiles[profileName];
  if (!profile) throw new PatcherError("PROFILE", `Unknown profile: ${profileName}`);
  return {
    format: "srne-fan-candidate-provenance-v1",
    created_at: createdAt,
    repository: buildInfo.repository ?? "yudaihata/srne-asf48100u200-h-fan-control",
    repository_commit: buildInfo.commit ?? "unknown",
    manifest_format_version: manifest.format_version,
    source: {
      label: manifest.source.label,
      sha256: manifest.source.sha256,
      size: manifest.source.size,
    },
    profile: {
      name: profileName,
      start_c: profile.start_c,
      max_c: profile.max_c,
      stop_c: profile.stop_c,
      evidence: profile.evidence,
    },
    candidate: {
      filename: outputFileName(profileName),
      sha256: result.sha256,
      changed_offsets: result.changedOffsets.map((value) => `0x${value.toString(16).toUpperCase()}`),
    },
  };
}
