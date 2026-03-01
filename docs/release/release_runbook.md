# Release Runbook

This runbook describes how maintainers publish releases in `World-Open-Graph/br-acc`.

## Preconditions

- Target commit is on `main`.
- Required checks are green.
- PRs merged for the milestone have release labels.
- Draft release content is reviewed.

## 1) Confirm draft notes

1. Open **GitHub -> Releases -> Drafts**.
2. Verify sections and ordering.
3. Ensure PT-BR and EN scope are clear.

## 2) Pick version

Apply SemVer policy:

- MAJOR: incompatible behavior/contract changes.
- MINOR: additive user-facing changes.
- PATCH: compatible fixes.

For validation cycles use RC:

- `vX.Y.Z-rc.N`

## 3) Run publish workflow

1. Open **Actions -> Publish Release**.
2. Click **Run workflow**.
3. Fill inputs:
- `version`: e.g. `v0.3.0`
- `target_sha`: commit SHA on `main`
- `prerelease`: `true` for RC, `false` for stable
- `title_pt`: short PT-BR title
- `title_en`: short EN title
- `highlights_pt`: PT highlights separated by `|`
- `highlights_en`: EN highlights separated by `|`
- `patterns_included`: comma-separated pattern IDs (use `none` when not applicable)
- `technical_changes_pt`: PT technical changes separated by `|`
- `technical_changes_en`: EN technical changes separated by `|`

Example inputs for a pattern release:

- `highlights_pt`: `Port de 8 padrões públicos factuais | Padronização de payload público`
- `highlights_en`: `Port of 8 factual public-safe patterns | Public payload standardization`
- `patterns_included`: `sanctioned_still_receiving,amendment_beneficiary_contracts,split_contracts_below_threshold,contract_concentration,embargoed_receiving,debtor_contracts,srp_multi_org_hitchhiking,inexigibility_recurrence`
- `technical_changes_pt`: `Provider community de 4 para 8 padrões | ETL criou relação Contract-REFERENTE_A-Bid`
- `technical_changes_en`: `Community provider expanded from 4 to 8 patterns | ETL created Contract-REFERENTE_A-Bid linkage`

## 4) Workflow validations performed

The workflow blocks publication when:

- tag is not SemVer-compliant,
- tag already exists,
- target SHA does not exist,
- target SHA is not reachable from `origin/main`.

## 5) Output produced

On success the workflow:

1. Creates and pushes an annotated tag.
2. Creates GitHub Release (PT+EN notes) with explicit highlights, patterns, and technical changes.
3. Uploads `release_manifest.json` asset.

## 6) Post-release checklist

1. Open the release page and confirm:
- version tag is correct,
- PT+EN notes are present,
- included patterns are explicitly listed (or marked as none),
- non-accusatory disclaimer line is present,
- `release_manifest.json` is attached.
2. Share release link in community channels.
3. If stable release follows RC, update milestone board status.

## 7) Rollback guidance

If notes are wrong but code is correct:

- edit release notes in GitHub UI.

If tag points to wrong commit:

1. Delete release,
2. delete remote tag,
3. re-run workflow with correct SHA and same/new version according to policy.
