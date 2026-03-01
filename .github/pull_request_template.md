## Summary

Describe what changed and why.

## Release metadata

Release note (PT-BR):

Release note (EN):

Release highlights (PT-BR, bullets with `|`):

Release highlights (EN, bullets with `|`):

Included pattern IDs (comma-separated, or `none`):

Technical changes (PT-BR, bullets with `|`):

Technical changes (EN, bullets with `|`):

Change type (choose one release label from taxonomy):

- [ ] `release:major`
- [ ] `release:feature`
- [ ] `release:patterns`
- [ ] `release:api`
- [ ] `release:data`
- [ ] `release:privacy`
- [ ] `release:fix`
- [ ] `release:docs`
- [ ] `release:infra`
- [ ] `release:security`

Breaking change?

- [ ] No
- [ ] Yes (describe migration/impact in summary)

## Validation

- [ ] Local tests/checks passed for impacted scope
- [ ] CI and Security checks are green
- [ ] Exactly one release label is set on this PR

## Public safety and compliance checklist

- [ ] No personal identifier exposure was introduced
- [ ] `PUBLIC_MODE` behavior was reviewed (if relevant)
- [ ] Public boundary gate is green
- [ ] Public endpoints and demo data contain no personal data fields
- [ ] Legal/policy docs were reviewed for scope-impacting changes
- [ ] Snapshot boundary remains compliant with `docs/release/public_boundary_matrix.csv`

## Risk and rollback

Describe key risks and how to roll back if needed.
