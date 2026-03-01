# br/acc open graph

[![WTG Header](docs/brand/bracc-header.png)](docs/brand/bracc-header.png)

[English](README.md) | [Portugues](docs/pt-BR/README.md)

**Open-source graph infrastructure that cross-references Brazil's public databases to generate actionable intelligence for civic improvement.**

[![CI](https://github.com/brunoclz/world-transparency-graph/actions/workflows/ci.yml/badge.svg)](https://github.com/brunoclz/world-transparency-graph/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Last Commit](https://img.shields.io/github/last-commit/brunoclz/world-transparency-graph)](https://github.com/brunoclz/world-transparency-graph/commits)
[![Issues](https://img.shields.io/github/issues/brunoclz/world-transparency-graph)](https://github.com/brunoclz/world-transparency-graph/issues)
[![Stars](https://img.shields.io/github/stars/brunoclz/world-transparency-graph?style=social)](https://github.com/brunoclz/world-transparency-graph/stargazers)
[![Forks](https://img.shields.io/github/forks/brunoclz/world-transparency-graph?style=social)](https://github.com/brunoclz/world-transparency-graph/network/members)
[![Twitter Follow](https://img.shields.io/twitter/follow/brunoclz?style=social)](https://x.com/brunoclz)
[![Discord](https://img.shields.io/badge/Discord-Join%20us-5865F2?logo=discord&logoColor=white)](https://discord.gg/YyvGGgNGVD)

[Discord](https://discord.gg/YyvGGgNGVD) | [Twitter](https://x.com/brunoclz) | [Website](https://bracc.org) | [Contributing](#contributing)

---

## What is br/acc?

br/acc is a decentralized movement of Brazilian builders using technology and open data to make public information more accessible. This repository is one of its projects: an open-source graph infrastructure that ingests official Brazilian public databases — company registries, health records, education metrics, employment data, public finances, procurement, environment — and normalizes them into a single queryable graph.

It makes public data that is already open but scattered across dozens of portals accessible in one place. It does not interpret, score, or rank results — it surfaces connections and lets users draw their own conclusions.

[Learn more at bracc.org](https://bracc.org)

---

## Features

- **45 data pipelines** — CNPJ, TSE, DataSUS, INEP, CAGED, RAIS, IBAMA, SICONFI, PNCP, Portal da Transparencia, and 35 more
- **Neo4j graph database** — entities, relationships, and connections normalized into a single queryable graph
- **React frontend** — search, explore corporate networks, and analyze entity connections
- **Public API** — programmatic access to graph data via FastAPI
- **Reproducible ETL** — every data source has a download script and a transform-load pipeline
- **Privacy-first** — LGPD compliant, public-safe defaults, no personal data exposure

---

## Quick Start

```bash
cp .env.example .env          # set NEO4J_PASSWORD
make dev                       # start all services
export NEO4J_PASSWORD=your_password
make seed                      # load sample data
```

You should see all containers running. Verify with:

- API: http://localhost:8000/health
- Frontend: http://localhost:3000
- Neo4j Browser: http://localhost:7474

---

## Architecture

| Layer | Technology |
|---|---|
| Graph DB | Neo4j 5 Community |
| Backend | FastAPI (Python 3.12+, async) |
| Frontend | Vite + React 19 + TypeScript |
| ETL | Python (pandas, httpx) |
| Infra | Docker Compose |

```mermaid
graph LR
    A[Public Data Sources] --> B[ETL Pipelines]
    B --> C[(Neo4j)]
    C --> D[FastAPI]
    D --> E[React Frontend]
    D --> F[Public API]
```

---

## Repository Map

```
api/          FastAPI backend (routes, services, models)
etl/          ETL pipelines and download scripts
frontend/     React app (Vite + TypeScript)
infra/        Docker, Neo4j schema, seed scripts
scripts/      Utility and automation scripts
docs/         Documentation, brand assets, legal index
data/         Downloaded datasets (git-ignored)
```

---

## API Reference

| Method | Route | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/v1/public/meta` | Aggregated metrics and source health |
| GET | `/api/v1/public/graph/company/{cnpj_or_id}` | Public company subgraph |
| GET | `/api/v1/public/patterns/company/{cnpj_or_id}` | Pattern analysis (when enabled) |

Full interactive docs available at `http://localhost:8000/docs` after starting the API.

---

## Contributing

We welcome contributions of all kinds — code, data pipelines, documentation, and bug reports. Check open issues for good first tasks, or open a new one to discuss your idea.

If you find this project useful, **star the repo** — it helps others discover it.

---

## Support the Project

[![Sponsor](https://img.shields.io/badge/GitHub_Sponsors-Support-ea4aaa?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/brunoclz)

If you want to support development directly:

| Network | Address |
|---|---|
| Solana | `HFceUyei1ndQypNKoiYSsHLHrVcaMZeNBeRhs8LmmkLn` |
| Ethereum | `0xbB3538D3e1B1Dd7c916BE7DfAC9ac7e322f592c7` |

---

## Community

- **Discord**: [discord.gg/YyvGGgNGVD](https://discord.gg/YyvGGgNGVD)
- **Twitter**: [@brunoclz](https://x.com/brunoclz)
- **Website**: [bracc.org](https://bracc.org)
- **Brazilian Accelerationism Community** on X

---

## Legal & Ethics

All data processed by this project is public by law. Every source is published by a Brazilian government portal or international open-data initiative and made available under one or more of the following legal instruments:

| Law | Scope |
|---|---|
| **CF/88 Art. 5 XXXIII, Art. 37** | Constitutional right to access public information |
| **Lei 12.527/2011 (LAI)** | Freedom of Information Act — regulates access to government data |
| **LC 131/2009 (Lei da Transparencia)** | Mandates real-time publication of fiscal and budget data |
| **Lei 13.709/2018 (LGPD)** | Data protection — Art. 7 IV/VII allow processing of publicly available data for public interest |
| **Lei 14.129/2021 (Governo Digital)** | Mandates open data by default for government agencies |

<details>
<summary><b>Brazil Dataset Matrix (Legal Basis)</b></summary>

| # | Source | Portal | Legal Basis |
|---|--------|--------|-------------|
| 1 | CNPJ (Company Registry) | Receita Federal | LAI, CF Art. 37 |
| 2 | TSE (Elections & Donations) | dadosabertos.tse.jus.br | Lei 9.504/1997 (Lei Eleitoral), LAI |
| 3 | Portal da Transparencia | portaldatransparencia.gov.br | LC 131/2009, LAI |
| 4 | CEIS/CNEP (Sanctions) | Portal da Transparencia | LAI, Lei 12.846/2013 (Lei Anticorrupcao) |
| 5 | BNDES (Dev. Bank Loans) | bndes.gov.br | LAI, LC 131/2009 |
| 6 | PGFN (Tax Debt) | portaldatransparencia.gov.br | LAI, Lei 6.830/1980 |
| 7 | ComprasNet (Procurement) | comprasnet.gov.br | Lei 14.133/2021 (Licitacoes), LAI |
| 8 | TCU (Audit Sanctions) | portal.tcu.gov.br | LAI, CF Art. 71 |
| 9 | TransfereGov | transferegov.sistema.gov.br | LC 131/2009, LAI |
| 10 | RAIS (Labor Stats) | PDET/MTE | LAI (aggregate, no personal data) |
| 11 | INEP (Education Census) | dados.gov.br | LAI, Lei 14.129/2021 |
| 12 | DataSUS/CNES (Health) | datasus.saude.gov.br | LAI, Lei 8.080/1990 (SUS) |
| 13 | IBAMA (Embargoes) | dados.gov.br | LAI, Lei 9.605/1998 (Crimes Ambientais) |
| 14 | DOU (Official Gazette) | in.gov.br | CF Art. 37 (publicidade) |
| 15 | Camara (Deputy Expenses) | dadosabertos.camara.leg.br | LAI, CF Art. 37 |
| 16 | Senado (Senator Expenses) | dadosabertos.senado.leg.br | LAI, CF Art. 37 |
| 17 | ICIJ (Offshore Leaks) | offshoreleaks.icij.org | Public interest journalism database |
| 18 | OpenSanctions (Global PEPs) | opensanctions.org | Open-data aggregator (CC-licensed) |
| 19 | CVM (Securities Proceedings) | dados.cvm.gov.br | LAI, Lei 6.385/1976 |
| 20 | CVM Funds | dados.cvm.gov.br | LAI, Lei 6.385/1976 |
| 21 | Servidores (Public Servants) | Portal da Transparencia | LC 131/2009, LAI |
| 22 | CEAF (Expelled Servants) | portaldatransparencia.gov.br | LAI, Lei 8.112/1990 |
| 23 | CEPIM (Barred NGOs) | portaldatransparencia.gov.br | LAI |
| 24 | CPGF (Govt Credit Cards) | portaldatransparencia.gov.br | LC 131/2009, LAI |
| 25 | Viagens a Servico | portaldatransparencia.gov.br | LC 131/2009, LAI |
| 26 | Renuncias Fiscais | portaldatransparencia.gov.br | LC 131/2009, LAI |
| 27 | Acordos de Leniencia | portaldatransparencia.gov.br | Lei 12.846/2013, LAI |
| 28 | BCB Penalidades | dados.bcb.gov.br | LAI, Lei 4.595/1964 |
| 29 | STF (Supreme Court) | portal.stf.jus.br | CF Art. 93 IX (publicidade judiciaria) |
| 30 | PEP CGU | portaldatransparencia.gov.br | LAI, Decreto 9.687/2019 |
| 31 | TSE Bens (Candidate Assets) | dadosabertos.tse.jus.br | Lei 9.504/1997 |
| 32 | TSE Filiados (Party Members) | dadosabertos.tse.jus.br | Lei 9.096/1995 (Lei dos Partidos) |
| 33 | OFAC SDN | treasury.gov | US public sanctions list |
| 34 | EU Sanctions | data.europa.eu | EU public sanctions list |
| 35 | UN Sanctions | un.org | UN Security Council public list |
| 36 | World Bank Debarment | worldbank.org | Public debarment list |
| 37 | Holdings (derived) | — | Derived from CNPJ data |
| 38 | SIOP (Budget Amendments) | siop.planejamento.gov.br | LC 131/2009, LAI |
| 39 | Senado CPIs | dadosabertos.senado.leg.br | LAI, CF Art. 58 §3 |

</details>

All findings are presented as source-attributed data connections, never as accusations. The platform enforces public-safe defaults that prevent exposure of personal information in public deployments.

<details>
<summary><b>Public-safe defaults</b></summary>

```
PRODUCT_TIER=community
PUBLIC_MODE=true
PUBLIC_ALLOW_PERSON=false
PUBLIC_ALLOW_ENTITY_LOOKUP=false
PUBLIC_ALLOW_INVESTIGATIONS=false
PATTERNS_ENABLED=false
VITE_PUBLIC_MODE=true
VITE_PATTERNS_ENABLED=false
```
</details>

- [ETHICS.md](ETHICS.md)
- [LGPD.md](LGPD.md)
- [PRIVACY.md](PRIVACY.md)
- [TERMS.md](TERMS.md)
- [DISCLAIMER.md](DISCLAIMER.md)
- [SECURITY.md](SECURITY.md)
- [ABUSE_RESPONSE.md](ABUSE_RESPONSE.md)
- [Legal Index](docs/legal/legal-index.md)

---

## Releases

- [Release history](https://github.com/World-Open-Graph/br-acc/releases)
- [Release policy](docs/release/release_policy.md)
- [Maintainer runbook](docs/release/release_runbook.md)

---

## License

[GNU Affero General Public License v3.0](LICENSE)
