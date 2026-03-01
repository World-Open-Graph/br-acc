# BR/ACC Open Graph — Dados Públicos do Brasil em Grafo

[![BRACC Header](docs/brand/bracc-header.jpg)](docs/brand/bracc-header.jpg)

Idioma: **Português (Brasil)** | [English](#english)

[![CI](https://github.com/World-Open-Graph/br-acc/actions/workflows/ci.yml/badge.svg)](https://github.com/World-Open-Graph/br-acc/actions/workflows/ci.yml)
[![Licença: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

> **Em uma frase:** O BR/ACC conecta dados públicos do Brasil (empresas, políticos, contratos, sanções, doações eleitorais) em um grafo que mostra quem se relaciona com quem.

Site: [bracc.org](https://bracc.org) | Iniciativa: [World Open Graph](https://worldopengraph.com) | Upstream: [World-Open-Graph/br-acc](https://github.com/World-Open-Graph/br-acc)

> **Este fork** é mantido pela comunidade [EGOS](https://egos.ia.br) com foco em: tradução PT-BR, acessibilidade para leigos, integração com bots (Discord/Telegram/WhatsApp) e algoritmos de detecção de anomalias. Todas as contribuições são enviadas como PR ao repositório original.

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

**Total: 141 milhões de nós e 92 milhões de conexões.**

> **Importante:** Padrões encontrados nos dados são **sinais**, não prova jurídica. Toda conclusão de alto risco exige revisão humana.

Para a matriz legal completa de datasets, veja: [Matriz de Bases Públicas Brasil](docs/pt-BR/datasets/matriz-bases-publicas-brasil.md)

---

## Como Funciona

```
[38+ Fontes Oficiais] → [ETL Python] → [Neo4j Grafo] → [API FastAPI] → [Frontend React]
```

| Componente | Tecnologia |
|---|---|
| **Banco de Dados** | Neo4j 5 Community (grafo — especializado em conexões) |
| **Backend** | FastAPI (Python 3.12, assíncrono) |
| **Frontend** | React 19 + Vite + visualização de grafo interativa |
| **ETL** | Python com pandas — coleta, limpa e carrega os dados |
| **Infra** | Docker Compose (roda tudo com um comando) |

---

## Quero Usar! Como Começo?

### Opção 1: Usar os Bots (Sem Instalar Nada)

Os dados do BR/ACC estão disponíveis via bots de mensagem que respondem em português:

- **Discord:** [Servidor EGOS](https://discord.gg/egos) — bot `@EGOS Intelligence`
- **Telegram:** [@ethikin](https://t.me/ethikin)
- **WhatsApp:** Em breve

Pergunte: *"Quais os vínculos da empresa CNPJ 00.000.000/0001-00?"*

### Opção 2: Rodar Localmente (Desenvolvedores)

```bash
git clone https://github.com/enioxt/br-acc.git
cd br-acc
cp .env.example .env
# Edite o .env e defina NEO4J_PASSWORD

make dev

export NEO4J_PASSWORD=sua_senha
make seed
```

Depois de rodar:
- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000/health
- **Neo4j Browser:** http://localhost:7474

### Opção 3: Hospedar Seu Próprio Servidor

Para o dataset completo (141M nós): mínimo 32GB RAM, recomendado 48-64GB.

| Provedor | Config | Preço/mês |
|---|---|---|
| **Contabo VPS 40** | 12 vCPU, 48GB RAM, 250GB NVMe | ~R$143/mês |
| Contabo VPS 30 | 8 vCPU, 24GB RAM, 200GB NVMe | ~R$80/mês |
| Hetzner CCX33 | 8 vCPU ded., 32GB RAM, 240GB | ~R$275/mês |
| Oracle Cloud Free | 4 ARM, 24GB RAM | Grátis (testes) |

Guia completo de setup: em breve em [egos.ia.br/guia](https://egos.ia.br/guia)

---

## API Pública

| Método | Rota | O Que Faz |
|---|---|---|
| GET | `/health` | Verifica se o servidor está online |
| GET | `/api/v1/public/meta` | Estatísticas: quantos dados estão carregados |
| GET | `/api/v1/public/graph/company/{cnpj}` | Grafo de vínculos de uma empresa |
| GET | `/api/v1/public/patterns/company/{cnpj}` | Padrões de risco (desabilitado no modo público) |

---

## Modos de Operação

O BR/ACC protege a privacidade com feature flags:

| Variável | Padrão | O Que Controla |
|---|---|---|
| `PUBLIC_MODE` | `true` | Modo público ativado |
| `PUBLIC_ALLOW_PERSON` | `false` | Bloqueia busca por CPF/pessoa |
| `PATTERNS_ENABLED` | `false` | Desabilita detecção de padrões |

Esses defaults cumprem a LGPD e evitam uso indevido.

---

## Mapa do Repositório

| Pasta | O Que Tem |
|---|---|
| `api/` | FastAPI — rotas, queries Cypher, serviços |
| `etl/` | Pipelines ETL — coleta e carrega dados no Neo4j |
| `frontend/` | React — explorador visual do grafo |
| `infra/` | Docker Compose, bootstrap do Neo4j |
| `scripts/` | Scripts operacionais e de validação |
| `docs/` | Documentação, legal, datasets |

---

## Quero Contribuir!

Contribuições são muito bem-vindas. Veja [CONTRIBUTING.md](CONTRIBUTING.md).

| Nível | O Que Fazer | Precisa Programar? |
|---|---|---|
| **Iniciante** | Tradução, documentação, reportar bugs | Não |
| **Intermediário** | Pipelines ETL para novas fontes de dados | Sim (Python) |
| **Avançado** | Algoritmos de anomalia, queries Cypher otimizadas | Sim (Python + Neo4j) |

**Issues abertas:** [ver issues](https://github.com/enioxt/br-acc/issues) — várias marcadas como `good first issue`

### O Que Este Fork Adiciona (em desenvolvimento)

- Tradução completa PT-BR (docs, frontend, API)
- Bots conversacionais (Discord, Telegram, WhatsApp)
- Algoritmos: Lei de Benford, HHI (concentração de fornecedores)
- Pipeline ETL: Extrateto (salários do judiciário)
- MCP Server para IDEs (Cursor, Windsurf, Claude)
- Copy acessível para não-programadores

---

## Ética e Legal

- [Política de Ética](ETHICS.md) — usos proibidos, linguagem neutra
- [LGPD](LGPD.md) — tratamento de dados pessoais
- [Termos de Uso](TERMS.md) — condições de uso
- [Aviso Legal](DISCLAIMER.md) — sinais ≠ prova jurídica
- [Privacidade](PRIVACY.md)
- [Segurança](SECURITY.md) — reportar vulnerabilidades
- [Resposta a Abuso](ABUSE_RESPONSE.md)
- [Índice Legal](docs/legal/legal-index.md)

## Licença

[GNU Affero General Public License v3.0](LICENSE) — código aberto, copyleft.

---

<a name="english"></a>

# English

BR/ACC Open Graph is an open-source graph infrastructure for Brazilian public data intelligence, built by [World Open Graph](https://worldopengraph.com).

This fork is maintained by the [EGOS](https://egos.ia.br) community, focused on: PT-BR translation, accessibility for non-technical users, bot integrations (Discord/Telegram/WhatsApp), and anomaly detection algorithms. All contributions are submitted as PRs to the [upstream repository](https://github.com/World-Open-Graph/br-acc).

## Quick Start

```bash
git clone https://github.com/enioxt/br-acc.git
cd br-acc
cp .env.example .env
# set NEO4J_PASSWORD

make dev

export NEO4J_PASSWORD=your_password
make seed
```

- API: `http://localhost:8000/health`
- Frontend: `http://localhost:3000`
- Neo4j Browser: `http://localhost:7474`

## Architecture

- **Graph DB:** Neo4j 5 Community
- **Backend:** FastAPI (Python 3.12+, async)
- **Frontend:** Vite + React 19 + TypeScript
- **ETL:** Python (pandas, httpx)
- **Infra:** Docker Compose

## API Surface

| Method | Route | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/v1/public/meta` | Aggregated metrics and source health |
| GET | `/api/v1/public/graph/company/{cnpj_or_id}` | Public company subgraph |
| GET | `/api/v1/public/patterns/company/{cnpj_or_id}` | `503` while pattern engine is disabled |

## What This Fork Adds

- Full PT-BR translation (docs, frontend, API errors)
- Conversational bots (Discord, Telegram, WhatsApp) via EGOS AI Router
- Anomaly detection: Benford's Law, HHI (supplier concentration)
- ETL pipeline: Extrateto (judiciary salaries)
- MCP Server for IDEs
- Accessible copy for non-programmers

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Open issues: [github.com/enioxt/br-acc/issues](https://github.com/enioxt/br-acc/issues)

## Legal & Ethics

[ETHICS.md](ETHICS.md) · [LGPD.md](LGPD.md) · [PRIVACY.md](PRIVACY.md) · [TERMS.md](TERMS.md) · [DISCLAIMER.md](DISCLAIMER.md) · [SECURITY.md](SECURITY.md) · [ABUSE_RESPONSE.md](ABUSE_RESPONSE.md)

## License

[GNU Affero General Public License v3.0](LICENSE)

---

*"Dados públicos são sinais, não prova jurídica. Nossa missão é torná-los acessíveis a todos."*

*"Public data patterns are signals, not legal proof. Our mission is to make them accessible to everyone."*
