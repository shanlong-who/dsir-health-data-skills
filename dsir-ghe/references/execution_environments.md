# Execution and user requirements

The intended user experience is to enable the plugin in the AI platform and
request data in natural language. The user does not install R, DSIR, Python,
additional packages or a server, and does not supply a WHO or OpenAI API key
to this plugin. Platform subscription or usage charges are separate.

The plugin uses Python 3.10+ already supplied by the host, standard-library
modules, a writable export directory and HTTPS to `xmart-api-public.who.int`.
Find the interpreter using the host's documented runtime capability, or an
existing executable; do not hardcode the maintainer's machine path. `doctor`
checks local requirements; `doctor --live` also checks the GHE schema and year
catalogue. A local pass is not proof of cloud, mobile or another account's
network access.

If a host lacks a runtime or permitted network access, explain the concrete
limitation instead of instructing an end user to install software, silently
provisioning dependencies or replacing data with web-search snippets. Network
permission is a platform/workspace setting and cannot be granted by this skill.

OpenAI documents [skills with optional scripts](https://learn.chatgpt.com/docs/build-skills)
and [plugin packaging](https://developers.openai.com/plugins/build/plugins).
Work execution location and code/shell network permissions depend on the host,
account and workspace: see [Work overview](https://learn.chatgpt.com/docs/enterprise/chatgpt-work-overview).
These references were checked on 24 October 2026; they do not establish that
every AI platform can execute this package.

This version contains no MCP or REST service. If a target platform cannot run
the client, assess a remote adapter separately with the maintainer before
deploying a service. Merely uploading the ZIP as conversation context does not
establish executable plugin installation.
