[![CI](https://github.com/AI-Colleagues/skill-mgr/actions/workflows/ci.yml/badge.svg?event=push)](https://github.com/AI-Colleagues/skill-mgr/actions/workflows/ci.yml?query=branch%3Amain)
[![Coverage](https://coverage-badge.samuelcolvin.workers.dev/AI-Colleagues/skill-mgr.svg)](https://coverage-badge.samuelcolvin.workers.dev/redirect/AI-Colleagues/skill-mgr)
[![PyPI](https://img.shields.io/pypi/v/skill-mgr.svg)](https://pypi.python.org/pypi/skill-mgr)

# skill-mgr

`skill-mgr` is a standalone multi-agent skill installer and inspector for AgentSkills-compatible `SKILL.md` packages. It installs one validated skill into bundled agent targets, supports local directories and GitHub shorthand refs, and exposes the same lifecycle surface as the Orcheo skill workflows: `install`, `update`, `uninstall`, `validate`, `list`, and `show`.

## Installation

```bash
uv tool install skill-mgr
```

Run the installed CLI directly:

```bash
skill-mgr -h
```

If you want to use the CLI without installing it first:

```bash
uv run skill-mgr -h
```

If you are working from source:

```bash
uv sync --all-groups
```

## Commands

```text
skill-mgr install REF [--target TARGET ...] [--format rich|markdown|json]
skill-mgr update REF [--target TARGET ...] [--format rich|markdown|json]
skill-mgr uninstall NAME [--target TARGET ...] [--format rich|markdown|json]
skill-mgr validate REF [--format rich|markdown|json]
skill-mgr list [--target TARGET ...] [--format rich|markdown|json]
skill-mgr show NAME [--target TARGET ...] [--format rich|markdown|json]
skill-mgr support-matrix [--format rich|markdown|json]
```

Rules:

- Repeated `--target/-t` values are allowed.
- Omitting `--target` installs to bundled agents detected in the current environment.
- Explicit `--target` values bypass detection and are still honored even if the agent home directory does not exist yet.
- `all` is mutually exclusive with explicit targets.
- Rich-rendered human output is the default.
- Use `--format markdown` for plain-text Markdown tables that are easier for LLMs and other text consumers to parse.
- Use `--format json` for strict structured output.

## Source Refs

Supported `REF` forms:

- Local skill directory path containing `SKILL.md`
- GitHub shorthand `owner/repo`
- GitHub shorthand `owner/repo/path/to/skill`

Resolution behavior:

- Existing local paths always win after home expansion and normalization.
- Only non-existent local refs fall through to GitHub shorthand parsing.
- GitHub installs resolve the repository default branch via the GitHub API, download one tarball, safely extract it once, then reuse the materialized skill directory across all selected targets.
- Nested GitHub paths must resolve to a directory inside the archive.

## Initial OS Support Matrix

The bundled adapters currently publish this matrix:

| Adapter | Windows | Linux | macOS | Managed install root | Notes |
|---------|---------|-------|-------|----------------------|-------|
| `claude` | supported | supported | supported | `~/.claude/skills` | Home-relative managed skill root used by the adapter |
| `codex` | supported | supported | supported | `~/.codex/skills` | Matches the local Codex skill layout used by the app/CLI |
| `openclaw` | supported | supported | supported | `~/.openclaw/skills` | Matches OpenClaw's documented managed/local skills directory |
| `orcheo` | supported | supported | supported | `~/.orcheo/skills` | Matches Orcheo's managed local skills directory |

Platform semantics:

- `supported`: the adapter has a defined install root and is expected to work on that OS.
- `unsupported`: the adapter is intentionally skipped on that OS.
- `unknown`: the adapter root is not yet defined and the target is skipped with `unknown_install_root`.
- `agent_not_detected`: the adapter is bundled, but its home directory was not found during default target selection.

Current bundled adapters all map to explicit home-relative roots. Explicit `--target all` expands to `claude`, `codex`, `openclaw`, and `orcheo` on Windows, Linux, and macOS, while the default target set only includes agents detected on the current machine.

## `SKILL.md` Contract

`validate` enforces the following `SKILL.md` contract:

- `SKILL.md` must exist at the resolved skill directory root.
- The file must start with valid YAML frontmatter delimited by `---` lines.
- `name` is required.
- `name` must be 1-64 characters of lowercase letters, numbers, and internal hyphens.
- `description` is required and must be a non-empty string.
- `license`, when present, must be a string.
- `compatibility`, when present, must be a string.
- `metadata`, when present, must be a mapping.
- `allowed-tools`, when present, must be a string.

Recognized fields are normalized into the validation output:

- `name`
- `description`
- `license`
- `compatibility`
- `metadata`
- `allowed-tools`

Unknown frontmatter keys are preserved in `extra_fields` in the library result so downstream tools can retain adapter-specific metadata.

Minimal valid example:

```md
---
name: demo-skill
description: Explain what the skill does and when to use it.
---

Skill instructions go here.
```

## Examples

Install from a local directory into every bundled target:

```bash
skill-mgr install ~/skills/demo-skill
```

Install only for Codex and Claude:

```bash
skill-mgr install ~/skills/demo-skill -t codex -t claude
```

Install from a GitHub repo root:

```bash
skill-mgr install owner/repo
```

Install from a nested GitHub skill directory:

```bash
skill-mgr install owner/repo/skills/demo-skill
```

Validate without installing:

```bash
skill-mgr validate owner/repo/skills/demo-skill --format markdown
```

List skills across bundled adapters:

```bash
skill-mgr list
```

## Development

```bash
make format
make lint
make test
```

The CI workflow currently runs formatting, linting, type-checking, and `pytest` on Windows, Linux, and macOS.
