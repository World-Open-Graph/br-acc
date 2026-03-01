# Security and Compliance — BR/ACC Open Graph

---

## Hard rules (apply to every task — no exceptions)

1. **No secrets in source.** Never hard-code API keys, tokens, passwords, or credentials. Use environment variables; see [.env.example](../.env.example).
2. **No personal identifier exposure.** CPF numbers or any CPF fragment must never appear in API responses. The CPF masking middleware is active on every route — do not bypass or disable it.
3. **Public-safe defaults.** Features behind `PUBLIC_MODE=true` must not expose personal data fields. Mirror server flags in the frontend via `VITE_PUBLIC_MODE`.
4. **No real personal data in demo or test fixtures.** Use only synthetic data (`data/demo/`).
5. **Only public-domain government data sources.** ETL pipelines may only ingest officially published Brazilian government datasets.

---

## Neutrality — banned words in source

The CI neutrality check fails if any of these words appear in `api/src/`, `etl/src/`, or `frontend/src/`:

> `suspicious` · `corrupt` · `criminal` · `fraudulent` · `illegal` · `guilty`

Use neutral, factual language instead: "flagged", "under review", "irregularity", "discrepancy".

---

## Key environment flags

| Variable                      | Purpose                                             | Safe public default |
| ----------------------------- | --------------------------------------------------- | ------------------- |
| `PUBLIC_MODE`                 | Disables personal-data endpoints                    | `true`              |
| `PUBLIC_ALLOW_PERSON`         | Enables person lookup                               | `false`             |
| `PUBLIC_ALLOW_ENTITY_LOOKUP`  | Enables full entity lookup                          | `false`             |
| `PUBLIC_ALLOW_INVESTIGATIONS` | Enables investigations endpoint                     | `false`             |
| `PATTERNS_ENABLED`            | Enables pattern/signal engine                       | `false`             |
| `PRODUCT_TIER`                | Feature tier (`community` / `enterprise`)           | `community`         |
| `JWT_SECRET_KEY`              | Auth signing key — must be ≥ 32 chars in production | —                   |

`PRODUCT_TIER=community` must also be set when running API tests (already set in the CI `env:` block).

---

## Input validation

- All API inputs are validated through Pydantic models — do not bypass them.
- Do not expose internal stack traces or error detail to API consumers; use structured error responses.

---

## Public boundary

The public boundary matrix at [docs/release/public_boundary_matrix.csv](../docs/release/public_boundary_matrix.csv) defines which paths are included in the public release. Do not move internal-only content into public paths without a review.

Notable exclusions from the public repo:

- `api/src/bracc/services/pattern_service.py` — pattern engine, pending validation
- `api/src/bracc/queries/pattern_*.cypher` — pattern queries

---

## LGPD and legal compliance

This project handles publicly released Brazilian government data subject to [LGPD](../LGPD.md). Key boundaries:

- Aggregate and relational data is permissible; individual profiling is not.
- Demo and test data must be fully synthetic (see `data/demo/README.md`).
- Review [docs/legal/public-compliance-pack.md](../docs/legal/public-compliance-pack.md) for any change that touches data ingestion or public endpoints.

---

## Vulnerability reporting

Use GitHub Security Advisories: repository `Security` tab → `Report a vulnerability`. Do not disclose exploit details publicly before triage. See [SECURITY.md](../SECURITY.md) for SLA targets.
