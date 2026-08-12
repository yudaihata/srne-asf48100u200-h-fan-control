# Contributing

This is a safety-sensitive reverse-engineering project. Keep changes small and
separate static conclusions, candidate generation, and physical-device writes.

Before opening a pull request:

```bash
python3 tools/generate_manifest.py --check
python3 -m unittest discover -s tests -v
node --test tests/test_web_patcher.mjs
git diff --check
```

Do not edit `profiles/profiles.json` directly. Update the concise files under
`spec/`, run `python3 tools/generate_manifest.py`, and commit the generated
manifest together with its source specification and tests.

Never commit vendor BINs, patched BINs, device serial numbers, private logs, or
private research. The public fan-control checkout must have only the public
GitHub remote. Keep MPPT and other unpublished research in a separate clone with
a separate `.git` directory.

See `docs/release-process.md` for the additional evidence gate required before a
release.
