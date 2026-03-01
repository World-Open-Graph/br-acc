# Public Repo Release Checklist — `World-Open-Graph/br-acc`

## 1) Pre-release gate

1. Confirm target merge commit exists on `main`.
2. Confirm CI + Security + Public gates are green on that commit.
3. Confirm PR is merged with exactly one release label.

## 2) Public boundary checks

```bash
python scripts/check_public_privacy.py --repo-root .
python scripts/check_compliance_pack.py --repo-root .
python scripts/check_open_core_boundary.py --repo-root .
```

Expected: all `PASS`.

## 3) Snapshot hygiene (optional verification)

```bash
bash scripts/prepare_public_snapshot.sh . /tmp/br-acc-public
python /tmp/br-acc-public/scripts/check_public_privacy.py --repo-root /tmp/br-acc-public
python /tmp/br-acc-public/scripts/check_compliance_pack.py --repo-root /tmp/br-acc-public
python /tmp/br-acc-public/scripts/check_open_core_boundary.py --repo-root /tmp/br-acc-public
```

Expected in snapshot:

- No `CLAUDE.md`.
- No `AGENTS.md` or `AGENTS*.md`.
- No private operational runbooks outside public scope.

## 4) Publish release (manual workflow)

In GitHub Actions, run **Publish Release** with:

- `version`: SemVer tag (e.g. `v0.3.0`, `v0.3.1-rc.1`)
- `target_sha`: merge commit on `main`
- `prerelease`: `false` (stable) or `true` (RC)
- `title_pt`: release title PT-BR
- `title_en`: release title EN

## 5) Verify outputs

1. Tag exists in repository.
2. Release page published under `/releases`.
3. Notes include PT+EN and non-accusatory disclaimer.
4. `release_manifest.json` asset is attached.
5. Compare link is valid (`previous_tag...new_tag`).

## 6) Community communication

1. Use `docs/release/community_announcement_template.md`.
2. Publish short PT+EN summary with release URL.
3. Keep wording factual: “signals/co-occurrence”, never accusatory language.
