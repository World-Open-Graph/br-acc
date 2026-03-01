# BR/ACC Fork — Roadmap Público

> **Fork:** [enioxt/br-acc](https://github.com/enioxt/br-acc)
> **Upstream:** [World-Open-Graph/br-acc](https://github.com/World-Open-Graph/br-acc)
> **Atualizado:** 2026-03-01

---

## Status Board

| # | Task | Status | Responsável | Prioridade | Issue |
|---|---|---|---|---|---|
| 1 | README PT-BR reescrito (copy acessível) | ✅ Feito | @enioxt | P0 | — |
| 2 | Frontend locale pt-BR (i18next) | 🟡 Aberto | Voluntário | P1 | [#1](https://github.com/enioxt/br-acc/issues/1) |
| 3 | API mensagens de erro PT-BR | 🟡 Aberto | Voluntário | P1 | [#2](https://github.com/enioxt/br-acc/issues/2) |
| 4 | Traduzir data-sources.md | 🟡 Aberto | Voluntário | P2 | [#3](https://github.com/enioxt/br-acc/issues/3) |
| 5 | FAQ para leigos | 🟡 Aberto | Voluntário | P2 | [#4](https://github.com/enioxt/br-acc/issues/4) |
| 6 | ETL Extrateto (Judiciário) | 🟡 Aberto | Voluntário | P1 | [#5](https://github.com/enioxt/br-acc/issues/5) |
| 7 | Algoritmo Lei de Benford | 🟡 Aberto | Voluntário | P2 | [#6](https://github.com/enioxt/br-acc/issues/6) |
| 8 | Algoritmo HHI (Concentração) | 🟡 Aberto | Voluntário | P2 | [#7](https://github.com/enioxt/br-acc/issues/7) |
| 9 | Bot Discord/Telegram/WhatsApp | 🔵 Em progresso | @enioxt | P0 | [#8](https://github.com/enioxt/br-acc/issues/8) |
| 10 | Repo monitor automatizado 2x/dia | 🟡 Aberto | @enioxt | P1 | [#9](https://github.com/enioxt/br-acc/issues/9) |
| 11 | Roadmap público + coordenação | ✅ Feito | @enioxt | P1 | [#10](https://github.com/enioxt/br-acc/issues/10) |
| 12 | Detecção de PR duplicado | 🟡 Aberto | Voluntário | P2 | [#11](https://github.com/enioxt/br-acc/issues/11) |
| 13 | Deploy servidor Contabo (Neo4j) | 🔵 Em progresso | @enioxt | P0 | — |

**Legenda:** ✅ Feito · 🔵 Em progresso · 🟡 Aberto · 🔴 Bloqueado

---

## Prioridades

### P0 — Bloqueante
- Deploy do servidor Neo4j (Contabo VPS 40, 48GB RAM)
- Bot Discord consumindo API BR/ACC
- README PT-BR acessível

### P1 — Sprint atual (Mar/2026)
- Tradução do frontend (locale pt-BR)
- ETL Extrateto (nova fonte de dados)
- Monitor automático de atividade no repo
- Bot Telegram

### P2 — Backlog
- Algoritmos (Benford, HHI)
- FAQ
- Tradução completa de docs
- MCP Server para IDEs
- Bot WhatsApp
- Detecção de duplicatas em PRs

---

## Como contribuir

1. **Escolha uma issue** marcada como 🟡 Aberto
2. **Comente na issue** dizendo que vai trabalhar nela
3. Eu atualizo o status para 🔵 e seu nome como responsável
4. **Abra PR** quando terminar
5. PRs são revisados e mergeados no fork, depois enviados como PR ao upstream

### Evitar duplicatas
Antes de começar, verifique:
- Se alguém já está trabalhando nisso (coluna "Responsável")
- Se já existe PR aberto no upstream para a mesma coisa
- Se a issue ainda está relevante

---

## Upstream PRs (monitoramento)

| # | Status | Título | Relevância para nós |
|---|---|---|---|
| #7 | OPEN | Makefile + dev docs | ⚠️ Duplicata do #6 |
| #6 | OPEN | Adding Makefile | ⚠️ Duplicata do #7 |
| #5 | MERGED | Fix local dev setup | ✅ Já sincronizado |
| #4 | MERGED | Brazil datasets legal matrix | ✅ Já sincronizado |
| #3 | MERGED | Replace Icarus naming + PT-BR docs | ✅ Já sincronizado |
| #2 | MERGED | Rebrand to BRACC | ✅ Já sincronizado |
| #1 | MERGED | Update repo refs | ✅ Já sincronizado |

*Última sincronização com upstream: 2026-03-01 17:00 UTC-3*

---

*"Coordenação evita retrabalho. Transparência atrai contribuidores."*
