# CI Baseline (March 2026)

Snapshot date: 2026-03-01  
Repository: `World-Open-Graph/br-acc`

## Workflow inventory

- `CI`
- `Security`
- `Deploy`
- `Release Drafter`
- `Release Label Policy`
- `Publish Release`
- `Claude PR Governor`

## Trigger matrix

| Workflow | Trigger |
|---|---|
| `CI` | `push` on `main`, `pull_request` to `main` |
| `Security` | `push` on `main`, `pull_request` to `main` |
| `Deploy` | `workflow_run` after `CI` completion on `main` |
| `Release Drafter` | `push` on `main` |
| `Release Label Policy` | `pull_request_target` for PR label enforcement |
| `Publish Release` | `workflow_dispatch` |
| `Claude PR Governor` | `pull_request` lifecycle events to `main` |

## Required status checks (branch protection)

Branch protection on `main` is strict (`strict=true`) and currently requires:

- `API (Python)`
- `ETL (Python)`
- `Frontend (TypeScript)`
- `Neutrality Audit`
- `Gitleaks`
- `Bandit (Python)`
- `Pip Audit (Python deps)`
- `Public Privacy Gate`
- `Compliance Pack Gate`
- `Public Boundary Gate`

## Last-40-runs summary

Data source: `gh run list --repo World-Open-Graph/br-acc --limit 40`

| Workflow | Count | Avg duration | Median duration | Min | Max |
|---|---:|---:|---:|---:|---:|
| `CI` | 9 | 406.1s | 59.0s | 31.0s | 870.0s |
| `Security` | 9 | 403.4s | 61.0s | 26.0s | 866.0s |
| `Claude PR Governor` | 7 | 36.0s | 35.0s | 21.0s | 53.0s |
| `Release Label Policy` | 11 | 6.4s | 7.0s | 4.0s | 8.0s |
| `Release Drafter` | 2 | 9.5s | 10.0s | 9.0s | 10.0s |
| `Deploy` | 2 | 1.0s | 1.0s | 1.0s | 1.0s |

Note: CI/Security averages are skewed by outlier runs; medians better represent normal runtime.

## Top failing job pattern

Sampled from the latest 15 `CI` runs:

- Failing CI runs: `1`
- Most frequent failing job: `Frontend (TypeScript)` (`1` occurrence)

## Optimization objective

Improve PR feedback speed without reducing coverage:

- keep `CI` and `Security` separate,
- keep full checks on PRs,
- preserve existing required check names.
