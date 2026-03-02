# TASKS.md — BR/ACC (SSOT)

> **Updated:** 2026-03-02 | **GitHub Issues:** https://github.com/enioxt/br-acc/issues

---

## P0 — Em Andamento (Blockers)

### TASK-001: CNPJ ETL — 53.6M empresas ⏳
- [x] Upload 6.8GB zip para Contabo
- [x] Extrair dados (26GB descomprimido)
- [ ] Phase 1: Build estab_lookup (em execução, PID 555786)
- [ ] Phase 2: Create Company nodes
- [ ] Phase 3: Create Person/Partner nodes + SOCIO_DE relationships
- [ ] Phase 4: Post-load hooks (entity linking)
> **Server:** 217.216.95.126 | **Log:** `/opt/bracc/cnpj-etl.log`

### TASK-002: Neo4j Performance Optimization ⏳
- [x] Criar script `neo4j-memory-upgrade.sh` (16G heap, 22G pagecache)
- [x] Criar script `post-etl-optimize.sh` (12 indexes + fulltext)
- [x] Documentar arquitetura: `docs/analysis/PERFORMANCE_ARCHITECTURE_2026-03.md`
- [ ] Aplicar memory upgrade APÓS ETL completar
- [ ] Criar todos os indexes APÓS ETL completar
- [ ] Verificar query < 5ms para CNPJ lookup
> **Depende de:** TASK-001

### TASK-003: Search Fix + Hardcoded Data ✅ (02/03/2026)
- [x] Remover números falsos do i18n.ts (87M, 53M, 8 algoritmos)
- [x] Adicionar wildcard + fuzzy search na API (`_build_search_query()`)
- [x] Deploy API + frontend reconstruídos
- [x] Verificar busca funcionando ("silva" → 1073 resultados)
> **Arquivos:** `api/src/bracc/routers/search.py`, `frontend/src/i18n.ts`

---

## P1 — Sprint Atual

### TASK-004: Redis Cache-Aside (GitHub #19) ⬜
- [ ] Adicionar Redis ao docker-compose.prod.yml
- [ ] Criar `api/src/bracc/services/cache.py`
- [ ] Wrap endpoints: search (TTL 2min), entity (TTL 5min), stats (TTL 1min)
- [ ] Endpoint `/api/v1/meta/cache-stats` para monitorar hit rate
> **Inspiração:** Facebook TAO, LinkedIn RAM-first

### TASK-005: GDS Algorithms (GitHub #20) ⬜
- [ ] Instalar plugin GDS no Neo4j
- [ ] Implementar PageRank para entidades
- [ ] Community Detection (Louvain) para clusters
- [ ] Shortest Path entre entidades
- [ ] Betweenness Centrality para bridge entities
> **Depende de:** TASK-001, TASK-002

### TASK-006: Bounded Traversals (GitHub #22) ⬜
- [ ] Limitar traversals a max 3 hops
- [ ] Query timeout 30s max
- [ ] Pre-computar anomaly scores para hot entities
- [ ] Paginação para large result sets
> **Inspiração:** Palantir Gotham

### TASK-007: Investigation Upload + Sharing ⬜
- [ ] API: endpoint para upload de investigações (HTML, PDF, JSON)
- [ ] API: listar investigações compartilhadas publicamente
- [ ] Frontend: UI de upload no menu do usuário
- [ ] Frontend: galeria de investigações compartilhadas
- [ ] Frontend: "continuar a partir de" outra investigação (fork)
> **Referência:** Intelink `components/shared/ShareJourneyDialog.tsx`

### TASK-008: Journey Tracker / Step Counter ⬜
- [ ] Portar JourneyContext do Intelink
- [ ] Portar JourneyFABGlobal (balãozinho flutuante)
- [ ] Adaptar tipos (journey.ts) para contexto BR/ACC
- [ ] Integrar com busca (registrar cliques)
> **Referência:** Intelink `providers/JourneyContext.tsx`, `components/shared/JourneyFABGlobal.tsx`

### TASK-009: Patense Report v2 ✅ (02/03/2026)
- [x] Reescrever relatório com linguagem neutra
- [x] Completar dados BNDES (R$217M, 4 empresas, 563 operações)
- [x] Publicar em bracc.egos.ia.br/reports/patense.html
- [x] Persistir em frontend/public/reports/
> **Arquivos:** `docs/showcase/patense-investigation.html`

### TASK-010: Public Mode + Landing Page ✅ (02/03/2026)
- [x] Ativar VITE_PUBLIC_MODE=true no Dockerfile
- [x] Adicionar LiveDatabaseStatus component
- [x] Adicionar PartnershipCTA component
- [x] Deploy no Contabo
> **Arquivos:** `frontend/Dockerfile`, `frontend/src/pages/Landing.tsx`

---

## P2 — Backlog

### TASK-011: Rename BR/ACC → Novo Nome ⬜
- [ ] Definir nome final (EGOS Intelligence? Outro?)
- [ ] Atualizar i18n, README, ROADMAP, frontend
- [ ] Atualizar DNS se necessário
- [ ] Score de divergência do fork original > 80%

### TASK-012: Gem Hunter Agent (GitHub #23) ⬜
- [ ] Criar agente que escaneia GitHub por repos brasileiros de transparência
- [ ] Classificar repos por qualidade, features únicas, oportunidades
- [ ] Gerar relatório semanal em docs/gem-hunter/
- [ ] Notificar bots (Telegram/Discord) sobre descobertas
> **Referência:** `egos-lab/scripts/scan_ideas.ts`, `docs/plans/EGOS_LOST_GEMS.md`

### TASK-013: Fork Monitor (GitHub #9) ⬜
- [ ] Script 2x/dia checa forks de World-Open-Graph/br-acc
- [ ] Detectar novos PRs, issues, contribuições
- [ ] Alertar no Telegram/Discord
- [ ] Comparar features entre forks

### TASK-014: Website Redesign (GitHub #21) ⬜
- [ ] CMD+K global search (portar do Intelink)
- [ ] Search history (últimos acessos)
- [ ] Connection preview on hover
- [ ] Entity Detail Modal from search
- [ ] Mobile responsive improvements
- [ ] Accessibility (a11y)
> **Referência:** Intelink `components/shared/GlobalSearch.tsx`

### TASK-015: Bot Integration — Discord/Telegram/WhatsApp (GitHub #8) ⬜
- [ ] Discord: integrar BR/ACC como tool no bot existente
- [ ] Telegram: integrar no @ethikin bot
- [ ] WhatsApp: estrutura pronta para qualquer número
- [ ] Passo a passo para leigos no egos.ia.br

### TASK-016: Pipeline Extrateto — Supersalários (GitHub #5) ⬜
- [ ] ETL para dados de salários do judiciário
- [ ] Detecção de supersalários acima do teto

### TASK-017: Lei de Benford (GitHub #6) ⬜
- [ ] Implementar análise de primeiro dígito em contratos
- [ ] API endpoint para consulta por órgão

### TASK-018: HHI — Concentração de Fornecedores (GitHub #7) ⬜
- [ ] Implementar índice Herfindahl-Hirschman
- [ ] Detectar monopolização por órgão contratante

### TASK-019: i18n Completo PT-BR (GitHub #1, #2) ⬜
- [ ] Frontend: locale pt-BR completo
- [ ] API: mensagens de erro em PT-BR

### TASK-020: Neutrality Audit CI ⬜
- [ ] CI que bane palavras como "suspicious", "corrupt", "criminal"
- [ ] Adaptado do br-acc upstream

### TASK-021: Interoperabilidade Global (GitHub #18) ⬜
- [ ] FollowTheMoney format
- [ ] Aleph/OCCRP integration
- [ ] ICIJ compatibility

### TASK-022: Pipelines Restantes (GitHub #12-16) ⬜
- [ ] IBGE (Censo, PNAD, IPCA, PIB) — #12
- [ ] DENATRAN/RENAVAM — #13
- [ ] Agências Reguladoras — #14
- [ ] Meio Ambiente (INPE, CAR, INCRA) — #15
- [ ] SIAFI + Tesouro Transparente — #16

### TASK-023: Docs para Leigos (GitHub #3, #4) ⬜
- [ ] Traduzir data-sources.md para PT-BR
- [ ] Criar FAQ para leigos

---

## Métricas

| Métrica | Valor | Data |
|---|---|---|
| **Nós no grafo** | 317.583 | 02/03/2026 |
| **Relacionamentos** | 34.507 | 02/03/2026 |
| **Issues GitHub abertas** | 23 | 02/03/2026 |
| **Tasks concluídas** | 3/23 | 02/03/2026 |
| **ETL Status** | Phase 1 em andamento | 02/03/2026 |

---

*"Siga o dinheiro público. Dados abertos, código aberto."*
