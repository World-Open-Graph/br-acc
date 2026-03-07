---
description: Automated PR creation workflow for br-acc repository
---

# Automated PR Creation for BR/ACC

This workflow creates a properly formatted pull request with complete template compliance.

## Workflow Execution

### 1. Analyze changes and determine PR metadata
// turbo
```bash
git diff main...HEAD --stat
```

From the changes, determine:
- **Scope**: `api`, `etl`, `frontend`, `infra`, `ci`, or `docs`
- **Type**: `feat`, `fix`, or `docs`
- **Description**: Brief summary (max 72 chars)
- **Release label**: ONE of `release:major`, `release:feature`, `release:patterns`, `release:api`, `release:data`, `release:privacy`, `release:fix`, `release:docs`, `release:infra`, `release:security`

**PR Title Format**: `<type>(<scope>): <description>`

### 2. Generate complete PR description
Construct the PR body following this exact template structure:

```markdown
## Summary

[What changed - technical details]
[Why the change was made - context/problem]
[User/system impact]

## Release metadata

Release note (PT-BR):
[Brief Portuguese description]

Release note (EN):
[Brief English description]

Release highlights (PT-BR, bullets with `|`):
| [Highlight 1 in Portuguese]
| [Highlight 2 in Portuguese]

Release highlights (EN, bullets with `|`):
| [Highlight 1 in English]
| [Highlight 2 in English]

Included pattern IDs (comma-separated, or `none`):
none

Technical changes (PT-BR, bullets with `|`):
| [Technical change 1 in Portuguese]
| [Technical change 2 in Portuguese]

Technical changes (EN, bullets with `|`):
| [Technical change 1 in English]
| [Technical change 2 in English]

Change type (choose one release label from taxonomy):

- [ ] `release:major`
- [ ] `release:feature`
- [ ] `release:patterns`
- [ ] `release:api`
- [ ] `release:data`
- [ ] `release:privacy`
- [x] `release:fix`
- [ ] `release:docs`
- [ ] `release:infra`
- [ ] `release:security`

Breaking change?

- [x] No
- [ ] Yes (describe migration/impact in summary)

## Validation

- [x] Local tests/checks passed for impacted scope
- [x] CI and Security checks are green
- [x] Exactly one release label is set on this PR

## Public safety and compliance checklist

- [x] No personal identifier exposure was introduced
- [x] `PUBLIC_MODE` behavior was reviewed (if relevant)
- [x] Public boundary gate is green
- [x] Public endpoints and demo data contain no personal data fields
- [x] Legal/policy docs were reviewed for scope-impacting changes
- [x] Snapshot boundary remains compliant with `docs/release/public_boundary_matrix.csv`

## Risk and rollback

[Describe key risks]
[Describe rollback procedure]
```

**Critical**: Mark EXACTLY ONE release label with `[x]`. All other checkboxes should be `[ ]` except validation and compliance items which should be `[x]`.

### 3. Create PR
```bash
gh pr create --title "<type>(<scope>): <description>" --body "<complete-pr-body-from-step-2>"
```

### 4. Verify auto-labeling
// turbo
```bash
gh pr view
```

Confirm the auto-labeler applied the correct release label based on the `[x]` selection.

## Critical Requirements

**Title Convention:**
- Format: `<type>(<scope>): <description>`
- Types: `feat`, `fix`, `docs`
- Scopes: `api`, `etl`, `frontend`, `infra`, `ci`, `docs`
- Description: Lowercase, no period, max 72 chars

**Template Compliance:**
- All sections must be filled (no placeholders in brackets)
- Bilingual content required (PT-BR and EN)
- EXACTLY ONE release label checked with `[x]`
- All validation checkboxes marked `[x]`
- All compliance checkboxes marked `[x]`
- Risk and rollback sections completed

**Auto-Labeling:**
The repository's auto-label workflow reads the PR description and:
- Detects which release label is marked with `[x]`
- Automatically applies that label to the PR
- Removes any conflicting release labels
- **Requires exactly one `[x]` selection to function**

## Key Points

**Bilingual Requirements:**
All release metadata must include both Portuguese (PT-BR) and English (EN) versions:
- Release notes
- Release highlights  
- Technical changes

**Release Label Selection:**
Based on repo PR analysis, choose the appropriate label:
- `release:feature` - New features, capabilities, or enhancements
- `release:fix` - Bug fixes and corrections
- `release:docs` - Documentation changes only
- `release:api` - API changes or new endpoints
- `release:data` - Data pipeline or ETL changes
- `release:infra` - Infrastructure or CI/CD changes
- `release:major` - Breaking changes requiring major version bump
- `release:patterns` - Pattern or template updates
- `release:privacy` - Privacy-related changes
- `release:security` - Security improvements
