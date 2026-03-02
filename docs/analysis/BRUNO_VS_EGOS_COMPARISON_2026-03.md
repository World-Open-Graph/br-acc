# Bruno's BR/ACC vs EGOS Fork — Honest Comparison

> **Date:** 2026-03-02 | **Author:** EGOS Intelligence

---

## Bruno's Original Promise (Feb 21, 2026)

Bruno César (@brunoclz) posted a viral thread on X showing:
- "If you connect all open databases in Brazil, you can detect corruption based on CPF of politicians"
- Screenshots showing R$89.2M in irregularities across 11 cases (critical, high, medium)
- 45 ETL pipelines, 70+ data sources mentioned in press coverage
- Got 835+ stars on GitHub, millions of views, press coverage (Soberano, etc.)

**Key quote:** "Transparency, open data, civic tools. Made by people who are tired of waiting."

---

## What Bruno's Repo ACTUALLY Delivers (Public Repo)

| Claim | Reality |
|-------|---------|
| "Detects corruption" | **Code exists** but patterns are **disabled by default** (`PATTERNS_ENABLED=false`) |
| "70+ data sources" | 45 ETL pipeline **code files** exist. Most are **not loaded** — require manual download + hours of processing |
| "R$89.2M in irregularities" | From his **private instance**. Public repo ships with **synthetic demo data** only |
| "Anyone can use it" | Requires Docker, Python 3.12, significant disk/RAM, and technical knowledge |
| "Open source" | **True** — AGPL-3.0, well-structured code, excellent documentation |

### What you get with `make bootstrap-demo`:
- A toy graph with synthetic seed data
- Working API + frontend + Neo4j locally
- Zero real Brazilian data

### What you get with `make bootstrap-all`:
- "Intentionally heavy, can take hours"
- Many sources are rate-limited, blocked, or offline
- No guaranteed success — reports per-source status
- Requires significant bandwidth, disk, and patience

### What's NOT in the public repo:
- No pre-populated Neo4j dump
- No bots (Discord/Telegram/WhatsApp)
- No public API for non-technical users
- No investigation reports or examples
- No persistent conversation memory
- No BNDES tool integration

---

## What EGOS Fork Actually Has Running (RIGHT NOW)

| Feature | Status | Details |
|---------|--------|---------|
| **Real data loaded** | ✅ LIVE | 278,501 nodes, 30,916 relationships on public server |
| **CNPJ (53.6M companies)** | 🔄 Loading | Upload to Contabo in progress, ETL ready to run |
| **Discord Bot** | ✅ LIVE 24/7 | 14 OSINT tools, @EGOS Intelligence#2881 |
| **Telegram Bot** | ✅ LIVE 24/7 | 14 tools, @EGOSin_bot |
| **BNDES API** | ✅ LIVE | Query any company's public financing (2002-present) |
| **Persistent memory** | ✅ LIVE | Conversations survive restart (Supabase) |
| **Public API** | ✅ LIVE | http://217.216.95.126/health |
| **Model fallback** | ✅ LIVE | Free tier → paid fallback → donation message |
| **Investigation reports** | ✅ Published | 11 reports including Patense (R$217M BNDES) |
| **Shared platform** | ✅ Schema ready | Anonymous reports, crowd corrections, governance |
| **Self-funded transparency** | ✅ Published | $36/mo total, all costs public |

### What a regular citizen can do TODAY with EGOS (zero install):
1. Open Telegram, search @EGOSin_bot
2. Type: "Quais os financiamentos BNDES da empresa Patense?"
3. Get real data from 14+ public sources in seconds
4. No Docker, no Python, no API keys needed

### What they'd need to do with Bruno's public repo:
1. Install Docker, Python 3.12, Git
2. Clone repo, configure .env, run bootstrap
3. Wait hours for data to load (if sources are online)
4. Navigate Neo4j browser or API manually
5. Write Cypher queries to cross-reference

---

## The Real Differentiator: After CNPJ Loads

When CNPJ (53.6M companies + QSA/partners) finishes loading:

| What becomes possible | ChatGPT can do this? |
|----------------------|---------------------|
| Query any CNPJ → see all partners, subsidiaries, holdings | No (would need to scrape Receita) |
| Cross-ref: BNDES money → company owners → PEPs | No (requires graph traversal) |
| Detect: politician is partner in company that received R$X from BNDES | No (requires multi-hop join) |
| Find: sanctioned company (CEIS) has partner who is PEP | No (requires entity resolution) |
| Expand: show all 1st/2nd/3rd degree connections of any entity | No (graph algorithm) |
| Anomaly: company received 147 BNDES ops in one year (fragmentation?) | Maybe, if you tell it the data |
| Pattern: shell companies (many companies, few employees, same address) | No (requires dataset) |
| Cross-case: find common entities across unrelated investigations | No (requires persistent graph) |

**This is where our tool goes from "ChatGPT with extra steps" to "impossible to replicate manually."**

---

## Comparison with Palantir Gotham

| Feature | Palantir Gotham | BR/ACC + EGOS | Gap |
|---------|----------------|---------------|-----|
| Entity resolution | Multi-source, ML-based | Jaro-Winkler + exact match (from Intelink) | Medium |
| Graph visualization | Interactive, drag-drop | React frontend + Neo4j browser | Large |
| Investigation timeline | Full audit trail | Designed, not implemented yet | Medium |
| Cross-case analysis | Core feature | Supabase tables ready, logic pending | Large |
| 1st/2nd/3rd degree expansion | Click-to-expand | API ready, UI pending | Medium |
| Data sources | 100+ (proprietary + public) | 45 ETL pipelines (10 loaded) | Medium |
| Anomaly detection | ML models, Benford, network analysis | Benford + HHI code exists, not activated | Medium |
| Price | $10M+/year | **$36/month** | We win |
| Accessibility | Government contracts only | **Any citizen, free, via Telegram** | We win |

**Our Intelink already has:** Cross-reference service (6-level matching), link prediction, accuracy tracking, draggable dashboard, investigation timeline, graph visualization. These components can be ported to BR/ACC.

---

## Honest Bottom Line

**Bruno built excellent infrastructure.** 45 ETL pipelines, clean architecture, proper legal framework. His viral post was legitimate — the code CAN do what he showed. But his public repo gives you demo data and a DIY kit.

**We made it accessible.** Any Brazilian can message our bot and get real answers from real data. No install, no Docker, no API keys. We added BNDES (which nobody else has as a tool), persistent memory, and investigation reports.

**The gap to Palantir is real but closeable.** With CNPJ loaded, graph algorithms activated, and Intelink components ported, we'll have 80% of Palantir's core functionality at 0.004% of the cost.

**What makes this genuinely unique:**
1. Free bot accessible to any citizen (not just technicians)
2. 14+ data sources unified in one conversational interface
3. BNDES financing data as queryable tool (nobody else does this)
4. Open source — anyone can audit, contribute, or fork
5. Self-funded transparency — every cent accounted for

---

*"The code was always open. We made the knowledge open."*
