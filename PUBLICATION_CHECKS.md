# GitHub publication checks

Date: 2026-09-16

- GHO source unit suite: 54 tests passed.
- SDG source unit suite: 69 tests passed.
- Both extracted plugin directories passed the Codex plugin manifest validator.
- All 156 included JSON files parsed successfully.
- Plugin author and developer fields identify Shanlong Ding.
- Plugin ZIPs are unchanged from their validated local releases.
- Machine-specific report paths were normalized; runtime code was not changed.

The first sandboxed test attempt could not access temporary test directories.
The suites then passed outside that restricted sandbox without code changes.
These are publication checks; recorded live API and R parity results remain
under each skill's `reports/` directory with their original timestamps.
