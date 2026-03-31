# Design Document

## For Multi-agent skill manager

- **Version:** 0.1
- **Author:** Codex
- **Date:** 2026-03-30
- **Status:** Approved

---

## Overview

`skill-mgr` is a standalone Python package and CLI that installs a valid agent skill into one or more supported AI coding agents. The design combines two Orcheo ideas: a generic skill lifecycle surface and a multi-target installer that copies one validated skill directory into several agent-specific locations. The system must stay source-agnostic after resolution, so local directories and GitHub shorthand refs flow through the same validation and install pipeline.

The key design choice is an adapter registry. Core logic should know how to parse refs, validate skills, and orchestrate installs, but it should not hard-code per-agent filesystem rules beyond asking adapters for their destination roots and availability checks. This keeps the initial release focused on `claude`, `codex`, `openclaw`, and `orcheo` while making future adapters incremental rather than invasive.

Windows, Linux, and macOS are all first-class platforms in this design. That does not mean every bundled adapter is guaranteed to support every OS on day one, but it does mean the product must model support explicitly, surface unsupported combinations clearly, and test the shared install engine across all three.

## Components

- **CLI (`skill_mgr.cli` or equivalent)**
  - Exposes `install`, `update`, `uninstall`, `validate`, `list`, and `show`.
  - Normalizes flags, human vs JSON rendering, and exit codes.

- **Source resolver (`skill_mgr.sources`)**
  - Parses input refs into `LocalSource` or `GitHubSource`.
  - Checks for an existing normalized local path before attempting GitHub shorthand parsing.
  - Downloads and safely extracts GitHub archives into a temp directory when needed.
  - Resolves nested repo paths from `owner/repo/path/to/skill`.

- **Skill validator (`skill_mgr.validation`)**
  - Verifies `SKILL.md` exists and is structurally valid.
  - Produces normalized metadata used by install and show operations.

- **Adapter registry (`skill_mgr.adapters`)**
  - Registers supported agent adapters keyed by stable names such as `claude`, `codex`, `openclaw`, and `orcheo`.
  - Resolves `all`, deduplicates repeated targets, and filters unavailable adapters.
  - Stores per-OS install root rules and support metadata for Windows, Linux, and macOS.

- **Install engine (`skill_mgr.services`)**
  - Orchestrates install, update, uninstall, list, and show operations.
  - Reuses a materialized skill directory across all target operations in a single command.

- **Filesystem layer (`skill_mgr.fs`)**
  - Owns safe copy, replace, and delete helpers.
  - Guards against deleting outside adapter-managed roots.

## Request Flows

### Flow 1: Install from local directory to all supported agents

1. User runs `skill-mgr install /path/to/skill`.
2. CLI resolves targets to the agents detected in the current environment because none were passed.
3. Source resolver confirms the input is a directory and returns it unchanged.
4. Validator parses `SKILL.md` and extracts metadata, including the canonical skill name.
5. Adapter registry checks every bundled adapter and marks undetected agents as `skipped_unavailable` with reason `agent_not_detected`.
6. Install engine copies the validated skill directory into each adapter destination root.
7. CLI prints per-target results with statuses such as `installed`, `skipped_unavailable`, or `error`.
8. If a bundled adapter is unsupported on the current OS, the result must include an explicit machine-readable reason.

### Flow 2: Install from GitHub repo shorthand

1. User runs `skill-mgr install owner/repo`.
2. Source resolver parses the ref as GitHub shorthand with no nested path.
3. Resolver fetches the repo archive for the default branch, extracts it safely, and locates the repo root directory.
4. Validator checks that the repo root contains a valid `SKILL.md`.
5. Install engine proceeds exactly as in Flow 1.

### Flow 3: Install from GitHub repo shorthand with nested directory

1. User runs `skill-mgr install owner/repo/path/to/skill`.
2. Source resolver parses `owner` and `repo` from the first two path segments and treats the remainder as `path/to/skill`.
3. Resolver downloads and extracts the default-branch archive.
4. Resolver locates `<extracted-root>/path/to/skill`.
5. Validator checks that the nested directory contains a valid `SKILL.md`.
6. Install engine installs the skill to the resolved targets.

### Flow 4: Update or uninstall for selected targets

1. User runs `skill-mgr update owner/repo -t codex -t claude` or `skill-mgr uninstall my-skill -t codex`.
2. Adapter registry resolves and deduplicates explicit targets.
3. For `update`, source resolution and validation run first, then destination directories are replaced.
4. For `uninstall`, the engine computes the adapter-managed destination path and removes it only if it exists inside the adapter root.
5. CLI renders per-target statuses such as `updated`, `installed`, `uninstalled`, or `not_installed`.

## Platform Support Model

Every bundled adapter must declare one of the following support states for each OS:

- `supported`: install root and behavior are verified and covered by tests on that OS.
- `unsupported`: the agent does not support this OS or `skill-mgr` intentionally does not support it there.
- `unknown`: support has not been verified yet; this state is allowed during development but should not ship in a stable release for bundled adapters.

At runtime, target resolution combines:

1. Adapter support state for the current OS.
2. Environment checks such as home directory resolution and adapter-specific install root detection.
3. User target selection.

This yields a final result per target such as `installed`, `updated`, `skipped_unavailable`, or `error`.

## API Contracts

### CLI Commands

```text
skill-mgr install REF [--target TARGET ...] [--format rich|markdown|json]
skill-mgr update REF [--target TARGET ...] [--format rich|markdown|json]
skill-mgr uninstall NAME [--target TARGET ...] [--format rich|markdown|json]
skill-mgr validate REF [--format rich|markdown|json]
skill-mgr list [--target TARGET ...] [--format rich|markdown|json]
skill-mgr show NAME [--target TARGET ...] [--format rich|markdown|json]
```

### Target result statuses

```text
installed
updated
uninstalled
not_installed
skipped_unavailable
error
```

`skipped_unavailable` must include a reason, for example:
- `unsupported_os`
- `unknown_install_root`
- `agent_not_detected`

### Source ref contract

```text
REF := LOCAL_PATH | GITHUB_SHORT_REF
GITHUB_SHORT_REF := OWNER "/" REPO ["/" SUBPATH]
```

Rules:
- `OWNER` and `REPO` are the first two path segments.
- `SUBPATH`, when present, may contain one or more additional segments.
- `owner/repo` means the skill lives at the repository root.
- `owner/repo/dir` or `owner/repo/path/to/dir` means the skill lives under that nested directory.
- After home expansion and path normalization, an existing local path takes precedence over GitHub shorthand parsing.
- Omitting `--target` means "use detected bundled agents in the current environment".
- Explicit `all` expands to every bundled adapter, even if some are not detected in the current environment.
- `all` is mutually exclusive with explicit non-`all` targets; mixed usage must be rejected before service execution.

### Service contract: install/update result

```json
{
  "skill": "example-skill",
  "action": "install",
  "source": {
    "kind": "github",
    "ref": "owner/repo/path/to/skill",
    "repository": "owner/repo",
    "subpath": "path/to/skill"
  },
  "targets": [
    {
      "target": "codex",
      "path": "/home/user/.codex/skills/example-skill",
      "status": "installed",
      "message": null
    }
  ]
}
```

### Service contract: list

```json
{
  "target": "claude",
  "skills": [
    {
      "name": "example-skill",
      "description": "Example description",
      "path": "/home/user/.claude/skills/example-skill",
      "status": "installed"
    }
  ]
}
```

### Service contract: show

```json
{
  "name": "example-skill",
  "targets": [
    {
      "target": "claude",
      "path": "/home/user/.claude/skills/example-skill",
      "status": "installed",
      "metadata": {
        "name": "example-skill",
        "description": "Example description"
      }
    },
    {
      "target": "codex",
      "path": null,
      "status": "not_installed",
      "metadata": null
    }
  ]
}
```

### Service contract: validate

Success:

```json
{
  "ref": "owner/repo/path/to/skill",
  "source": {
    "kind": "github",
    "repository": "owner/repo",
    "subpath": "path/to/skill"
  },
  "valid": true,
  "skill": {
    "name": "example-skill",
    "description": "Example description"
  },
  "errors": []
}
```

Failure:

```json
{
  "ref": "owner/repo/path/to/skill",
  "source": {
    "kind": "github",
    "repository": "owner/repo",
    "subpath": "path/to/skill"
  },
  "valid": false,
  "skill": null,
  "errors": [
    {
      "code": "missing_skill_md",
      "message": "Resolved directory does not contain SKILL.md."
    }
  ]
}
```

### Shared top-level error contract

Source-resolution failures that occur before a validated skill directory exists should abort the command and return a top-level error rather than synthetic per-target statuses. This applies to shared GitHub download failures such as timeouts, 404s, and rate limiting.

```json
{
  "error": {
    "code": "github_rate_limited",
    "message": "GitHub archive download failed before target processing began."
  }
}
```

## Data Models / Schemas

### `GitHubSourceSpec`

| Field | Type | Description |
|-------|------|-------------|
| owner | string | GitHub owner or organization |
| repo | string | GitHub repository name |
| subpath | string \| null | Nested directory containing the skill |
| display_ref | string | Original user ref |

### `AgentAdapter`

| Field | Type | Description |
|-------|------|-------------|
| name | string | Stable target name used by CLI |
| support_by_os | dict[str, string] | Per-OS support state keyed by `windows`, `linux`, and `macos` |
| install_root_by_os | dict[str, string \| null] | Platform-specific install root template or null when unsupported |
| install_root | Path \| null | Runtime-resolved install root for the current OS, derived from `install_root_by_os[current_os]` after environment expansion |
| available | bool | Whether the adapter is usable on the current machine |
| availability_reason | string \| null | Explanation when unavailable |

### `TargetResult`

| Field | Type | Description |
|-------|------|-------------|
| target | string | Adapter name |
| path | string | Final skill path for this target |
| status | string | `installed`, `updated`, `uninstalled`, `not_installed`, `skipped_unavailable`, or `error` |
| source | string \| null | Original source ref for install/update operations |
| message | string \| null | Optional detail for warnings or failures |

### Adapter OS support metadata

| Field | Type | Description |
|-------|------|-------------|
| windows | string | `supported`, `unsupported`, or `unknown` |
| linux | string | `supported`, `unsupported`, or `unknown` |
| macos | string | `supported`, `unsupported`, or `unknown` |
| install_root_by_os | dict[str, str \| null] | Platform-specific install root template or null when unsupported; this is the source of truth used to derive `AgentAdapter.install_root` |

### Initial adapter matrix

The initial release should maintain a published matrix for bundled adapters:

| Adapter | Windows | Linux | macOS | Notes |
|---------|---------|-------|-------|-------|
| `claude` | To verify | To verify | To verify | Must not claim support until install root is confirmed per OS |
| `codex` | To verify | To verify | To verify | Must not claim support until install root is confirmed per OS |
| `openclaw` | To verify | To verify | To verify | Must not claim support until install root is confirmed per OS |

Before alpha release, each `To verify` cell should become `supported` or `unsupported`.

## Security Considerations

- Reject archive members that escape the extraction root or contain symlinks/hardlinks.
- Validate before installation so malformed skills are never copied into agent roots.
- Scope delete operations to adapter-managed roots to avoid arbitrary filesystem removal.
- Sanitize GitHub shorthand parsing and refuse empty owner, repo, or subpath segments.
- Avoid logging secrets or authentication headers if authenticated GitHub access is added later.
- Handle Windows path normalization carefully so adapter-root containment checks cannot be bypassed through drive-letter or separator differences.
- Surface GitHub archive download failures as top-level command errors with stable codes such as `github_not_found`, `github_timeout`, or `github_rate_limited`; do not emit partial per-target results when source resolution fails before installation starts.

## Performance Considerations

- Download the GitHub archive once per command and reuse it across all targets.
- Avoid repeated validation per target; validate the materialized source directory once.
- Keep directory copies simple and deterministic for the first release; parallel target installs can remain a future optimization if copy cost becomes significant.
- `list` and `show` should inspect adapter roots directly without network calls.
- Platform branches should stay inside adapters; the core engine should not accumulate scattered OS-specific conditionals.

## Testing Strategy

- **Unit tests**: GitHub shorthand parser, target normalization, adapter availability handling, safe extraction guards, and result shaping.
- **Integration tests**: temp-home installs for each bundled adapter, update/install status transitions, uninstall boundaries, and GitHub archive resolution with mocked HTTP responses on Windows, Linux, and macOS.
- **Manual QA checklist**: install from local path, install from `owner/repo`, install from `owner/repo/path`, install to `all`, install to selected targets, update existing installs, uninstall absent installs, unsupported-target reporting, and human-readable output on all three OSes.

## Rollout Plan

1. Implement the adapter registry and local-directory install path first.
2. Add GitHub shorthand resolution with secure archive extraction and nested path support.
3. Add list/show/uninstall coverage and fixture-backed adapter tests.
4. Publish an alpha release documenting the initial agent matrix, the meaning of `all`, and the OS support status for each bundled adapter.

Include a compatibility note in release docs that supported targets are defined by bundled adapters in the current version, not by a remote registry.

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-03-30 | Codex | Initial draft |
