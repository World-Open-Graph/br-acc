# Git Workflow — BR/ACC Open Graph

---

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <short imperative summary>

[optional body]
[optional footer]
```

**Types:** `feat` · `fix` · `docs` · `refactor` · `test` · `ci` · `chore` · `security`
**Scopes:** `api` · `etl` · `frontend` · `infra` · `docs`

Examples:

```
feat(api): add /graph/timeline endpoint for temporal subgraph queries
fix(etl): handle empty CEPIM rows without crashing normalizer
docs: add bilingual release notes for v0.4.0
security(api): rotate JWT signing key validation logic
```

---

## Pull requests

Every PR targeting `main` requires:

1. **Exactly one `release:*` label** — see the [label taxonomy](../docs/release/label_taxonomy.md) for the full list and when to use each.
2. **Bilingual release notes** (PT-BR and EN) — fill in both fields in the PR template.
3. **Full PR template** — [.github/pull_request_template.md](../.github/pull_request_template.md) includes a public safety and compliance checklist; every item must be checked.
4. **Green CI and Security workflow checks** before merge.

### Release label quick reference

| Label              | When to use                                     |
| ------------------ | ----------------------------------------------- |
| `release:major`    | Incompatible public contract or behavior change |
| `release:feature`  | New user-facing capability                      |
| `release:patterns` | New public-safe pattern or signal               |
| `release:api`      | Additive endpoint or schema update              |
| `release:data`     | Data ingestion or model improvement             |
| `release:privacy`  | Public safety or compliance hardening           |
| `release:fix`      | Bug fix with no compatibility break             |
| `release:docs`     | Documentation-only change                       |
| `release:infra`    | CI/CD or deployment change                      |
| `release:security` | Vulnerability or hardening update               |

---

## Versioning

Releases follow **SemVer** (`vMAJOR.MINOR.PATCH`), milestone-based (no fixed cadence):

| Bump    | Trigger                                            |
| ------- | -------------------------------------------------- |
| `MAJOR` | Incompatible public contract change                |
| `MINOR` | Additive feature or new public-safe pattern/signal |
| `PATCH` | Bugfix, docs, security hardening, infra            |

Pre-release suffix: `vMAJOR.MINOR.PATCH-rc.N`

All five release gates must be green before tagging — see [agents_docs/build-and-test.md](build-and-test.md#release-gates).
