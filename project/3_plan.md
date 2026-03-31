# Project Plan

## For Multi-agent skill manager

- **Version:** 0.1
- **Author:** Codex
- **Date:** 2026-03-30
- **Status:** Approved

---

## Overview

Plan to build `skill-mgr` as an independent multi-agent skill installer with an adapter registry, GitHub shorthand source resolution, and a CLI modeled after the Orcheo skill workflows. This plan depends on the requirements and design documents in `project/`.

**Related Documents:**
- Requirements: `project/1_requirements.md`
- Design: `project/2_design.md`

---

## Milestones

### Milestone 1: Product framing and skeleton

**Description:** Lock the command surface, data model boundaries, and package structure before implementation starts.

#### Task Checklist

- [x] Task 1.1: Draft and review the requirements document
  - Dependencies: None
- [x] Task 1.2: Draft and review the design document
  - Dependencies: Task 1.1
- [x] Task 1.3: Confirm Windows, Linux, and macOS support expectations for each initial adapter and publish the initial OS support matrix
  - Dependencies: Task 1.2
- [x] Task 1.4: Document the `SKILL.md` format contract, including required fields and the checks enforced by `validate`
  - Dependencies: Task 1.1, Task 1.2
- [x] Task 1.5: Create the package/module skeleton for CLI, adapters, sources, validation, and services
  - Dependencies: Task 1.2

---

### Milestone 2: Core install engine and adapters

**Description:** Implement the local install path and the multi-agent adapter abstraction.

#### Task Checklist

- [x] Task 2.1: Implement the adapter registry with bundled `claude`, `codex`, and `openclaw` adapters
  - Dependencies: Milestone 1
- [x] Task 2.2: Encode per-OS install roots, support states, and runtime availability mapping inside each bundled adapter
  - Dependencies: Task 2.1
- [x] Task 2.3: Implement local directory validation and install/update/uninstall services
  - Dependencies: Task 1.4, Task 2.1, Task 2.2
- [x] Task 2.4: Implement CLI commands and human/JSON output rendering, including explicit unsupported-OS messaging
  - Dependencies: Task 2.3
- [x] Task 2.5: Add unit and temp-home integration tests for local installs across bundled adapters on Windows, Linux, and macOS
  - Dependencies: Task 2.1, Task 2.2, Task 2.3, Task 2.4

---

### Milestone 3: GitHub shorthand source support

**Description:** Add `owner/repo` and `owner/repo/path` resolution with secure archive handling.

#### Task Checklist

- [x] Task 3.1: Implement GitHub shorthand parsing into owner, repo, and optional nested path
  - Dependencies: Milestone 2
- [x] Task 3.2: Implement archive download, safe extraction, and materialized source resolution
  - Dependencies: Task 3.1
- [x] Task 3.3: Add tests for repo-root and nested-path install flows, including invalid archive and invalid subpath cases, on Windows, Linux, and macOS
  - Dependencies: Task 3.2
- [x] Task 3.4: Document GitHub shorthand behavior, default-branch assumptions, and platform support semantics in README or docs
  - Dependencies: Task 3.3

---

### Milestone 4: Inventory commands and release hardening

**Description:** Complete the lifecycle feature set and prepare the first public alpha.

#### Task Checklist

- [x] Task 4.1: Implement `list` and `show` across one or more selected targets
  - Dependencies: Milestone 2
- [x] Task 4.2: Audit bundled adapters for release-ready availability metadata and confirm alpha docs match the implemented platform-skip behavior
  - Dependencies: Task 2.5, Task 3.4
- [x] Task 4.3: Add CI jobs for Windows, Linux, and macOS with the relevant lint and test commands
  - Dependencies: Milestone 3, Task 4.1, Task 4.2
- [x] Task 4.4: Run lint, format, and the relevant test suite in CI-parity commands across all three operating systems
  - Dependencies: Milestone 3, Task 4.1, Task 4.2, Task 4.3
- [x] Task 4.5: Cut an alpha release and publish the initial supported-agent and OS support matrix
  - Dependencies: Task 4.4

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-03-30 | Codex | Initial draft |
