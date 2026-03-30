# Requirements Document

## METADATA
- **Authors:** Codex
- **Project/Feature Name:** Multi-agent skill manager
- **Type:** Product
- **Summary:** Build a standalone CLI and library that installs, updates, validates, lists, and uninstalls agent skills across multiple coding agents from one command surface.
- **Owner (if different than authors):** ShaojieJiang
- **Date Started:** 2026-03-30

## RELEVANT LINKS & STAKEHOLDERS

| Documents | Link | Owner | Name |
|-----------|------|-------|------|
| Prior Artifacts | [Orcheo standalone skill installer](https://github.com/ShaojieJiang/orcheo/blob/main/packages/sdk/src/orcheo_sdk/cli/orcheo_skill.py) | Eng | `orcheo-skill` CLI |
| Prior Artifacts | [Orcheo external-agent install service](https://github.com/ShaojieJiang/orcheo/blob/main/packages/sdk/src/orcheo_sdk/services/orcheo_skill.py) | Eng | Multi-target install/update/uninstall flow |
| Prior Artifacts | [Orcheo generic skill CLI](https://github.com/ShaojieJiang/orcheo/blob/main/packages/sdk/src/orcheo_sdk/cli/skill.py) | Eng | Skill lifecycle command surface |
| Prior Artifacts | [Orcheo generic skill service](https://github.com/ShaojieJiang/orcheo/blob/main/packages/sdk/src/orcheo_sdk/services/skills.py) | Eng | Skill install/list/show/validate service layer |
| Design Review | [project/agent_skill_manager/2_design.md](./2_design.md) | Eng | Multi-agent skill manager design |
| Plan | [project/agent_skill_manager/3_plan.md](./3_plan.md) | Eng | Multi-agent skill manager plan |

## PROBLEM DEFINITION
### Objectives
Provide one standalone skill manager that installs a valid agent skill into all supported coding agents by default, while still allowing users to target a subset of agents explicitly. Make GitHub-based installs ergonomic by accepting shorthand refs in `owner/repo` and `owner/repo/path` form, and treat Windows, Linux, and macOS as first-class user platforms.

### Target users
- Developers who use more than one AI coding agent and want one command to keep skills synchronized.
- Skill authors who want to document a single installation flow instead of separate per-agent instructions.
- Tool maintainers who need a reusable library for agent-specific skill installation behavior.

### User Stories
| As a... | I want to... | So that... | Priority | Acceptance Criteria |
|---------|--------------|------------|----------|---------------------|
| Developer using multiple agents | Run one install command without passing targets | The skill is installed for every supported agent on my machine | P0 | `install` resolves `all` by default and reports per-target results |
| Developer using one agent | Pass one or more `--target` values | I only install into the agents I actually use | P0 | Repeated `--target` flags install only for the selected adapters |
| Skill author | Publish install instructions using `owner/repo` | Users can install from GitHub without copying clone URLs or tarball URLs | P0 | GitHub shorthand resolves and installs from the repo root when `SKILL.md` exists there |
| Skill author with mono-repo skills | Publish install instructions using `owner/repo/path/to/skill` | Users can install a nested skill directory from a repo that contains multiple skills | P0 | GitHub shorthand with a trailing path resolves the nested directory and validates `SKILL.md` there |
| Maintainer | Add support for another agent without rewriting the install pipeline | The project can grow to support more agents cleanly | P1 | New agent support is implemented by adding one adapter and tests |
| Developer updating a skill | Run `update` against all supported agents | Installed copies are replaced consistently | P1 | Update reuses source resolution once and reports installed vs updated status per target |
| Developer removing a skill | Run `uninstall <name>` with optional targets | I can remove one skill from all or some agents | P1 | Uninstall reports `uninstalled` or `not_installed` per target |

### Context, Problems, Opportunities
Orcheo already demonstrates two useful ideas: a generic local skill manager and a focused installer that copies one official skill into multiple agents. The gap is that the current behavior is product-specific and limited to a small hard-coded target set. A standalone `skill-mgr` can generalize that pattern into an independent package that works for any valid skill source, resolves friendly GitHub shorthands, and installs into a growing list of agent ecosystems through a shared adapter model.

### Product goals and Non-goals
Goals:
- Match the mental model of `orcheo skill` and `orcheo-skill`, but make it product-agnostic.
- Default to installing, updating, and uninstalling across all supported agents.
- Support explicit target selection per command.
- Support GitHub shorthand refs in `owner/repo` and `owner/repo/path` form.
- Treat Windows, Linux, and macOS as first-class supported operating systems for the core product surface.
- Keep the implementation extensible so new agent adapters can be added without changing core install logic.

Non-goals:
- Building a hosted registry or marketplace.
- Converting skill formats between incompatible agent ecosystems.
- Supporting arbitrary Git hosting providers in the first release.
- Managing agent application installation, upgrades, or authentication.

## PRODUCT DEFINITION
### Requirements
P0 requirements:
- Provide CLI commands for `install`, `update`, `uninstall`, `validate`, `list`, and `show`.
- `install` and `update` must accept a source reference that can be:
  - a local directory path containing `SKILL.md`
  - a GitHub shorthand in `owner/repo` form
  - a GitHub shorthand in `owner/repo/path/to/skill` form
- `install`, `update`, and `uninstall` must accept repeated `--target` / `-t` flags.
- When no targets are provided, the command must behave as if `--target all` were passed.
- `all` must resolve dynamically to every adapter bundled by the running version of the package.
- Initial bundled adapters must cover `claude`, `codex`, and `openclaw`.
- Each bundled adapter must declare its support status on Windows, Linux, and macOS.
- The CLI must report whether a target is unavailable because the adapter is unsupported on the current OS, the agent install root is unknown, or the local environment is missing required directories.
- The installer must validate the selected skill directory before copying it into any target.
- Each command must return structured per-target results including target name, destination path, and status.
- The CLI must expose both machine-readable output and a human-readable table view.
- GitHub shorthand parsing must treat the first two path segments as `owner` and `repo`, with the remaining suffix interpreted as the nested skill directory path.
- Path resolution and filesystem operations must work correctly on Windows, Linux, and macOS, including home-directory expansion and platform-native path separators.

P1 requirements:
- Allow adapters to declare platform-specific availability and skip unsupported targets with a clear status.
- Deduplicate repeated targets and normalize case.
- Reuse one downloaded archive for all targets in a single invocation.
- Offer a library API mirroring the CLI operations so external tools can embed `skill-mgr`.
- Add automated integration coverage for Windows, Linux, and macOS for the shared install engine and any adapter whose install root is defined on that OS.

P2 requirements:
- Support richer GitHub refs such as explicit branch, tag, or commit selection.
- Support custom adapter discovery from configuration or plugins.

### Designs (if applicable)
Not a UI project. See [project/agent_skill_manager/2_design.md](./2_design.md) for the system design and CLI contract.

### Other Teams Impacted
- Documentation: install instructions for skills can become shorter and agent-agnostic.
- Skill authors: repository layout guidance should document when to use repo root vs nested directory shorthand.
- Release engineering: adapter support must be versioned and documented per release.

## TECHNICAL CONSIDERATIONS
### Architecture Overview
The system should separate source resolution, skill validation, agent target resolution, and filesystem installation into distinct components. The central workflow is: parse ref, materialize a local validated skill directory, resolve targets from an adapter registry, then copy the skill into each target root and report per-target status.

### Technical Requirements
- Use an adapter registry so each supported agent owns its install root, naming rules, and platform checks.
- Preserve secure archive extraction behavior for GitHub downloads: reject path traversal, symlinks, and unexpected archive layouts.
- Keep skill validation independent of source type so local and GitHub installs share the same rules.
- Prevent partial corruption by copying into agent-specific destination directories atomically where practical.
- Ensure uninstall only deletes directories inside registered agent skill roots.
- Keep path handling home-directory aware and cross-platform safe.
- Document adapter install roots and support level per OS so users can tell whether `all` on their machine means supported, skipped, or unknown for each target.

### AI/ML Considerations (if applicable)
Not applicable.

## MARKET DEFINITION
This is an open-source developer tool for users who work across multiple AI coding agents. The primary addressable audience is developers and teams adopting reusable agent skills but frustrated by fragmented install instructions and duplicated setup work.

## LAUNCH/ROLLOUT PLAN

### Success metrics
| KPIs | Target & Rationale |
|------|--------------------|
| Install coverage | First release supports at least 3 production-ready agent adapters with declared Windows/Linux/macOS support status |
| Default install success | `install` with no targets succeeds across all available local adapters in fixture-based integration tests |
| GitHub shorthand success | Both `owner/repo` and `owner/repo/path` flows pass integration coverage |
| Platform coverage | Shared install/update/uninstall flows pass CI on Windows, Linux, and macOS |
| Author usability | Skill README install instructions can be reduced to one command template |

### Rollout Strategy
Release in three stages: internal dogfooding with fixture-backed tests, a public alpha with the initial adapter set, then broader adoption once adapter path conventions and edge cases are validated on Windows, Linux, and macOS.

### Experiment Plan (if applicable)
Not applicable.

### Estimated Launch Phases (if applicable)
| Phase | Target | Description |
|-------|--------|-------------|
| **Phase 1** | Internal maintainers | Validate adapter abstractions and GitHub shorthand parsing with temp-home integration tests on Windows, Linux, and macOS |
| **Phase 2** | Early OSS users | Ship alpha release with `claude`, `codex`, and `openclaw` adapters plus a published OS support matrix |
| **Phase 3** | General availability | Add more bundled adapters after confirming stable per-OS install roots and backward compatibility |

## HYPOTHESIS & RISKS
Hypothesis: users managing skills across multiple agents will prefer one default multi-target install flow over agent-specific instructions, and shorthand GitHub refs will materially reduce installation friction. Confidence is moderate because Orcheo already shows demand for multi-target installation, but generalizing to more agents introduces more path and compatibility variance.

Risks:
- Some agents may not have stable or well-documented skill install roots.
- GitHub shorthand without explicit ref selection may surprise users when default branches change.
- Nested repo paths may be ambiguous if a repo contains multiple `SKILL.md` files.
- Windows-specific filesystem semantics may differ from Linux and macOS in ways that break assumptions about permissions, separators, or replacement behavior.

Risk mitigation:
- Ship adapters only when their install locations are verified and testable.
- Make default-branch behavior explicit in CLI output and docs.
- Require the nested path to resolve to exactly one directory containing `SKILL.md`.
- Require cross-platform CI for shared install logic and mark adapters as unsupported instead of guessing on an unverified OS.

## APPENDIX
None.
