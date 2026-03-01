# Release Label Taxonomy

This taxonomy defines release labels used for changelog categorization and version resolution.

## Rule

Every PR targeting `main` must have exactly one release label.

## Labels

| Label | Category | Typical impact | Version tendency |
|---|---|---|---|
| `release:major` | Breaking changes | Public behavior/contract incompatibility | MAJOR |
| `release:feature` | New features | New user-facing capability | MINOR |
| `release:patterns` | New patterns/signals | New public-safe pattern/signal | MINOR |
| `release:api` | API changes | Additive endpoint/schema update | MINOR |
| `release:data` | Data/ETL updates | Data ingestion/model improvements | MINOR |
| `release:privacy` | Privacy/compliance | Public safety/compliance hardening | MINOR |
| `release:fix` | Fixes | Bug fixes without compatibility break | PATCH |
| `release:docs` | Documentation | Docs-only updates | PATCH |
| `release:infra` | Infrastructure | CI/CD/workflow/deployment behavior updates | PATCH |
| `release:security` | Security | Vulnerability or hardening updates | PATCH |

## Excluded labels for release notes

These labels are excluded from public release notes grouping:

- `chore`
- `ci`
- `refactor-internal`
- `no-release-note`

## Examples

- New public endpoint field (backward-compatible): `release:api`
- New community pattern in public tier: `release:patterns`
- Fix timeout fallback bug: `release:fix`
- Breaking response payload rename: `release:major`
