# DSIR GHO local test plugin

This is the local test candidate for the GHO Phase 1 repair. It keeps the existing
commands and 15-column exports, defaults to legacy, and supports explicit
--backend xmart. It never automatically switches or combines sources. See the
[source comparison guide](skills/dsir-gho/references/backend_comparison.md).

The host needs Python 3.10+, script execution and HTTPS to ghoapi.azureedge.net
(legacy) and xmart-api-public.who.int (xMart). No R, API key, MCP server or hosted
service is required. GHE is outside this plugin.

## Build and installation

From a clean repository with R and `digest`, `jsonlite` and `zip` installed, run:

    Rscript packaging/build_gho_test_package.R --output-dir dist/gho-0.1.4-test.4

The R builder uses tracked dsir-gho source, not old ZIPs or the embedded runtime
copy. It creates a plugin ZIP, a standalone skill ZIP, a local marketplace folder,
checksums and TESTING.md. It verifies the archive paths and every file byte before
the build succeeds, and it never rewrites source or existing outputs.

In the repository, read packaging/GHO_TESTING.md. In a built package, read
TESTING.md for exact local installation and acceptance steps. BUILD.json identifies
the source commit and every runtime file hash. The test plugin displays as
DSIR GHO Local Test, from the dsir-gho-local-test marketplace.

Register and install the local marketplace with the documented Codex CLI. Restart
the app, select the test plugin explicitly, and verify its installed BUILD.json.
Temporarily disable another GHO installation if its identical skill name would
make testing ambiguous. The build itself does not install or register anything.

This candidate has not been submitted to an online plugin directory or uploaded
as a GitHub release. Browser-only ChatGPT distribution is a separate workflow.
Attaching the ZIP to a normal chat or to Custom GPT Knowledge is not installation.

## Acceptance

Test default legacy measles, explicit xMart DTP3, sex and age filters, valid empty
results, invalid dimensions and catalogue differences. Retain CSV, response JSON,
raw data and manifests. Report upstream failures rather than inventing values.
Engineering tests and historical evidence do not replace acceptance of the actual
installed candidate. Do not infer statistical equivalence across backends.

Official local plugin documentation:
https://developers.openai.com/plugins/build/plugins
