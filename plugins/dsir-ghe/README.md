# DSIR GHE local test plugin

Independent WHO Global Health Estimates access using the host's existing
Python standard library. Users do not install R, DSIR or additional packages.
The host must permit script execution, public WHO HTTPS and result-file writes.

This directory holds packaging metadata. The authoritative runtime is
`dsir-ghe/` at the repository root. Build the complete plugin from tracked
source with `packaging/build_data_test_package.R --skill dsir-ghe`; do not
install this metadata directory as a complete plugin.

The package includes the DSIR country mapping, exact-code discovery, bounded
retrieval, completeness checks, QA and CSV/JSON provenance. It does not run a
server, merge GHO or SDG, derive age-standardized rates, or aggregate overlapping
causes or ages. See the packaged `TESTING.md` for installation and acceptance.
The maintainer is Shanlong Ding. This is an independent open-source tool.
