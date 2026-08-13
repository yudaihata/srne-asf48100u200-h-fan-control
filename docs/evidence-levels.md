# Evidence levels

The patcher deliberately separates file-integrity checks from runtime evidence.
Every reviewed profile in `profiles/profiles.json` carries four fields:

- `static_encoding`: the replacement instructions were independently decoded or assembled;
- `candidate_identity`: the exact source-to-candidate transformation and SHA-256 are known;
- `runtime`: whether this exact profile has recorded device observations;
- `runtime_document`: the document containing those observations, or `null`.

`confirmed-static` does not mean that an updater accepts the image or that a
device boots and operates safely. `runtime-observed` applies only to the device,
hardware context, updater, duration, and conditions recorded in the linked
document. Missing metadata is written as `not-recorded`; it is never inferred.

Current runtime status:

| Profile | Static identity | Runtime |
|---|---|---|
| `fan35C_max60C_off32C` | confirmed | observed on one ASF48100U200-H with control panel V3.00, power amplifier board V3.02, and Windows iPower 2.1.2.0 |
| `fan45C_max70C_off42C` | stock-equivalent | stock-day observations are included in the comparison |
| Other 12 reviewed profiles | confirmed | not established |

The Browser Patcher's “verified” result means that the selected source, patch
bytes, changed offsets, and candidate hash agree with the reviewed manifest. It
does not upgrade the profile's runtime evidence level.
