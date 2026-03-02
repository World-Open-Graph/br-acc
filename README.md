# BR/ACC Open Graph — Dados Públicos do Brasil em Grafo

<!-- RHO_BADGE --> **Rho Score:** 🟡 0.30 (WARNING) | Contributors: 4 | Commits (30d): 94 | Updated: 2026-03-02 <!-- /RHO_BADGE -->

[![BRACC Header](docs/brand/bracc-header.jpg)](docs/brand/bracc-header.jpg)

Idioma: **Português (Brasil)** | [English](#english)

[![CI](https://github.com/World-Open-Graph/br-acc/actions/workflows/ci.yml/badge.svg)](https://github.com/World-Open-Graph/br-acc/actions/workflows/ci.yml)
[![Licença: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![API Status](https://img.shields.io/badge/API-ONLINE-brightgreen)](http://217.216.95.126/health)
[![Discord Bot](https://img.shields.io/badge/Discord-EGOS%20Intelligence-7289da)](https://discord.gg/egos)

> **Em uma frase:** O BR/ACC conecta dados públicos do Brasil (empresas, políticos, contratos, sanções, doações eleitorais) em um grafo que mostra quem se relaciona com quem.

Site: [bracc.org](https://bracc.org) | Iniciativa: [World Open Graph](https://worldopengraph.com) | Upstream: [World-Open-Graph/br-acc](https://github.com/World-Open-Graph/br-acc)

> **Este fork** é mantido pela comunidade [EGOS](https://egos.ia.br) com foco em: tradução PT-BR, acessibilidade para leigos, integração com bots (Discord/Telegram/WhatsApp) e algoritmos de detecção de anomalias. Todas as contribuições são enviadas como PR ao repositório original.

---

## Status do Servidor (LIVE)

| Serviço | Status | URL |
|---|---|---|
| **API Pública** | ✅ Online | http://217.216.95.126/health |
| **Frontend** | ✅ Online | http://217.216.95.126 |
| **Neo4j** | ✅ Healthy (48GB RAM) | Interno |
| **Discord Bot** | ✅ Online (13 tools) | `@EGOS Intelligence#2881` |
| **Telegram Bot** | ✅ Online (13 tools) | [@EGOSin_bot](https://t.me/EGOSin_bot) |

**Servidor:** Contabo VPS 40 — 12 vCPU, 48GB RAM, 250GB NVMe

---

## Para Que Serve?

Imagine que você quer saber: **"A empresa que ganhou a licitação do hospital tem alguma ligação com o político que aprovou a verba?"**

Hoje, para responder isso, você precisaria acessar dezenas de portais diferentes (Receita Federal, TSE, Portal da Transparência, Diários Oficiais...) e cruzar os dados manualmente.

O BR/ACC faz isso automaticamente:

1. **Coleta** dados de 38+ fontes oficiais do governo brasileiro
2. **Conecta** esses dados em um grafo de relacionamentos
3. **Mostra** os vínculos de forma visual e pesquisável

### O Que Já Está Dentro

| O Que | Fonte | Volume |
|---|---|---|
| Empresas e sócios | CNPJ (Receita Federal) | 53,6 milhões de empresas |
| Doações eleitorais | TSE | 7,1 milhões de registros (2002-2024) |
| Contratos federais | Portal da Transparência + ComprasNet | 1,1 milhão de contratos |
| Empresas punidas | CEIS, TCU, IBAMA, CVM | 150 mil sanções |
| Dívidas com a União | PGFN | 24 milhões de débitos |
| Diário Oficial | DOU | 3,98 milhões de atos |
| Gastos de deputados | Câmara (CEAP) | 4,6 milhões de despesas |
| Offshores (Panama/Paradise Papers) | ICIJ | 4,8 mil entidades |
| Pessoas politicamente expostas | CGU + OpenSanctions | 252 mil registros |
| Processos no STF | STF | 2,38 milhões de casos |
| Patrimônio de candidatos | TSE Bens | 14,3 milhões de bens declarados |
| Filiações partidárias | TSE Filiados | 16,5 milhões de filiações |

**Meta: 141 milhões de nós e 92 milhões de conexões.**

**Status atual (2026-03-02): 278.501 nós e 30.916 conexões carregados.** Faltam CNPJ (53.6M), DataJud (80M+) e fontes financeiras para atingir a meta.

> **Importante:** Padrões encontrados nos dados são **sinais**, não prova jurídica. Toda conclusão de alto risco exige revisão humana.

Para a matriz legal completa de datasets, veja: [Matriz de Bases Públicas Brasil](docs/pt-BR/datasets/matriz-bases-publicas-brasil.md)

---

## Quero Usar! Como Começo?

### Opção 1: Usar os Bots (Sem Instalar Nada)

Os dados do BR/ACC estão disponíveis via bots de mensagem que respondem em português:

**Discord:** Entre no [Servidor EGOS](https://discord.gg/egos) e mencione `@EGOS Intelligence`

Exemplos de perguntas:
```
@EGOS Intelligence quais os vínculos da empresa CNPJ 11222333000181?
@EGOS Intelligence quais são as estatísticas do BR/ACC?
@EGOS Intelligence busque licitações de saúde em São Paulo
@EGOS Intelligence quem são os maiores supersalários do TJSP?
```

Os bots têm **13 ferramentas OSINT** integradas:

| Ferramenta | O Que Faz | Fonte |
|---|---|---|
| `bracc_meta_stats` | Estatísticas gerais do grafo | BR/ACC |
| `bracc_company_graph` | Grafo de vínculos de empresa por CNPJ | BR/ACC |
| `bracc_company_patterns` | Padrões de risco de empresa | BR/ACC |
| `fetch_top_earners` | Maiores supersalários do Judiciário | Extrateto |
| `check_specific_member` | Dados de servidor público específico | Extrateto |
| `get_member_history` | Histórico mensal de pagamentos | Extrateto |
| `list_orgaos` | Ranking de órgãos do Judiciário | Extrateto |
| `list_estados` | Estatísticas por estado | Extrateto |
| `search_gazettes` | Busca em diários oficiais de 5.570+ municípios | Querido Diário |
| `search_licitacoes` | Busca de licitações e pregões | Querido Diário |
| `search_contratos` | Busca de contratos públicos | Querido Diário |
| `web_search` | Busca web contextualizada | Exa AI |
| `task_persist` | Auto-criação de issues a partir de feedback | GitHub API |

**Telegram:** [@EGOSin_bot](https://t.me/EGOSin_bot) — ✅ Online 24/7 (mesmas 13 ferramentas)

**WhatsApp:** Em planejamento (Evolution API)

### Opção 2: Rodar Localmente (Desenvolvedores)

```bash
git clone https://github.com/enioxt/br-acc.git
cd br-acc
cp .env.example .env
# Edite o .env e defina NEO4J_PASSWORD

cd infra && docker compose up -d
# Aguarde Neo4j ficar healthy (~30s)

export NEO4J_PASSWORD=sua_senha
bash infra/scripts/seed-dev.sh
```

Depois de rodar:
- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000/health
- **Neo4j Browser:** http://localhost:7474

### Opção 3: Usar Nossa API Pública

A API está online e acessível:

```bash
# Estatísticas gerais
curl http://217.216.95.126/api/v1/public/meta

# Grafo de vínculos de uma empresa
curl http://217.216.95.126/api/v1/public/graph/company/11222333000181
```

---

## Como Funciona

```
[38+ Fontes Oficiais] → [ETL Python] → [Neo4j Grafo] → [API FastAPI] → [Frontend React + Bots]
```

| Componente | Tecnologia |
|---|---|
| **Banco de Dados** | Neo4j 5 Community (grafo) |
| **Backend** | FastAPI (Python 3.12, assíncrono) |
| **Frontend** | React 19 + Vite + grafo interativo |
| **ETL** | Python com pandas (45 pipelines) |
| **Bots** | Discord.js + AI Router (OpenRouter) |
| **Infra** | Docker Compose + Caddy |

---

## API Pública

| Método | Rota | O Que Faz |
|---|---|---|
| GET | `/health` | Verifica se o servidor está online |
| GET | `/api/v1/public/meta` | Estatísticas: total de dados carregados |
| GET | `/api/v1/public/graph/company/{cnpj}` | Grafo de vínculos de uma empresa |
| GET | `/api/v1/public/patterns/company/{cnpj}` | Padrões de risco (desabilitado no modo público) |

---

## Modos de Operação

| Variável | Padrão | O Que Controla |
|---|---|---|
| `PUBLIC_MODE` | `true` | Modo público ativado |
| `PUBLIC_ALLOW_PERSON` | `false` | Bloqueia busca por CPF/pessoa |
| `PATTERNS_ENABLED` | `false` | Desabilita detecção de padrões |

Esses defaults cumprem a LGPD e evitam uso indevido.

---

## Quero Contribuir!

Contribuições são muito bem-vindas. Veja [CONTRIBUTING.md](CONTRIBUTING.md) e o [ROADMAP.md](ROADMAP.md).

| Nível | O Que Fazer | Precisa Programar? |
|---|---|---|
| **Iniciante** | Tradução, documentação, reportar bugs | Não |
| **Intermediário** | Pipelines ETL para novas fontes de dados | Sim (Python) |
| **Avançado** | Algoritmos de anomalia, queries Cypher | Sim (Python + Neo4j) |

**Issues abertas:** [github.com/enioxt/br-acc/issues](https://github.com/enioxt/br-acc/issues) — várias marcadas como `good first issue`

### O Que Este Fork Adiciona

- ✅ README PT-BR acessível para leigos
- ✅ Servidor público com API online (48GB RAM, Contabo VPS)
- ✅ 278.501 nós carregados (PEPs, sanções, empresas, OpenSanctions)
- ✅ Bot Discord com 13 ferramentas OSINT (24/7)
- ✅ Bot Telegram @EGOSin_bot com 13 ferramentas OSINT (24/7)
- ✅ Auto-criação de GitHub Issues a partir de feedback dos usuários
- ✅ ROADMAP público com coordenação de tasks
- ✅ 5 relatórios de investigação reais publicados
- 🔵 Tradução completa do frontend (i18next)
-  Algoritmos: Lei de Benford, HHI
- 🟡 ETL: Extrateto (salários do judiciário)
- 🟡 Bot WhatsApp (Evolution API)
- 🟡 MCP Server para IDEs AI

### Infraestrutura & Custos (Transparência Total)

| Serviço | O Quê | Custo Mensal |
|---------|-------|-------------|
| **Contabo VPS** | Neo4j (278k nós), 2 bots AI, frontend, API, Caddy SSL | ~€10/mês |
| **Vercel** | egos.ia.br (Mission Control), APIs serverless | Free tier |
| **Supabase** | PostgreSQL para eventos, tasks, custos | Free tier |
| **OpenRouter** | Gemini 2.0 Flash para IA dos bots | ~$5/mês |
| **Domínio** | egos.ia.br | ~R$40/ano |
| **Total** | Plataforma OSINT completa + 2 bots AI + website | **~$15/mês** |

**Por que Contabo?** Neo4j na nuvem custa $65+/mês. Contabo dá 8 vCPU, 48GB RAM, 500GB SSD por €10. Quando carregarmos CNPJ (53.6M empresas) + DataJud (80M processos), vamos precisar dessa capacidade.

**Por que dados locais?** APIs do governo são rate-limited, frequentemente fora do ar (Receita Federal está offline há 3+ dias), e retornam 403/400 em requisições de alto volume. Dados locais = cruzamento em milissegundos, sem dependências externas.

---

## Ética e Legal

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

BR/ACC Open Graph is an open-source graph infrastructure for Brazilian public data intelligence, built by [World Open Graph](https://worldopengraph.com).

This fork is maintained by the [EGOS](https://egos.ia.br) community, focused on: PT-BR translation, accessibility for non-technical users, bot integrations (Discord/Telegram/WhatsApp), and anomaly detection algorithms. All contributions are submitted as PRs to the [upstream repository](https://github.com/World-Open-Graph/br-acc).

## Live Infrastructure

| Service | Status | URL |
|---|---|---|
| **Public API** | ✅ Online | http://217.216.95.126/health |
| **Frontend** | ✅ Online | http://217.216.95.126 |
| **Discord Bot** | ✅ Online (13 OSINT tools) | `@EGOS Intelligence#2881` |
| **Telegram Bot** | ✅ Online (13 OSINT tools) | [@EGOSin_bot](https://t.me/EGOSin_bot) |

## Quick Start

```bash
git clone https://github.com/enioxt/br-acc.git && cd br-acc
cp .env.example .env  # set NEO4J_PASSWORD
cd infra && docker compose up -d
export NEO4J_PASSWORD=your_password && bash infra/scripts/seed-dev.sh
```

## What This Fork Adds

- 278,501 nodes loaded (PEPs, sanctions, companies, OpenSanctions)
- Full PT-BR translation (docs, frontend, API errors)
- Public server with live API (48GB RAM, Contabo VPS)
- Discord + Telegram bots with 13 OSINT tools via EGOS AI Router
- Auto-GitHub-Issue creation from user feedback
- 5 real investigation reports published
- Anomaly detection: Benford's Law, HHI (in progress)
- ETL pipeline: Extrateto judiciary salaries (in progress)
- Public ROADMAP with task coordination
- Full infrastructure cost transparency (~$15/mo total)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) · [ROADMAP.md](ROADMAP.md) · [Issues](https://github.com/enioxt/br-acc/issues)

## Legal & Ethics

[ETHICS.md](ETHICS.md) · [LGPD.md](LGPD.md) · [PRIVACY.md](PRIVACY.md) · [TERMS.md](TERMS.md) · [DISCLAIMER.md](DISCLAIMER.md) · [SECURITY.md](SECURITY.md) · [ABUSE_RESPONSE.md](ABUSE_RESPONSE.md)

## License

[GNU Affero General Public License v3.0](LICENSE)

---

*"Dados públicos são sinais, não prova jurídica. Nossa missão é torná-los acessíveis a todos."*
