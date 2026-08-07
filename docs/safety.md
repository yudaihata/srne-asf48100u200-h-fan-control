# Safety and deployment boundary

This repository documents independent reverse engineering. It is not an
installation recommendation and does not make modified firmware safe.

Before any device write:

1. Confirm the model, hardware revision, firmware version, source SHA-256,
   source size, and trailer.
2. Build from the pristine source, never from an earlier candidate.
3. Run `verify_candidate.py` with both `--candidate` and `--source`.
4. Review the four changed offsets and candidate SHA-256.
5. Keep a known-good backup, spare control board if available, and a verified
   way to transfer the load to grid power.
6. Test on non-critical hardware while monitoring all three temperatures,
   fan operation, alarms, power paths, and abnormal noise.

Known unresolved risks include:

- no official recovery procedure for an interrupted or rejected update;
- unknown compatibility across hardware revisions;
- no proof that the updater authenticates, transforms, or validates every
  image in the same way;
- more fan runtime, noise, dust ingestion, and bearing wear;
- possible interaction with thermal conditions absent from the test day;
- warranty, electrical-code, insurance, and regulatory consequences.

Do not bypass fan-lock or high-temperature error paths. The documented profiles
do not intentionally change them.
