# Public Compliance Pack (WTG Open)

## 1. Data minimization baseline
- Public mode defaults:
  - `PUBLIC_MODE=true`
  - `PUBLIC_ALLOW_PERSON=false`
  - `PUBLIC_ALLOW_ENTITY_LOOKUP=false`
  - `PUBLIC_ALLOW_INVESTIGATIONS=false`
- Public endpoints are company-only and aggregated.

## 2. LGPD-compatible operating principles
- Purpose limitation: investigative transparency and civic oversight.
- Data minimization: no person-level lookup in public surface.
- Security by design: least-privilege runtime and auditable controls.
- Transparency: source attribution and coverage caveats on every report.

## 3. Public terms of use requirements
- Tool presents connections in public records, not legal conclusions.
- Users cannot use the platform for harassment or doxxing.
- Abuse patterns trigger throttling and access restrictions.

## 4. Correction and takedown policy
- Accept correction requests with source evidence.
- Record decision logs with timestamp and rationale.
- Propagate approved corrections to next published snapshot.

## 5. Abuse response playbook
- Enforce strict rate limiting in public mode.
- Retain request logs for abuse analysis in legal window.
- Block abusive clients and rotate keys/tokens when needed.

## 6. Mandatory legal review gates before launch
- RIPD/DPIA draft reviewed by legal counsel.
- Terms of Use published.
- Public communication includes limitation statement.
