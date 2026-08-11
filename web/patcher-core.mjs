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
  if (manifest?.format_version !== 1 || !manifest.source || !manifest.profiles) {
    throw new PatcherError("MANIFEST", "Unsupported or incomplete profile manifest");
  }
  const required = ["fan40C_off37C", "fan35C_off32C"];
  for (const name of required) {
    const profile = manifest.profiles[name];
    if (!profile?.patches?.length || !profile?.output_sha256 || !profile?.changed_offsets) {
      throw new PatcherError("MANIFEST", `Missing reviewed profile: ${name}`);
    }
  }
  return manifest;
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
