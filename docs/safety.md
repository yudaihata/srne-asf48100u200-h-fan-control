# Safety and deployment boundary

This repository documents independent reverse engineering. It is not an
installation recommendation and does not make modified firmware safe.

Before any device write:

1. Confirm the model, hardware revision, firmware version, source SHA-256,
   source size, and trailer.
2. Build from the pristine source, never from an earlier candidate.
3. Run `verify_candidate.py` with both `--candidate` and `--source`.
4. Review the exact declared changed-offset set and candidate SHA-256. Depending
   on the selected curve, zero to nine bytes differ from stock.
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
- possible stop/restart cycling caused by enclosure thermal lag; the public
  profiles require at least 10 °C between fan start and fan maximum, but that
  limit is statically reviewed rather than proven for every installation;
- warranty, electrical-code, insurance, and regulatory consequences.

The browser exposes only the 14 statically reviewed combinations. The manual
CLI also has an explicitly acknowledged custom mode for advanced analysis. A
custom candidate is not part of that reviewed set, has no pre-reviewed output
hash or runtime result, and can use a start-to-maximum span below 10 °C. Treat
its exact settings, generated hash, disassembly, and runtime behavior as a new
candidate requiring separate review.

Do not bypass fan-lock or high-temperature error paths. The documented profiles
do not intentionally change them.
