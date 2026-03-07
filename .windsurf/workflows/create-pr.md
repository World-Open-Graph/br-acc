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

### 3. Preflight GitHub remote and permission setup
Before creating the PR, confirm whether your branch is on the upstream repo or on a fork you can push to.

// turbo
```bash
git remote -v
```

Use this decision rule:
- If you have write access to `World-Open-Graph/br-acc`, push your branch normally and keep using that branch as the PR head.
- If you do **not** have write access to `World-Open-Graph/br-acc`, do **not** push to upstream. Push the branch to your fork and create the PR from `<your-user>:<branch>` into `World-Open-Graph/br-acc`.
- If no fork remote exists yet, create one first with GitHub CLI, add it as a git remote if needed, and push the branch there before opening the PR.

Recommended fork flow when upstream push would 403:
```bash
gh repo fork World-Open-Graph/br-acc --remote-name fork
git push -u fork <branch-name>
```

### 4. Create PR
```bash
gh pr create --repo World-Open-Graph/br-acc --head <owner>:<branch-name> --title "<type>(<scope>): <description>" --body "<complete-pr-body-from-step-2>"
```

Rules for the command:
- Set `<owner>` to `World-Open-Graph` only if the branch exists on upstream and you have push permission there.
- Otherwise set `<owner>` to your GitHub username and use the branch pushed to your fork.
- Always pass `--repo World-Open-Graph/br-acc` so the base repository is explicit.

### 5. Verify PR creation and auto-labeling
// turbo
```bash
gh pr view --repo World-Open-Graph/br-acc
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

**403 Prevention and Fallback:**
- A 403 usually means your GitHub user does not have push permission to `World-Open-Graph/br-acc`
- Avoid that failure by pushing your branch to your fork first and creating the PR with `--repo World-Open-Graph/br-acc --head <your-user>:<branch-name>`
- If the PR is created successfully but the release label is still missing after the workflow runs, verify the body still has exactly one checked release label
- If labeling still does not occur, ask a maintainer with write access to apply the release label manually in GitHub

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
