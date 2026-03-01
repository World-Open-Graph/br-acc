# LGPD BASELINE POLICY — World Transparency Graph (WTG)

Policy-Version: v1.0.0  
Effective-Date: 2026-02-28  
Owner: WTG Governance Team

## Legal basis posture

WTG is operated with a public-interest and transparency posture for analysis of publicly available records, with strict minimization and access controls.

This baseline is operational guidance and does not replace formal legal advice.

## Data categories and exclusions

Data categories processed in this public repository:

- Company records and corporate relationships.
- Public procurement and public finance records.
- Publicly disclosed sanctions and regulatory actions.
- Public legislative and administrative records.

Default exclusions in public mode:

- Person-level lookup and personal identifier exposure.
- `Person` and `Partner` entities in public responses.
- Personal document properties such as CPF and partial document fields.

## Data subject rights workflow

Rights requests (access, correction, deletion review) are handled through GitHub issue templates:

- Privacy request.
- Data correction request.

Required handling steps:

- Register timestamp and case ID.
- Verify request scope and source evidence.
- Produce a decision log with rationale.

## Retention and deletion principles

Retention follows operational necessity and legal obligations:

- Keep only the minimum needed for platform operation, security, and abuse response.
- Avoid retaining unnecessary personal data in public-facing flows.
- Apply correction/removal actions in the next published snapshot cycle when approved.

## Cross-border processing note

WTG may process infrastructure and collaboration workflows across jurisdictions.  
Brazil-first LGPD posture remains mandatory for datasets and outputs related to Brazil.

See [PRIVACY.md](PRIVACY.md), [TERMS.md](TERMS.md), and [docs/legal/legal-index.md](docs/legal/legal-index.md).
