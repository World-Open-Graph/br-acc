# Public Repo Release Checklist — World Transparency Graph

## 1) Prepare sanitized snapshot
```bash
bash scripts/prepare_public_snapshot.sh /Users/brunoclz/CORRUPTOS /tmp/world-transparency-graph-public
```

## 2) Initialize clean-history repo from snapshot
```bash
cd /tmp/world-transparency-graph-public
git init
git add .
git commit -m "Initial public release (WTG)"
```

## 3) Create GitHub repository (manual)
- Owner: `brunoclz`
- Name: `world-transparency-graph`
- Visibility: Public
- Do not auto-add README/License (already present)

## 4) Push initial release
```bash
git branch -M main
git remote add origin https://github.com/brunoclz/world-transparency-graph.git
git push -u origin main
```

## 5) Configure branch protection (GitHub UI)
Require all checks:
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

## 6) Configure environment defaults
- Set public deployment environment vars:
  - `PRODUCT_TIER=community`
  - `PUBLIC_MODE=true`
  - `PUBLIC_ALLOW_PERSON=false`
  - `PUBLIC_ALLOW_ENTITY_LOOKUP=false`
  - `PUBLIC_ALLOW_INVESTIGATIONS=false`
  - `PATTERNS_ENABLED=false`
  - `VITE_PUBLIC_MODE=true`
  - `VITE_PATTERNS_ENABLED=false`

## 7) Final checks before launch
- `python scripts/check_public_privacy.py --repo-root .` => `PASS`
- `python scripts/check_compliance_pack.py --repo-root .` => `PASS`
- `python scripts/check_open_core_boundary.py --repo-root .` => `PASS`
- Confirm no internal runbooks in public repo
- Confirm demo data is synthetic (`data/demo/synthetic_graph.json`)
- Confirm all legal docs exist in root:
  - `ETHICS.md`
  - `LGPD.md`
  - `PRIVACY.md`
  - `TERMS.md`
  - `DISCLAIMER.md`
  - `SECURITY.md`
  - `ABUSE_RESPONSE.md`

## 8) Launch communication split
- Publish product announcement as **WTG**
- Publish movement announcement as **BRCC**
- Mention methodology limits and non-accusatory policy

## 9) Release system bootstrap
- Ensure `.github/release.yml` exists for auto-notes categories.
- Ensure `.github/release-drafter.yml` + workflow are active.
- Ensure `publish-release.yml` workflow is present and dispatchable.
- Ensure release label taxonomy is documented and applied to PRs.
- Publish first policy-compliant tag from this stream (`v0.3.0`).
