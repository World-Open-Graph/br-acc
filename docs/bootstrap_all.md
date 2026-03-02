# Bootstrap All

`bootstrap-all` is the heavy reproducibility path for the public repository.

## Commands

```bash
# interactive reset prompt (default)
make bootstrap-all

# noninteractive reset for automation
make bootstrap-all-noninteractive

# print latest summary report
make bootstrap-all-report
```

## What It Does

1. Starts Docker services for Neo4j, API, and frontend.
2. Waits for Neo4j and API health.
3. Prompts whether to reset the local graph (`yes/no`) unless noninteractive flags are set.
4. Loads source contract from `config/bootstrap_all_contract.yml`.
5. Attempts all implemented pipelines in contract order.
6. Continues on errors and classifies outcomes per source.
7. Writes machine/human summaries under `audit-results/bootstrap-all/<UTC_STAMP>/` and copies latest to `audit-results/bootstrap-all/latest/`.

## Prerequisites

- Docker + Docker Compose available locally.
- `.env` present (start from `.env.example`).
- Adequate machine resources for long-running ingestion.
- Optional credentials when required by specific sources (for example `GOOGLE_APPLICATION_CREDENTIALS`).

## Status Model

Per-source terminal status is one of:

- `loaded`
- `blocked_external`
- `blocked_credentials`
- `failed_download`
- `failed_pipeline`
- `skipped`

## Exit Policy

Run exits with non-zero code only when one or more **core** sources fail.
Core sources are defined in `config/bootstrap_all_contract.yml`.

## Report Interpretation

`summary.json` includes:

- `run_id`, `started_at_utc`, `ended_at_utc`
- `full_historical`, `db_reset_used`
- per-source statuses, durations, and remediation hints
- aggregate counts and core failure list

`summary.md` is a compact human-readable table for sharing with community reviewers.
