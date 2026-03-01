# Release Policy (Milestone-Based, SemVer, PT+EN)

This policy defines how releases are published in `World-Open-Graph/br-acc`.

## Goals

- Keep a clear and auditable public history of changes.
- Use a stable, AI-friendly version format.
- Keep release communication bilingual (PT-BR and EN).
- Publish only after validation gates are green.

## Cadence

Releases are milestone-based (`por marco`).

A release is published when a meaningful package of user-facing changes is complete.

## Versioning

Tags must follow SemVer with optional release-candidate suffix:

- Stable: `vMAJOR.MINOR.PATCH`
- Pre-release: `vMAJOR.MINOR.PATCH-rc.N`

Examples:

- `v0.3.0`
- `v0.3.1-rc.1`

## Version bump rules

- `MAJOR`: incompatible public contract or behavior changes.
- `MINOR`: additive user-facing features or new public-safe signals/patterns.
- `PATCH`: backward-compatible fixes (bugfix/docs/security/infra).

## Mandatory release gates

A release can only be published from a commit on `main` where all required gates are green:

- CI workflow
- Security workflow
- Public privacy gate
- Compliance pack gate
- Public boundary gate (in public repo)

## Release notes standard

Every release must include PT-BR and EN sections with:

1. Scope summary.
2. Notable changes.
3. Compatibility/breaking notes.
4. Privacy/compliance notes when applicable.
5. Non-accusatory disclaimer.

## Artifacts

Each release must contain:

- Git tag (SemVer compliant).
- GitHub Release notes.
- `release_manifest.json` asset for machine-readable change summaries.

## Label policy for PRs

Every PR targeting `main` must contain exactly one release label from the release taxonomy.

This label is used for release drafting and version resolution.

## Historical tags

Historical tags remain intact:

- `v0.1.0-public-alpha`
- `v0.2.0-pre-deploy`

Policy-compliant stream starts at `v0.3.0`.
