# TASKS.md — EGOS Inteligência (SSOT)

> **Updated:** 2026-03-02 (session 2) | **GitHub Issues:** https://github.com/enioxt/EGOS-Inteligencia/issues

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

### TASK-004: Redis Cache-Aside (GitHub #19) ✅ (02/03/2026)
- [x] Redis rodando no docker-compose (bracc network)
- [x] `api/src/bracc/services/cache.py` — async cache with graceful degradation
- [x] Search endpoint cached (TTL 2min), entity (5min), stats (1min), connections (3min)
- [x] `/api/v1/meta/cache-stats` — hit rate, misses, errors, TTL config
- [x] `/api/v1/meta/cache` DELETE — flush all cache keys
- [x] Deployed and verified: 50% hit rate on repeated queries
> **Arquivos:** `api/src/bracc/services/cache.py`, `api/src/bracc/routers/search.py`, `api/src/bracc/routers/meta.py`

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
- [x] Publicar em inteligencia.egos.ia.br/reports/patense.html
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

### TASK-015: Bot Integration — Discord/Telegram (GitHub #8) ✅ (02/03/2026)
- [x] Discord: `EGOS Intelligence#2881` — 14 OSINT tools, slash commands, Supabase persistence
- [x] Telegram: `@EGOSin_bot` — 14 OSINT tools, long polling, conversation memory
- [x] Both bots stable via PM2 ecosystem.config.cjs with .env loading
- [x] Model fallback: paid Gemini 2.0 Flash first, free tier as backup
- [x] Auto-create GitHub issues from user feedback (||TASK|| markers)
- [ ] WhatsApp: estrutura pronta para qualquer número
> **Arquivos:** `/opt/egos-bot/packages/shared/src/social/` (discord-bot.ts, telegram-bot.ts, ai-engine.ts)

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

### TASK-023: Docs para Leigos (GitHub #3, #4) ⏳
- [ ] Traduzir data-sources.md para PT-BR
- [x] Criar FAQ para leigos em PT-BR (02/03/2026)
> **Arquivos:** `docs/FAQ_PT-BR.md`

### TASK-024: Rename BR/ACC → EGOS Inteligência ✅ (02/03/2026)
- [x] i18n.ts — todas as referências
- [x] index.html — title
- [x] AppShell.tsx — logo sidebar
- [x] README.md — reescrito completo
- [x] ROADMAP.md — headers e links
- [x] TASKS.md — header
> **DNS pendente:** Criar `inteligencia.egos.ia.br` e atualizar Caddy

### TASK-025: LGPD — Remover CPF do sistema inteiro ✅ (02/03/2026)
- [x] Frontend: remover CPF de search placeholders (i18n.ts)
- [x] Frontend: remover CPF de EntityDetail.tsx (só mostra CNPJ)
- [x] Backend: `public_guard.py` — CPF lookup SEMPRE bloqueado (não só public mode)
- [x] Backend: `sanitize_public_properties` — SEMPRE filtra CPF (não só public mode)
- [x] Backend: CPF masking middleware mantido como safety net
> **Arquivos:** `frontend/src/i18n.ts`, `frontend/src/components/entity/EntityDetail.tsx`, `api/src/bracc/services/public_guard.py`

### TASK-026: Mobile-First — Remover bloqueio de tela <1024px ✅ (02/03/2026)
- [x] Remover `isMobileBlocked` do AppShell.tsx
- [x] Adicionar bottom navigation para mobile (<768px)
- [x] Mobile layout funcional com Outlet + nav fixa
> **Arquivos:** `frontend/src/components/common/AppShell.tsx`

### TASK-027: Chatbot AI na Landing Page ✅ (02/03/2026)
- [x] Backend: `POST /api/v1/chat` — endpoint conversacional
- [x] Frontend: `ChatInterface.tsx` — componente mobile-first (dark theme)
- [x] Integrar na Landing como interface primária
- [x] Phase 1: busca estruturada Neo4j (sem LLM)
- [x] Phase 2: LLM via OpenRouter (Gemini 2.0 Flash) com function calling
- [x] Memória de conversa por sessão (IP-based, 30min TTL, 20 msgs)
- [x] 3 tools: search_entities, get_graph_stats, get_entity_connections
- [x] Sugestões contextuais dinâmicas
- [ ] Phase 3: rich results (entity cards clicáveis, mini-grafos)
> **Arquivos:** `api/src/bracc/routers/chat.py`, `frontend/src/components/chat/ChatInterface.tsx`

### TASK-028: Investigações — Upload, Fork, Compartilhamento ⬜
- [ ] Formatos de exportação: MD, PDF, DOCX, JSON, HTML
- [ ] Formatos de importação: MD, JSON, HTML (os que fazem sentido)
- [ ] Fork/clone de investigações públicas
- [ ] Espiral de escuta — continuar investigação a partir de outra
- [ ] Interação e comentários em investigações compartilhadas

### TASK-029: Journey Tracker v2 ⬜
- [ ] Design novo (não port do Intelink)
- [ ] Rastreamento de passos de investigação
- [ ] FAB mobile-friendly
- [ ] Exportação de timeline

### TASK-030: Gem Hunter Agent ⬜ (GitHub #23)
- [ ] Construir modular no egos-lab framework
- [ ] Scanner de repos GitHub brasileiros de transparência
- [ ] Primeiro deploy no website EGOS Inteligência
- [x] Pesquisa inicial: 9 projetos encontrados (02/03/2026)
> **Projetos encontrados:**
> - `jpvss/CEAP-Playbook` — Benford + HHI para CEAP (OURO)
> - `Pr0teus/BROS` — OSINT sources brasileiras + Neo4j
> - `pedropberger/Julius` — Bot scraper de portais de transparência (ES)
> - `vfpimenta/corruption-profiler` — Anomalia em gastos parlamentares
> - `rodrigolink/benford` — Benford em dados eleitorais TSE
> - `pedronipalhares/CVM358` — Insider trading CVM
> - `GuiCosti/Public-Spending-Analysis` — CPGF anomalias
> - `RenatoDev4/spending-anomalies` — AutoEncoder para gastos
> - `Apify/brazil-government-transparency` — Scraper dados governo

### TASK-031: Integrar CEAP-Playbook (Benford + HHI) ⬜
- [ ] Adaptar `analise_benford()` para nosso backend (scipy chi-squared)
- [ ] Adaptar HHI por fornecedor para contratos no grafo
- [ ] Criar ETL pipeline para CEAP (Câmara API, CSV zips por ano)
- [ ] Adicionar dicionário de dados CEAP
- [ ] Visualização Benford no frontend (esperado vs observado)
> **Ref:** https://github.com/jpvss/CEAP-Playbook

### TASK-032: DNS inteligencia.egos.ia.br ✅ (02/03/2026)
- [x] DNS A record criado pelo usuário
- [x] Caddyfile atualizado (inteligencia.egos.ia.br + bracc 301 redirect)
- [x] SSL Let's Encrypt obtido automaticamente
- [x] Caddy reiniciado, serviço ativo
- [x] URLs atualizadas no codebase (TASKS, ROADMAP, plans)
- [x] CORS_ORIGINS/.env atualizados

### TASK-033: Linguagem Legal — Pesquisa Pessoal ✅ (02/03/2026)
- [x] Disclaimer atualizado: "Pesquisa pessoal com dados públicos. Padrões são sinais, não prova jurídica."
- [x] "Investigue em profundidade" → "Pesquise em profundidade"
- [x] "Investigações recentes" → "Pesquisas recentes"
- [x] Feature descriptions focam em "pesquisa pessoal" e "dados públicos"
> **Arquivos:** `frontend/src/i18n.ts`

### TASK-034: Gem Hunter — Keywords de Busca ⬜
- [ ] Implementar busca por semântica no GitHub API
- [ ] Keywords mapeadas: CEAP, cota parlamentar, transparencia brasil, CNPJ consulta, licitacao anomalia, benford brazil, Neo4j governo, OSINT brasil, serenata amor, TCU auditoria, CGU dados
- [ ] Engenharia reversa do EGOS Inteligência para extrair tags
- [ ] Monitoramento periódico de novos repos

### TASK-035: Changelog/Updates no Website ✅ (02/03/2026)
- [x] UpdatesTimeline component na landing page (expandable cards, tags, metricas)
- [x] JSON changelog entries em frontend/public/updates/YYYY-MM-DD.json
- [x] Primeira entrada: Redis cache, 108 fontes, bots, governanca
- [x] Relatorio Patense linkado no changelog
> **Arquivos:** `frontend/src/components/landing/UpdatesTimeline.tsx`, `frontend/public/updates/`

### TASK-036: Pipeline Social Integrado (/postar) ⏳
- [x] Workflow /postar criado (X.com, Telegram, Discord)
- [x] Telegram e Discord postando com sucesso
- [ ] X.com: precisa API keys (X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
- [ ] Conta @anoineim precisa verificacao por telefone
> **Arquivos:** `.windsurf/workflows/postar.md`, bot x-client.ts

### TASK-037: Bot Self-Healing ✅ (02/03/2026)
- [x] Cron healthcheck cada 5 min (/opt/egos-bot/healthcheck.sh)
- [x] Auto-restart de bots crashados via PM2
- [x] Logging em /var/log/egos-bot-health.log
- [x] Alertas via Telegram quando bot restartar (envia para @ethikin)
- [x] Healthcheck v2: pm2 describe + awk para status correto
- [ ] Dashboard de uptime no website (P3)
- [ ] HGR-style 3-level memory (P3, inspirado RokoOfficial/HGR)

### TASK-038: Kubernetes / Autoscaler / Self-Healing ⬜ (P2 — Planejamento)
- [ ] Avaliar migrar de Docker Compose para k3s (lightweight Kubernetes para VPS)
- [ ] Configurar HPA (Horizontal Pod Autoscaler) para API
- [ ] Liveness/readiness probes para todos os servicos
- [ ] Auto-rollback em deploys com falha
- [ ] Monitoramento com Prometheus + Grafana
> **Nota:** Contabo VPS tem recursos limitados. k3s é mais viavel que k8s completo.

### TASK-039: Codex CLI no Contabo VPS ⬜ (P2 — Pesquisa)
- [ ] Verificar se OpenAI Codex CLI funciona em VPS headless
- [ ] Configurar codex login via token (sem browser)
- [ ] Usar codex exec para tarefas async (code review, testes)
- [ ] Integrar com CI/CD para auto-fix de falhas
> **Requisitos:** Conta OpenAI ativa, CODEX_TOKEN no .env

### TASK-040: OpenClaw / Agentes CI/CD QA ⬜ (P2 — Pesquisa)
- [ ] Avaliar OpenClaw como framework de agentes autonomos
- [ ] Configurar agente QA para monitorar erros e sugerir fixes
- [ ] Integrar com GitHub Actions para PR auto-review
- [ ] Usar modelo Gemini 2.0 Flash (pago) via OpenRouter
- [ ] Pipeline: erro detectado -> agente analisa -> sugere fix -> cria PR
> **Inspiracao:** OpenClaw molt.sh self-healing pattern, RokoOfficial/OPENBOT

### TASK-041: SourceRegistry — Transparencia Total no Website ✅ (02/03/2026)
- [x] SourceRegistry component com 108 fontes, links diretos, categorias, tiers, filtros
- [x] sources.json gerado do CSV com 27 categorias
- [x] Injetado na landing page acima do UpdatesTimeline
- [x] Cada fonte com link para portal oficial do governo
- [x] Paginacao: 10 fontes por pagina com botoes prev/next
> **Arquivos:** `frontend/src/components/landing/SourceRegistry.tsx`, `frontend/public/updates/sources.json`

### TASK-044: Linha do Tempo Completa + ETL Progress Widget ✅ (02/03/2026)
- [x] UpdatesTimeline reescrito com timeline vertical (24 marcos desde fork do Bruno)
- [x] timeline.json com todos os milestones de Jan 15 a Mar 02 2026
- [x] Mostra 5 recentes por padrao, expansivel para todos os 24
- [x] ETLProgress widget: barra de progresso ao vivo, auto-refresh 30s
- [x] Endpoint /api/v1/meta/etl-progress: fase, arquivo, %, running status
- [x] ETL usa mtime do log (container-compatible) em vez de pgrep
> **Arquivos:** `frontend/src/components/landing/UpdatesTimeline.tsx`, `frontend/public/updates/timeline.json`, `frontend/src/components/landing/ETLProgress.tsx`, `api/src/bracc/routers/meta.py`

### TASK-045: Bot Error Handling — DM Only ✅ (02/03/2026)
- [x] Telegram: erros so enviados em chat privado (ctx.chat.type === 'private')
- [x] Discord: erros via message.author.send() (DM), nao message.reply() (channel)
- [x] Healthcheck v2: corrigido parsing de status (pm2 describe + awk)
- [x] Healthcheck alertas Telegram para @ethikin no restart/failure
> **Arquivos:** `telegram-bot.ts`, `discord-bot.ts`, `/opt/egos-bot/healthcheck.sh`

### TASK-047: Chat Links New Tab + Journey System ✅ (02/03/2026)
- [x] Chat: entity clicks abrem em nova aba (window.open _blank) em vez de navegar
- [x] Chat: URLs no markdown recebem target=_blank automaticamente
- [x] Chat: links markdown [text](url) renderizados corretamente
- [x] Journey: lib/journey.ts — localStorage com 500 entries max, dedup 60s, export JSON/MD
- [x] Journey: JourneyPanel.tsx — painel flutuante com stats, lista, export, share, clear
- [x] Journey: integrado no ChatInterface (tracks queries + entity views)
- [x] Journey: exportavel como JSON ou Markdown, compartilhavel via Web Share API
- [ ] Journey: persistencia no backend com login (futuro)
> **Arquivos:** `frontend/src/lib/journey.ts`, `frontend/src/components/journey/JourneyPanel.tsx`, `frontend/src/components/chat/ChatInterface.tsx`

### TASK-046: Diagnostico Completo do Sistema ✅ (02/03/2026)
- [x] 14 OSINT tools registrados nos bots
- [x] 30+ endpoints API em 10 routers
- [x] 5 containers Docker (frontend, api, caddy, neo4j, redis)
- [x] 2 bots PM2 (discord, telegram)
- [x] 23 issues GitHub abertas, 0 fechadas
- [x] ETL: CPU processing (32GB em disco), nao internet
- [x] Relatorio Patense em /reports/patense.html (nao linkado na landing)
- [ ] Falta: pre-commit hooks no repo EGOS-Inteligencia
- [ ] Falta: pagina dedicada de relatorios na landing
- [ ] Falta: rebuild da imagem Docker da API (DNS transient error, hotfix via docker cp)

### TASK-042: /app — Plataforma de Pesquisa Colaborativa ⏳ (P1)
- [x] /app/search: Busca no grafo (JA EXISTE, public mode)
- [x] /app/analysis/:entityId: Analise de entidade (JA EXISTE)
- [x] /app/graph/:entityId: Explorador de grafo (JA EXISTE)
- [x] /app/patterns: Deteccao de padroes (JA EXISTE)
- [x] /app/baseline/:entityId: Baseline de entidade (JA EXISTE)
- [x] /app/investigations: Caderno de pesquisa (JA EXISTE, auth-gated)
- [x] /app/shared/:token: Compartilhamento publico de investigacoes (JA EXISTE)
- [x] Dashboard com pesquisas recentes + busca rapida (JA EXISTE)
- [ ] Auth: Login com Google/GitHub (precisa backend auth)
- [ ] /app/public: Feed comunitario de pesquisas publicadas
- [ ] Incentivo: Badge "Pesquisador Cidadao" para quem publica
- [ ] Cross-link: Quando pesquisas diferentes encontram mesmas entidades, destacar
- [ ] Feedback loop: Conexoes de usuarios -> melhorar ETL
- [ ] Historico de pesquisas (privado por padrao, publico se optar)
> **Status:** Frontend JA TEM 8 paginas funcionais. Falta auth backend + feed comunitario.
> **Arquivos:** `frontend/src/pages/Dashboard.tsx`, `Investigations.tsx`, `SharedInvestigation.tsx`, `Search.tsx`, `EntityAnalysis.tsx`, `GraphExplorer.tsx`, `Patterns.tsx`, `Baseline.tsx`

### TASK-043: Gem Hunter v2 — Melhorar Busca de Projetos ⏳ (P2)
- [x] Adicionar keywords semanticas: "accountability", "civic tech", "open government"
- [x] Busca automatizada via GitHub Search API (5 categorias, 02/03/2026)
- [x] LMCache avaliado: NAO aplicavel (usamos API OpenRouter)
- [x] Bruin avaliado: framework ETL declarativo — NAO aplicavel AGORA (sem Neo4j), util futuro para DuckDB analytics
- [x] OSINT-BIBLE (299★), WebRecon (250★), OSINTel-Dashboard (39★) encontrados
- [x] synapse-lite (Neo4j fraud detection) encontrado — pequeno mas relevante
- [ ] Monitorar repos novos com cron semanal
- [ ] Manter registro de projetos avaliados (evitar re-avaliar)
> **Projetos avaliados:** 9 anteriores + LMCache + 3 RokoOfficial + Bruin + 4 novos OSINT (total: 18)
> **Bruin:** getbruin.com — declarative YAML+SQL+Python pipelines. Suporta Postgres/DuckDB/BigQuery. SEM Neo4j. Futuro: DuckDB analytics layer.

---

## Métricas

| Métrica | Valor | Data |
|---|---|---|
| **Nós no grafo** | 317.583 | 02/03/2026 |
| **Relacionamentos** | 34.507 | 02/03/2026 |
| **Issues GitHub abertas** | 23 | 02/03/2026 |
| **Tasks concluídas** | 27/47 | 02/03/2026 |
| **ETL Status** | Phase 1 em andamento | 02/03/2026 |
| **Website** | inteligencia.egos.ia.br (SSL ✅) | 02/03/2026 |
| **Projetos Gem Hunter** | 9 encontrados | 02/03/2026 |

---

*"Siga o dinheiro público. Dados abertos, código aberto."*
