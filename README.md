# EGOS Inteligência — Plataforma Aberta de Cruzamento de Dados Públicos

<!-- RHO_BADGE --> **Rho Score:** 🟡 0.30 (WARNING) | Contributors: 4 | Commits (30d): 94 | Updated: 2026-03-02 <!-- /RHO_BADGE -->

Idioma: **Português (Brasil)** | [English](#english)

[![Licença: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![API Status](https://img.shields.io/badge/API-ONLINE-brightgreen)](http://217.216.95.126/health)
[![Discord Bot](https://img.shields.io/badge/Discord-EGOS%20Intelig%C3%AAncia-7289da)](https://discord.gg/egos)
[![Telegram Bot](https://img.shields.io/badge/Telegram-@EGOSin__bot-26A5E4)](https://t.me/EGOSin_bot)

> **Em uma frase:** O EGOS Inteligência conecta dados públicos do Brasil (empresas, políticos, contratos, sanções, doações eleitorais) em um grafo interativo que mostra quem se relaciona com quem.

Site: [inteligencia.egos.ia.br](https://inteligencia.egos.ia.br) | Ecossistema: [EGOS](https://egos.ia.br) | Comunidade: [@ethikin](https://t.me/ethikin)

---

## Origem e Diferenças

Este projeto é um **fork** do [World-Open-Graph/br-acc](https://github.com/World-Open-Graph/br-acc), uma infraestrutura open-source para dados públicos brasileiros em grafo.

O EGOS Inteligência diverge significativamente do upstream:

| Aspecto | Upstream (br-acc) | EGOS Inteligência |
|---|---|---|
| **Idioma** | Inglês | Português-BR nativo |
| **Interface** | Desktop-only, requer login | Mobile-first, público, chatbot AI |
| **Dados carregados** | Demo/seed | 278k nós + 53.6M empresas (ETL em andamento) |
| **Bots AI** | Nenhum | Discord + Telegram (14 ferramentas OSINT) |
| **Investigações** | Não | Upload, fork, compartilhamento público |
| **Relatórios** | Não | 11 relatórios publicados (ex: Patense R$217M BNDES) |
| **Infraestrutura** | Local/demo | Contabo VPS (12 vCPU, 48GB RAM) + Redis |
| **LGPD** | Parcial | CPF bloqueado em todo o sistema, masking middleware |
| **Fontes planejadas** | 13 | 79 fontes no roadmap |
| **Algoritmos** | Básico | PageRank, Benford, HHI, Community Detection (roadmap) |
| **Ecossistema** | Standalone | Integrado ao [EGOS Framework](https://egos.ia.br) (24 agentes AI) |

Mantemos rastreamento do upstream e contribuímos PRs quando aplicável.

---

## Para Que Serve?

Imagine que você quer saber: **"A empresa que ganhou a licitação do hospital tem alguma ligação com o político que aprovou a verba?"**

Hoje, você precisaria acessar dezenas de portais diferentes (Receita Federal, TSE, Portal da Transparência...) e cruzar manualmente.

O EGOS Inteligência faz isso automaticamente:

1. **Coleta** dados de 38+ fontes oficiais do governo brasileiro
2. **Conecta** em um grafo de relacionamentos
3. **Revela** vínculos de forma visual, pesquisável e compartilhável

### O Que Já Está Dentro

| O Que | Fonte | Volume |
|---|---|---|
| Empresas e sócios | CNPJ (Receita Federal) | 53,6M empresas (ETL em andamento) |
| Doações eleitorais | TSE | 7,1M registros (2002-2024) |
| Contratos federais | Portal da Transparência + ComprasNet | 1,1M contratos |
| Empresas punidas | CEIS, TCU, IBAMA, CVM | 150k sanções |
| Dívidas com a União | PGFN | 24M débitos |
| Diário Oficial | DOU | 3,98M atos |
| Gastos de deputados | Câmara (CEAP) | 4,6M despesas |
| Offshores | ICIJ (Panama/Paradise/Pandora Papers) | 4,8k entidades |
| PEPs | CGU + OpenSanctions | 252k registros |
| Processos no STF | STF | 2,38M casos |
| Patrimônio de candidatos | TSE Bens | 14,3M bens declarados |

**Meta: 141M nós e 92M conexões.** Status atual: 278.501 nós carregados, CNPJ ETL em progresso.

> **Importante:** Padrões encontrados são **sinais**, não prova jurídica. Toda conclusão requer revisão humana.

---

## Quero Usar!

### Opção 1: Chatbot AI (Sem Instalar Nada)

O assistente EGOS Inteligência está disponível 24/7 via:

- **Website:** [inteligencia.egos.ia.br](https://inteligencia.egos.ia.br) — chatbot direto na página inicial
- **Discord:** [Servidor EGOS](https://discord.gg/egos) → mencione `@EGOS Intelligence`
- **Telegram:** [@EGOSin_bot](https://t.me/EGOSin_bot)

Exemplos de perguntas:
```
Quais os vínculos da empresa CNPJ 11.222.333/0001-81?
Quanto a empresa X recebeu do BNDES?
Busque licitações de saúde em São Paulo
Quem são os maiores supersalários do TJSP?
```

**14 ferramentas OSINT integradas:**

| Ferramenta | O Que Faz | Fonte |
|---|---|---|
| `egos_meta_stats` | Estatísticas gerais do grafo | EGOS Inteligência |
| `egos_company_graph` | Grafo de vínculos por CNPJ | EGOS Inteligência |
| `egos_company_patterns` | Padrões de risco de empresa | EGOS Inteligência |
| `bndes_search` | Financiamentos do BNDES (2002-presente) | BNDES Dados Abertos |
| `fetch_top_earners` | Maiores supersalários do Judiciário | Extrateto |
| `check_specific_member` | Dados de servidor público | Extrateto |
| `get_member_history` | Histórico de pagamentos | Extrateto |
| `list_orgaos` | Ranking de órgãos do Judiciário | Extrateto |
| `list_estados` | Estatísticas por estado | Extrateto |
| `search_gazettes` | Diários oficiais de 5.570+ municípios | Querido Diário |
| `search_licitacoes` | Licitações e pregões | Querido Diário |
| `search_contratos` | Contratos públicos | Querido Diário |
| `web_search` | Busca web em tempo real | Exa AI |
| `brazil_news_search` | Notícias recentes do Brasil | Exa AI |

### Opção 2: API Pública

```bash
# Estatísticas gerais
curl http://217.216.95.126/api/v1/public/meta

# Grafo de vínculos de uma empresa
curl http://217.216.95.126/api/v1/public/graph/company/11222333000181
```

| Método | Rota | O Que Faz |
|---|---|---|
| GET | `/health` | Verifica se o servidor está online |
| GET | `/api/v1/public/meta` | Estatísticas do grafo |
| GET | `/api/v1/public/graph/company/{cnpj}` | Grafo de vínculos por CNPJ |
| POST | `/api/v1/chat` | Chat conversacional (em desenvolvimento) |

### Opção 3: Rodar Localmente

```bash
git clone https://github.com/enioxt/br-acc.git
cd br-acc
cp .env.example .env  # Edite NEO4J_PASSWORD

cd infra && docker compose up -d
# Aguarde Neo4j ficar healthy (~30s)

export NEO4J_PASSWORD=sua_senha
bash infra/scripts/seed-dev.sh
```

- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000/health
- **Neo4j Browser:** http://localhost:7474

---

## Arquitetura

```
[79 Fontes Planejadas] → [ETL Python] → [Neo4j Grafo] → [FastAPI + Redis] → [React + Bots AI]
```

| Componente | Tecnologia |
|---|---|
| **Banco de Dados** | Neo4j 5 Community (grafo) |
| **Cache** | Redis 7 (512MB LRU, cache-aside) |
| **Backend** | FastAPI (Python 3.12, assíncrono) |
| **Frontend** | React 19 + Vite (mobile-first) |
| **ETL** | Python com pandas (45 pipelines) |
| **Bots** | Discord.js + Telegraf + AI Router (OpenRouter) |
| **Infra** | Docker Compose + Caddy + Contabo VPS |

---

## Modos de Operação

| Variável | Padrão | O Que Controla |
|---|---|---|
| `PUBLIC_MODE` | `true` | Modo público ativado |
| `PUBLIC_ALLOW_PERSON` | `false` | Bloqueia entidades de pessoa física |
| `PATTERNS_ENABLED` | `false` | Desabilita detecção de padrões |

### Conformidade LGPD

- **CPF é bloqueado em TODO o sistema** — busca, exibição, exportação
- Middleware de masking intercepta qualquer CPF que escape para respostas JSON
- Apenas dados de pessoa jurídica (CNPJ) e dados já públicos por lei são exibidos
- Pessoa física aparece apenas por nome (sem documento), quando vinculada a cargo público (PEP)

---

## Roadmap

Veja [ROADMAP.md](ROADMAP.md) para o plano completo. Destaques:

| Fase | Status | O Que |
|---|---|---|
| **CNPJ ETL** | 🔵 Em andamento | 53.6M empresas da Receita Federal |
| **Chatbot AI** | 🔵 Em desenvolvimento | Interface conversacional no website |
| **Redis Cache** | ✅ Pronto | Cache-aside para queries frequentes |
| **GDS Algoritmos** | 🟡 Planejado | PageRank, Community Detection, Shortest Path |
| **Investigações** | 🟡 Planejado | Upload, fork, compartilhamento, exportação |
| **Journey Tracker** | 🟡 Planejado | Rastreamento de passos de investigação |
| **79 Fontes** | 🟡 Gradual | DataJud, IBGE, DENATRAN, reguladoras... |

---

## Quero Contribuir!

| Nível | O Que Fazer | Precisa Programar? |
|---|---|---|
| **Iniciante** | Tradução, documentação, reportar bugs | Não |
| **Intermediário** | Pipelines ETL para novas fontes | Sim (Python) |
| **Avançado** | Algoritmos de anomalia, queries Cypher | Sim (Python + Neo4j) |

**Issues abertas:** [github.com/enioxt/br-acc/issues](https://github.com/enioxt/br-acc/issues) — várias marcadas como `good first issue` e `help wanted`

---

## Infraestrutura & Custos (Transparência Total)

| Serviço | O Quê | Custo (USD/mês) |
|---|---|---|
| **Contabo VPS** | 12 vCPU, 48GB RAM, 500GB SSD — Neo4j, Redis, API, bots, frontend | $35 |
| **Vercel** | egos.ia.br, inteligencia.egos.ia.br | Free |
| **Supabase** | PostgreSQL (conversas, relatórios, custos) | Free |
| **OpenRouter** | Gemini 2.0 Flash para IA dos bots | Free |
| **Domínio** | egos.ia.br | ~$0.60 |
| **Total** | Plataforma OSINT completa + 2 bots AI + website | **~$36/mo** |

> 100% autofinanciado. Se achar útil, considere apoiar: [egos.ia.br](https://egos.ia.br)

---

## Legal & Ética

- [Política de Ética](ETHICS.md) — usos proibidos, linguagem neutra
- [LGPD](LGPD.md) — tratamento de dados pessoais
- [Termos de Uso](TERMS.md)
- [Aviso Legal](DISCLAIMER.md) — sinais ≠ prova jurídica
- [Privacidade](PRIVACY.md)
- [Segurança](SECURITY.md) — reportar vulnerabilidades
- [Resposta a Abuso](ABUSE_RESPONSE.md)

## Licença

[GNU Affero General Public License v3.0](LICENSE) — código aberto, copyleft.

---

<a name="english"></a>

# English

EGOS Inteligência is an open-source platform for cross-referencing Brazilian public data, built on a graph database connecting companies, politicians, contracts, sanctions, and electoral donations.

**Forked from** [World-Open-Graph/br-acc](https://github.com/World-Open-Graph/br-acc) with significant divergence: mobile-first UI, AI chatbot, LGPD-compliant CPF blocking, 14 OSINT tools via Discord/Telegram bots, 79 planned data sources, and integration with the [EGOS Framework](https://egos.ia.br) (24 AI agents).

## Live Infrastructure

| Service | Status | URL |
|---|---|---|
| **Public API** | ✅ Online | http://217.216.95.126/health |
| **Frontend** | ✅ Online | [inteligencia.egos.ia.br](https://inteligencia.egos.ia.br) |
| **Discord Bot** | ✅ Online (14 OSINT tools) | `@EGOS Intelligence` |
| **Telegram Bot** | ✅ Online (14 OSINT tools) | [@EGOSin_bot](https://t.me/EGOSin_bot) |

## Quick Start

```bash
git clone https://github.com/enioxt/br-acc.git && cd br-acc
cp .env.example .env  # set NEO4J_PASSWORD
cd infra && docker compose up -d
export NEO4J_PASSWORD=your_password && bash infra/scripts/seed-dev.sh
```

## Key Differences from Upstream

- LGPD-compliant: CPF search/display blocked system-wide
- Mobile-first responsive design with bottom navigation
- AI chatbot as primary interface (not just search)
- 14 OSINT tools via Discord + Telegram bots
- 278,501 nodes loaded + 53.6M CNPJ ETL in progress
- Redis cache layer for performance
- 11 real investigation reports published
- Investigation upload, fork, and sharing (planned)
- 79 data sources on roadmap (vs 13 upstream)
- Integrated with EGOS ecosystem (24 AI agents, MCP tools)

## LGPD Compliance

CPF (Brazilian personal tax ID) is **never** searchable, displayable, or exportable. Only CNPJ (company ID) and publicly mandated data are exposed. All JSON responses pass through a CPF masking middleware as a safety net.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) · [ROADMAP.md](ROADMAP.md) · [Issues](https://github.com/enioxt/br-acc/issues)

## License

[GNU Affero General Public License v3.0](LICENSE)

---

*"Dados públicos são sinais, não prova jurídica. Nossa missão é torná-los acessíveis a todos."*
