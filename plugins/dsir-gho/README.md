# DSIR GHO Health Data Skill plugin

Unreleased Phase 1 source candidate for the existing skills-only GHO plugin. It keeps
the same commands and 15-column exports, defaults to legacy, and supports explicit
`--backend xmart`. No R, MCP server, hosted service or WHO API key is required.
See the [source comparison guide](skills/dsir-gho/references/backend_comparison.md)
and the source repository's `dsir-gho/reports/phase1-20261023.md` for validation.

## Package status

Only source files were updated. Existing version strings identify the
previous packaging baseline; release archives, installed plugins and marketplace
configuration were not changed. A future release needs a separate reviewed build
and version decision. The build script currently reads its standalone ZIP input;
do not rebuild from an old ZIP and overwrite these repaired sources.

The host needs Python 3.10+, script execution and HTTPS access to
`ghoapi.azureedge.net` for legacy, or `xmart-api-public.who.int` for xMart.
The following installation instructions describe existing distribution methods;
they do not install this unbuilt source candidate.

## For colleagues using the existing standalone ZIP in local Codex

PowerShell is optional. The installer only copies files to the skill directory.

On Windows, use File Explorer:

1. Extract `dsir-gho-0.1.1.zip`.
2. Enter `%USERPROFILE%` in File Explorer's address bar.
3. Open or create `.agents`, and inside it open or create `skills`.
4. Copy the extracted `dsir-gho` folder into that `skills` folder.
5. Confirm the final layout is `%USERPROFILE%\.agents\skills\dsir-gho\SKILL.md`, with `scripts` and `references` next to that file. Avoid an extra nested `dsir-gho` folder.
6. Start a new Codex conversation, restarting the app if discovery has not refreshed. Ask: `Use $dsir-gho to retrieve historical UHC service coverage for the Western Pacific Region.`

Do not overwrite an existing installation without reviewing it. The bundled PowerShell installer automates steps 2-5 and refuses an existing target. Merely extracting the ZIP to Downloads is not an installation.

## Local developer testing of this plugin

Extract the plugin ZIP and ask Codex to register the extracted plugin in your personal marketplace using its plugin-creator capability. After registration, refresh the Plugins Directory, open the plugin from that local source, install it, and start a new conversation. Registration is a separate operation; this ZIP does not silently update a personal marketplace.

If the target client lacks that capability, use its documented local marketplace setup rather than guessing an upload button. Do not copy the plugin root into the standalone skill directory. For a standalone fallback, the actual skill is under `skills/dsir-gho/`.

## ChatGPT installation and sharing

For the browser-based colleague experience, first make the plugin available to the target account through a supported workspace or public distribution route. A local developer's plugin registration is not a ChatGPT workspace installation.

Once the plugin is available in the colleague's Plugins Directory:

1. Open Plugins and locate DSIR GHO Health Data Skill.
2. Open its details and select the installation plus button.
3. Start a new chat. Use `@` to select the plugin or its skill, then ask a normal health-data question.
4. Confirm the agent's runtime can execute the bundled client and reach WHO. Use a Work/code-capable environment when required by the account's available tools.

Examples:

- Show historical UHC Service Coverage Index for the Western Pacific Region.
- Get measles reported cases in the Philippines since 2015.
- Compare historical UHC service coverage in China, Japan and the Philippines.
- Find WHO indicators for catastrophic health expenditure above 10%.

These are the steps for an available plugin, not proof this package is already discoverable in any account. Uploading the ZIP as a normal chat attachment or as Custom GPT Knowledge is not a documented installation method here. Do not promise colleagues a universal ZIP-upload button or unrestricted internet access.

## Publisher's next step

For public distribution, the official submission flow supports skills-only plugins and requires publisher verification and review. This build does not establish submission or approval. The listing uses the [public website](https://shanlong-who.github.io/dsir-health-data-skills/), [privacy policy](https://shanlong-who.github.io/dsir-health-data-skills/privacy.html) and [GitHub Issues support](https://github.com/shanlong-who/dsir-health-data-skills/issues). The subtitle is `Find and download WHO GHO data` and the category is `Data & Analytics`. Confirm saved dashboard fields after uploading the new ZIP.

Official references:

- [Plugin format](https://developers.openai.com/plugins/build/plugins)
- [Local testing](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [Plugin installation and use](https://learn.chatgpt.com/docs/plugins)
- [Skills-only public submission](https://developers.openai.com/plugins/deploy/submission)
- [ChatGPT Work networking](https://learn.chatgpt.com/docs/enterprise/chatgpt-work-overview)
