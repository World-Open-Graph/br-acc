# TASKS.md — EGOS Inteligência (SSOT)

> **Updated:** 2026-03-03 (session 6) | **Stars:** ~70 ⭐ | **Patterns:** 10 | **GitHub Issues:** https://github.com/enioxt/EGOS-Inteligencia/issues

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

### TASK-008: Journey Tracker / Step Counter ✅ (02/03/2026)
- [x] Journey lib: localStorage, 500 entries, dedup, export JSON/MD, Web Share API
- [x] JourneyPanel: floating panel with stats, entries, export/share/clear
- [x] Integrado em: Chat, Search, EntityAnalysis, Dashboard, Landing, GraphExplorer, Investigations
- [x] Registra buscas, views de entidades, queries de chat automaticamente
> **Arquivos:** `frontend/src/lib/journey.ts`, `frontend/src/components/journey/JourneyPanel.tsx`

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
- [x] Pre-commit hooks instalados (secrets, large files, Python syntax) ✅ (02/03/2026)
- [x] ReportsShowcase na landing (Patense report linkado) ✅ (02/03/2026)
- [x] Docker API rebuilt (DNS resolvido) ✅ (02/03/2026)

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
- [x] Historico de pesquisas: Journey system (localStorage, export JSON/MD, share) ✅ (02/03/2026)
> **Status:** Frontend JA TEM 8 paginas funcionais + Journey. Falta auth backend + feed comunitario.
> **Arquivos:** `frontend/src/pages/Dashboard.tsx`, `Investigations.tsx`, `SharedInvestigation.tsx`, `Search.tsx`, `EntityAnalysis.tsx`, `GraphExplorer.tsx`, `Patterns.tsx`, `Baseline.tsx`

### TASK-048: Chatbot Investigativo — 18 Tools ✅ (02/03/2026)
- [x] 3 graph tools: search_entities, get_graph_stats, get_entity_connections
- [x] web_search (DuckDuckGo), search_emendas, search_transferencias (TransfereGov)
- [x] search_ceap, search_pep_city, search_votacoes (Câmara dos Deputados)
- [x] search_gazettes, cnpj_info (Querido Diário — 510+ cidades)
- [x] search_servidores, search_licitacoes, search_cpgf, search_viagens, search_contratos, search_sancoes (Portal da Transparência — chave API)
- [x] search_processos (DataJud/CNJ — todos os tribunais do Brasil)
- [x] System prompt: puxar o fio, cross-reference, caminho do dinheiro
- [x] Suggestions: recuperações judiciais, supersalários, fornecedores, investigações
- [x] 18 tools total (3 grafo + 8 livres + 6 Portal Transparência + 1 DataJud)
- [x] Brave Search API integrado como primário ($5/mês), DDG fallback ✅ (02/03/2026)
> **Arquivos:** `api/src/bracc/services/transparency_tools.py`, `api/src/bracc/routers/chat.py`
> **APIs:** Brave Search (primário) + DDG (fallback), TransfereGov, Câmara, Querido Diário + Portal Transparência, DataJud

### TASK-049: Avaliação Unikraft + ESAA ✅ (02/03/2026)
- [x] Unikraft avaliado: NÃO aplicável (unikernels para microserviços stateless, nosso stack é Docker + Neo4j + Python)
- [x] ESAA avaliado: EXCELENTE padrão para egos-lab (event sourcing para agentes AI, audit trail, contracts)
- [ ] Implementar event sourcing no egos-lab agent runtime (inspirado ESAA) — P2
> **Unikraft:** github.com/unikraft/unikraft — 4.1k★. Boot em ms, footprint mínimo. Não roda Neo4j/Redis.
> **ESAA:** github.com/elzobrito/ESAA — Event Sourcing for Autonomous Agents. Append-only .jsonl, SHA-256 verified projections, contracts YAML.

### TASK-050: Observabilidade — Analytics + Error Tracking ✅ (02/03/2026)
- [x] Self-hosted analytics: `/api/v1/analytics/pageview` + `/api/v1/analytics/summary`
- [x] Redis-backed: page views por dia, unique visitors (IP hash), hourly, 7-day history
- [x] Frontend tracking: App.tsx useLocation → POST pageview em cada navegação
- [x] Microsoft Clarity ativado (project ID: vpkwrlf847) — session recordings, heatmaps
- [x] Analytics dashboard page: `/app/analytics` (page views, UV, hourly, 7-day chart) ✅ (02/03/2026)
- [ ] Sentry para error tracking (ou self-hosted alternative)
> **Arquivos:** `api/src/bracc/routers/analytics.py`, `frontend/src/App.tsx`, `frontend/index.html`, `frontend/src/pages/Analytics.tsx`

### TASK-051: Avaliação De Olho em Você + Mission Control ✅ (02/03/2026)
- [x] De Olho em Você (deolhoemvoce.com.br): monitora emendas Pix, CEAP, votações
- [x] Aprendizado: adicionamos search_votacoes (como eles têm), Flock analytics (similar ao nosso self-hosted)
- [x] Vantagem deles: per-deputy profiles visuais, Emendas Pix específicas, AdSense
- [x] Vantagem nossa: Neo4j graph, CNPJ/sócios, gazette search, AI chatbot, open-source
- [x] Mission Control (builderz-labs): agent orchestration dashboard
- [x] Relevante para egos-lab (23 agents), NÃO para EGOS Inteligência
- [x] Ideias: cost tracking por agente, GitHub Issues sync, Kanban board
> **Similares avaliados:** comovotou.org, deolhonodeputado.app.br, Mika-IO/deolho

### TASK-052: Daily Update Policy ✅ (02/03/2026)
- [x] Documento criado: `docs/DAILY_UPDATE_POLICY.md`
- [x] Regra: 1 post/dia contendo tudo, exceto updates "importantes" (ver critérios)
- [x] Critérios de "importante": nova fonte de dados, feature UX, marco, incidente, contribuição externa
- [x] Template de post diário definido
- [x] Canais: Telegram, Discord, Website timeline

### TASK-053: Portal da Transparência + DataJud APIs ✅ (02/03/2026)
- [x] Portal da Transparência: chave `f6341a...` integrada (6 endpoints)
- [x] Servidores federais: nome, salário, cargo, órgão (requer CPF ou código SIAPE)
- [x] Contratos: fornecedor, valor, vigência, aditivos
- [x] Sanções: CEIS (inidôneas) + CNEP (punidas) — funciona sem filtros
- [x] CPGF, viagens, licitações (requerem filtros mínimos)
- [x] DataJud (CNJ): chave `cDZH...` integrada — todos os 27+ tribunais
- [x] Recuperação Judicial: 1.180 processos TJMG confirmados
- [x] Elasticsearch queries: match_phrase para classes processuais
> **Arquivos:** `api/src/bracc/services/transparency_tools.py`
> **Verificado:** CEIS, contratos, DataJud TJMG (Recuperação Judicial) — todos funcionando

### TASK-054: Avaliação OpenPlanter ✅ (02/03/2026)
- [x] OpenPlanter (ShinMegamiBoson): agente investigativo recursivo com TUI
- [x] 19 tools: file I/O, shell, web search (Exa), subtask delegation
- [x] Entity resolution cross-dataset, evidence-chain construction
- [x] Suporta GPT-5.2, Claude Opus 4.6, Qwen, Ollama local
- [x] Inspiração: sub-agent delegation, recursive investigations
- [x] Nosso diferencial: Neo4j 317K+ nós, 18 APIs, frontend web, open-source
> **Veredicto:** Ótima inspiração para multi-step investigations futuras. Não substitui.

### TASK-055: Auditoria de Features Intelink ✅ (02/03/2026)
- [x] Intelink tem 179 pages/routes em 17 seções
- [x] **Já adotamos:** Chat, Graph, Entity, Search, Investigation, Dashboard, Journey, Landing, Patterns, Baseline (10/17)
- [x] **Relevante adotar:** Analytics dashboard (visual), Reports generation, Alertas, Activity feed
- [x] **NÃO relevante (policial):** Delegacias, operações, membros, equipe, permissões, qualidade
- [x] **Conclusão:** Core investigativo está completo. Faltam features de UX/engagement.

### TASK-056: Mapa de Portais de Transparência ✅ (02/03/2026)
- [x] Pesquisa: PNTP (10.335 portais), Transparência Internacional (300+ cidades), Radar Transparente
- [x] 122 municípios SEM portal, 109 com 100%, média prefeituras 67%
- [x] Gaps: 95% sem API, 70% dados em PDF, 40% sem licitações
- [x] Padrão referência: Portal da Transparência federal (⭐⭐⭐⭐⭐)
- [x] Proposta: API REST mínima obrigatória, JSON, atualização diária
- [x] Próximas APIs: Dados Abertos SP, MG, ComprasNet, SIAFI, Senado
> **Documento:** `docs/reports/transparency-portal-map.md`

### TASK-057: Análise de Custos de APIs ✅ (02/03/2026)
- [x] ReceitaWS (R$99/mês): NÃO vale — nosso ETL 60GB tem mesmos dados, ilimitado, grátis
- [x] SerpAPI ($75/mês): CARO — substituído por Brave Search
- [x] Brave Search ($5/mês): MELHOR custo-benefício — #1 benchmark, 669ms, 2k grátis/mês
- [x] Exa ($49/mês): Já temos via MCP Cascade — usar para dev, não produção
- [x] Recomendação: Brave para chatbot produção, Exa para pesquisa interna
> **Economia:** R$1.188/ano evitando ReceitaWS, $840/ano evitando SerpAPI

### TASK-058: GitGuardian Fix — Chaves em Env Vars ✅ (02/03/2026)
- [x] Removidas chaves hardcoded de `transparency_tools.py` (alerta GitGuardian)
- [x] Chaves movidas para `docker-compose.yml` como env vars
- [x] PORTAL_TRANSPARENCIA_API_KEY, DATAJUD_API_KEY, BRAVE_API_KEY
- [x] Código usa `os.environ.get()` — chaves nunca mais no código fonte
> **Nota:** DataJud e Portal Transparência são chaves públicas (registro gratuito), mas best practice é env vars.

### TASK-059: Brave Search Integration ✅ (02/03/2026)
- [x] Brave Search API como busca primária (key de `/home/enio/egos-lab/.env`)
- [x] DuckDuckGo como fallback automático
- [x] #1 benchmark (14.89), 669ms latência, 2k queries grátis/mês
- [x] Issue #28 fechada com comentário

### TASK-060: Analytics Dashboard Frontend ✅ (02/03/2026)
- [x] Página `/app/analytics` com visualização em tempo real
- [x] Cards: views hoje, visitantes únicos, total all-time
- [x] Gráfico de barras: últimos 7 dias + distribuição por hora
- [x] Tabela: páginas mais visitadas
> **Arquivos:** `frontend/src/pages/Analytics.tsx`, `Analytics.module.css`

### TASK-061: Monitor Endpoints (Sanções + Auto-Report) ✅ (02/03/2026)
- [x] `GET /api/v1/monitor/sanctions/recent` — últimas sanções CEIS+CNEP
- [x] `GET /api/v1/monitor/report/{municipio}` — relatório automático por município
- [x] Testado: 20 sanções recentes retornadas, Patos de Minas report funcional
> **Arquivos:** `api/src/bracc/routers/monitor.py`

### TASK-062: Sincronização GitHub Issues ↔ Tasks ✅ (02/03/2026)
- [x] Issue #25 (Portal Transparência): CLOSED — integrado
- [x] Issue #26 (DataJud): CLOSED — integrado
- [x] Issue #27 (ReceitaWS): CLOSED wontfix — ETL melhor
- [x] Issue #28 (SerpAPI/Brave): CLOSED — Brave integrado
- [ ] Criar issues para novas tasks pendentes
- [ ] Automatizar sync (script ou GitHub Action)

### TASK-063: 3 Relatórios de Investigação Publicados ✅ (02/03/2026)
- [x] Report 01: SUPERAR LTDA (CNPJ 13.482.516/0001-61) — 7 sanções no grafo, QSA com PJ sócia
- [x] Report 02: Transparência Municipal Manaus — 15 emendas, 4.664 ACPs TJAM, diligences ambientais
- [x] Report 03: Recuperação Judicial SP — 3.704 processos TJSP, 10K+ exec fiscais
- [x] Cada relatório: passo a passo para leigos + stack técnica + custos + comparação Palantir
- [x] Publicados no site: `/reports/report-0X-*.md`
- [x] Update JSON v2 para timeline do site
> **Arquivos:** `docs/reports/report-01-superar-ltda.md`, `report-02-manaus-transparencia.md`, `report-03-recuperacao-judicial-sp.md`
> **Dados reais:** Neo4j 317K nós + Portal Transparência + DataJud + BrasilAPI

### TASK-064: Auditoria Profunda Intelink v2 ✅ (02/03/2026)
- [x] 44 páginas mapeadas (14 adotadas, 3 parciais, 15 gaps relevantes, 11 N/A policial)
- [x] 135 API routes analisadas (entities, reports, analysis, documents, OCR, legal, debate)
- [x] Top 10 features para adotar: Report Gen, Activity Feed, Evidence Chain, Chat Vision, Alerts, Analysis Suite
- [x] Features egos-lab para trazer: Rho Score, Eagle Eye, Cost Tracking
- [x] Comparação Palantir/NSA/i2: tabela completa
> **Documento:** `docs/reports/intelink-deep-audit.md`

### TASK-065: Fix CEIS API Filter ✅ (02/03/2026)
- [x] Bug: Portal Transparência CEIS ignora parâmetro `cnpjSancionado`
- [x] Fix: filtro client-side por CNPJ/nome após receber resultados
- [x] Testado: sanções agora filtradas corretamente por empresa
> **Arquivo:** `api/src/bracc/services/transparency_tools.py`

### TASK-066: Evidence Chain — Data Provenance per Query ✅ (02/03/2026)
- [x] Backend: EvidenceItem model (tool, source, query, result_count, timestamp, api_url)
- [x] 18 tools mapeados para nomes de fonte e URLs de API
- [x] Cada resposta do chatbot inclui `evidence_chain[]` com proveniência completa
- [x] Frontend: display colapsável "Fontes (N) | Custo: $X.XXXX" abaixo de cada resposta
- [x] Testado: SUPERAR LTDA → 2 evidence items (Neo4j + Brave Search)
> **Conceito Mycelium aplicado:** Cada dado tem trail auditável — de onde veio, quando, quantos resultados.
> **Arquivos:** `api/src/bracc/routers/chat.py`, `frontend/src/components/chat/ChatInterface.tsx`, `frontend/src/api/client.ts`

### TASK-067: Cost Tracking per Query ✅ (02/03/2026)
- [x] Gemini Flash pricing: $0.075/1M input, $0.30/1M output tokens
- [x] `cost_usd` calculado por query baseado em `usage.prompt_tokens` + `usage.completion_tokens`
- [x] Retornado na ChatResponse e exibido no frontend
- [x] Testado: query típica = $0.000552 (~R$ 0,003)
> **Insight:** Uma investigação completa com 6 tool calls custa ~$0.003 (~R$ 0,02). Para R$630/mês operamos ~210K queries.

### TASK-068: Correção de Custos nos Relatórios ✅ (02/03/2026)
- [x] Contabo VPS: $35/mês (não €15)
- [x] Supabase Pro: $20/mês
- [x] Windsurf IDE: $45/mês
- [x] OpenRouter LLM: ~$5/mês
- [x] Brave Search: $0-5/mês
- [x] TOTAL: ~$105/mês (~R$ 630) — antes constava R$ 120 (ERRADO)
- [x] Corrigido nos 3 relatórios publicados

### TASK-069: Análise Mycelium + Chat Vision + Prioridades ✅ (02/03/2026)
- [x] Chat Vision: NÃO AGORA — sistema usa APIs estruturadas, não imagens
- [x] Mycelium Event Bus: APLICÁVEL — evidence chain implementada como conceito
- [x] Mycelium ZKP/Shadow Nodes: NÃO AGORA — overengineering sem base de usuários
- [x] Cross-app events (Intelink ↔ Intel): PLANEJADO para próxima fase
- [x] Prioridades filtradas: só tasks com ROI real (Evidence Chain, Activity Feed, Eagle Eye)
> **Documento:** Análise entregue no chat + knowledge base

### TASK-070: Activity Feed — Mycelium Event Trail ✅ (02/03/2026)
- [x] Backend: `activity.py` router com `/api/v1/activity/feed` + `/api/v1/activity/stats`
- [x] In-memory event store (500 max, Redis upgrade futuro)
- [x] Chat endpoint loga cada query como evento de atividade
- [x] Cada evento: type, title, source, result_count, cost_usd, timestamp
- [x] Frontend: `/app/activity` com timeline real-time (refresh 15s)
- [x] Stats bar: total events, by type (chat/search/report), custo total
- [x] Filtro por tipo de evento (click no stat)
- [x] Sidebar: Clock icon + nav.activity i18n
- [x] Testado: chat query → evento logado → visível no feed
> **Conceito Mycelium:** Cada ação do sistema é um evento auditável — transparência total.
> **Arquivos:** `api/src/bracc/routers/activity.py`, `frontend/src/pages/Activity.tsx`

### TASK-071: Eagle Eye Gazette Monitor ✅ (02/03/2026)
- [x] Backend: `gazette_monitor.py` com `/api/v1/monitor/gazettes/scan` + `/patterns`
- [x] 8 padrões investigativos: dispensa, inexigibilidade, aditivo, emergência, sobrepreço, tomada de contas, sanção, licitação fracassada
- [x] 10 cidades SP com dados no Querido Diário (Botucatu, Santos, Campinas, etc.)
- [x] Alertas auto-logados no Activity Feed
- [x] Testado: 23 alertas em Botucatu em 7 dias
- [x] Bridge Eagle Eye (egos-lab) ↔ EGOS Intel (produção)
> **Próximo:** Cron automático + dashboard de alertas + mais cidades
> **Arquivo:** `api/src/bracc/routers/gazette_monitor.py`

### TASK-072: GitGuardian Fix + Security Hardening ✅ (02/03/2026)
- [x] Incidente: Brave API key vazou em `apps/openclaw/config.json.bak.1` (EGOSv5 repo)
- [x] Key rotacionada pelo usuário
- [x] `.gitignore`: adicionado `*.bak`, `*.bak.*`, `*.backup`, `*.old`, `config.json.bak*`
- [x] `security_scan.ts`: +5 padrões (Brave BSA..., JSON apiKey/token, Bearer, backup files)
- [x] Pre-commit agora bloqueia: backup files + 13 padrões de secrets + entropy check
- [x] Regras de deploy documentadas em memória (docker rebuild para novos módulos)
> **Root cause:** .bak file não estava no .gitignore

### TASK-073: Website Overhaul — SEO + Copy + Crawlers ✅ (02/03/2026)
- [x] SEO meta tags: OG, Twitter Card, Schema.org JSON-LD, AI crawler meta
- [x] `robots.txt`: permitir AI crawlers (GPTBot, ChatGPT-User, Anthropic, Google-Extended)
- [x] `sitemap.xml`: landing + 4 relatórios
- [x] Landing page: custo corrigido $36 → $105/mês
- [x] Header/navbar com links para Pesquisar, Relatórios, Estatísticas, GitHub ✅ (03/03/2026)
- [x] Copy melhorada: CTA "Abrir Plataforma" (era "Open Explorer"), GitHub URL atualizada ✅ (03/03/2026)
- [ ] OG image para compartilhamento em redes sociais
> **Arquivos:** `index.html`, `robots.txt`, `sitemap.xml`, `Landing.tsx`

### TASK-074: Chatbot Intelligence — Reports + Proactive ✅ (02/03/2026)
- [x] System prompt: awareness de 4 relatórios com URLs
- [x] 6 sugestões inteligentes no welcome (em vez de 4 genéricas)
- [x] Regras proativas: "NUNCA peça se pode buscar, INVESTIGUE primeiro"
- [x] Testado: agora lista relatórios corretamente quando perguntado
- [x] Usa tools antes de responder (evidence chain ativa)
- [ ] Chatbot ainda pede cidade para queries nacionais (emendas, supersalários)
- [ ] Memória entre mensagens (histórico de sessão)
- [ ] Mais testes de hallucination e edge cases
> **Arquivo:** `chat.py` (SYSTEM_PROMPT), `ChatInterface.tsx`

### TASK-075: Docker DNS Fix — Permanent ✅ (03/03/2026)
- [x] Root cause: systemd-resolved `nameserver 127.0.0.53` não funciona dentro de containers Docker
- [x] Fix: `/etc/docker/daemon.json` com DNS `8.8.8.8`, `8.8.4.4`, `1.1.1.1` + retry opts
- [x] `systemctl restart docker` — todos containers voltaram healthy
- [x] Verificado: `docker run --rm alpine cat /etc/resolv.conf` mostra DNS corretos
- [x] `docker compose build api --no-cache` agora funciona sem falhas intermitentes
> **Arquivo:** `/etc/docker/daemon.json` no Contabo 217.216.95.126

### TASK-076: GitHub Actions — Reduce Noise ✅ (03/03/2026)
- [x] CI workflow: mudou de `push: main` para `pull_request + weekly Monday + manual`
- [x] Security workflow: mudou de `push: main` para `pull_request + weekly Wednesday + manual`
- [x] Release Drafter: mudou de `push: main` para `manual only`
- [x] Resultado: sem mais notificações de falha em cada commit
> **Arquivos:** `.github/workflows/ci.yml`, `security.yml`, `release-drafter.yml`

### TASK-077: Website Header/Navbar ✅ (03/03/2026)
- [x] PublicShell: adicionado nav com links Pesquisar, Relatórios, Estatísticas, GitHub
- [x] CTA: "Abrir Plataforma" (era "Open Explorer")
- [x] GitHub URLs atualizadas de br-acc para EGOS-Inteligencia
- [x] Responsivo: nav escondido em mobile (<768px)
- [x] Frontend rebuilt e deployed no Contabo
> **Arquivos:** `PublicShell.tsx`, `PublicShell.module.css`, `Landing.tsx`

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
| **Issues GitHub abertas** | 27 | 02/03/2026 |
| **Tasks concluídas** | 60/85 | 03/03/2026 |
| **Chatbot Tools** | 18 (3 grafo + 8 livres + 6 Portal + 1 DataJud) | 02/03/2026 |
| **ETL Status** | Phase 1 file 6/10 (15%) — Contabo CPU | 02/03/2026 |
| **Website** | inteligencia.egos.ia.br (SSL ✅) | 02/03/2026 |
| **Analytics** | Self-hosted + Clarity + Dashboard frontend ✅ | 02/03/2026 |
| **Web Search** | Brave Search (primário) + DDG (fallback) | 02/03/2026 |
| **Issues GitHub** | 23 abertas (4 fechadas: #25-#28) | 02/03/2026 |
| **APIs com chave** | Portal Transparência + DataJud + Brave | 02/03/2026 |
| **Segurança** | GitGuardian fix — chaves em env vars | 02/03/2026 |
| **Relatórios** | 3 publicados (SUPERAR, Manaus, RJ-SP) | 02/03/2026 |
| **Intelink Audit** | 44 págs, 135 routes, 15 gaps relevantes | 02/03/2026 |
| **Evidence Chain** | Proveniência de dados em cada query ✅ | 02/03/2026 |
| **Cost/Query** | ~$0.0006/query (~R$ 0,003) | 02/03/2026 |
| **Custo Mensal Real** | ~$105/mês (~R$ 630) | 02/03/2026 |

### TASK-087: Branding — EGOS Logo as Favicon + OG Image ✅ (03/03/2026)
- [x] Generate favicon.ico (16/32/48px), favicon-16x16.png, favicon-32x32.png
- [x] Generate apple-touch-icon.png (180x180), android-chrome (192/512)
- [x] Generate og-image.png (1200x630) for social sharing previews
- [x] Create site.webmanifest (theme: #00e5a0, standalone)
- [x] Update index.html with all icon refs + OG image + Twitter image
- [x] Deploy to Contabo — all assets returning HTTP 200
> **Source:** `/home/enio/Downloads/egos_discord_icon_1771941656007.png`
> **Arquivos:** `index.html`, `favicon.ico`, `site.webmanifest`, `og-image.png`

### TASK-088: First Community PR — Benford's Law + HHI Patterns ✅ (03/03/2026)
- [x] PR #30 by @mrncstt: 2 new intelligence patterns (+134/-2 lines)
- [x] Benford's Law: flags contract values deviating from expected leading-digit distribution (MAD threshold)
- [x] HHI Concentration: flags companies with high Herfindahl-Hirschman Index across contracting agencies
- [x] Code review: approved with minor observations (precision, performance, scaling docs)
- [x] Merged to main, API rebuild deployed
- [x] Test count: 8→10 patterns, 48 unit tests passing
> **Milestone:** First external contributor! ~70 GitHub stars 🎉
> **Arquivos:** `config.py`, `pattern.py`, `intelligence_provider.py`, 2 new `.cypher` files

### TASK-086: UI Fix — Scrolling + Analytics Improvement ✅ (03/03/2026)
- [x] Root cause: AppShell.module.css `.main` had `overflow: hidden` — killed scrolling on ALL app pages
- [x] Fix: changed to `overflow: auto` — Reports, Activity, Analytics all scroll now
- [x] Analytics: aggregate entity analysis URLs into single group (was polluting 200+ entries)
- [x] Analytics: added note about in-memory data persistence (resets on API restart)
- [x] Analytics data verified REAL: 4607 views, 20 unique visitors, 80 activity events
- [x] Contract tests: 9/9 endpoints passing (health, search, chat, cache, analytics, activity, 422, 404)
> **Arquivos:** `AppShell.module.css`, `Analytics.tsx`

### TASK-078: Crash Prevention — Defensive Frontend ✅ (03/03/2026)
- [x] Root cause: SourceRegistry crashed on placeholder sources.json (no sources array)
- [x] 14 files fixed: ?? [] guards on entity_ids, sources, entities, categories
- [x] Neo4j retry on startup: 30 attempts with 2-30s backoff (dependencies.py)
- [x] API healthcheck in docker-compose (Python urllib, 60s start_period)
- [x] Caddy depends on API+Frontend healthy before routing traffic
- [x] Pre-commit hook v2: warns on unsafe .length/.map without ?? guard
- [x] Memory saved: defensive coding rules for EGOS Inteligência
> **Impact:** 94% of requests were 502 errors before fix. Now 100% healthy.
> **Arquivos:** dependencies.py, docker-compose.yml, SourceRegistry.tsx, 13 more components

### TASK-079: Novas Fontes — ComexStat (MDIC) ⬜ (P2)
- [ ] ETL: API REST api-comexstat.mdic.gov.br — importação/exportação por CNPJ/NCM/município
- [ ] Grafo: Empresa ↔ Município ↔ Produto (NCM) ↔ Fluxo comercial
- [ ] Detecção: dumping, triangulação, crescimento anômalo de importações
> **Fonte:** https://api-comexstat.mdic.gov.br/docs
> **LGPD:** Dados agregados por empresa (CNPJ), 100% público

### TASK-080: Novas Fontes — ANM (Mineração + CFEM) ⬜ (P2)
- [ ] ETL: API/CSV da Agência Nacional de Mineração
- [ ] Grafo: Empresa ↔ Título Minerário ↔ Município ↔ Royalties CFEM
- [ ] Cruzar com sanções, contratos, DOU
> **Fonte:** https://www.gov.br/anm/pt-br/acesso-a-informacao/dados-abertos
> **LGPD:** Registro público (Lei 227/1967)

### TASK-081: Novas Fontes — SALIC / Lei Rouanet ⬜ (P2)
- [ ] ETL: API api.salic.cultura.gov.br — projetos culturais + captação + patrocinadores
- [ ] Grafo: CNPJ/Proponente ↔ Projeto ↔ Captação ↔ Patrocinador
- [ ] LGPD: masking extra para proponentes pessoa física
> **Fonte:** https://api.salic.cultura.gov.br/docs

### TASK-082: Novas Fontes — CADE (Concorrência) ⬜ (P2)
- [ ] ETL: dados abertos CADE — processos + multas + TCCs
- [ ] Grafo: Empresa ↔ Processo CADE ↔ Multa ↔ TCC
- [ ] Cruzar com contratos públicos e sanções
> **Fonte:** https://www.gov.br/cade/pt-br/centrais-de-conteudo/cade-em-numeros

### TASK-083: Novas Fontes — INPI (Propriedade Industrial) ⬜ (P2)
- [ ] ETL: dados abertos INPI — patentes, marcas, desenhos industriais
- [ ] Grafo: Empresa ↔ Patente/Marca ↔ Setor
> **Fonte:** https://www.gov.br/inpi/pt-br (dados abertos)
> **LGPD:** Registro público (Lei 9.279/1996)

### TASK-084: Novas Fontes — GLEIF (Identificador Global) ⬜ (P3)
- [ ] ETL: API GLEIF — LEI (Legal Entity Identifier) + ownership chains
- [ ] Entity resolution cross-border: conectar CNPJs a LEIs globais
- [ ] Enriquecer offshores ICIJ com dados GLEIF
> **Fonte:** https://www.gleif.org/en/lei-data/gleif-api

### TASK-085: Novas Fontes — TCEs/TCMs (Tribunais de Contas) ⬜ (P3)
- [ ] Mapear portais de dados abertos dos 33 TCEs + TCMs
- [ ] ETL: licitações, contratos, folhas de pagamento estaduais/municipais
- [ ] Grafo: Empresa ↔ Contrato Estadual/Municipal ↔ Servidor
> **Impacto:** Expande cobertura além do federal para estados e municípios

---

*"Siga o dinheiro público. Dados abertos, código aberto."*
