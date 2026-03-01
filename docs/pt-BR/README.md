# BR/ACC Open Graph — Dados Públicos do Brasil em Grafo

[![BRACC Header](../brand/bracc-header.jpg)](../brand/bracc-header.jpg)

Idioma: [English](../../README.md) | **Português (Brasil)**

[![CI](https://github.com/World-Open-Graph/br-acc/actions/workflows/ci.yml/badge.svg)](https://github.com/World-Open-Graph/br-acc/actions/workflows/ci.yml)
[![Licença: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

> **Em uma frase:** O BR/ACC conecta dados públicos do Brasil (empresas, políticos, contratos, sanções, doações eleitorais) em um grafo que mostra quem se relaciona com quem.

Site: [bracc.org](https://bracc.org) | Iniciativa: [World Open Graph](https://worldopengraph.com)

---

## Para Que Serve?

Imagine que você quer saber: **"A empresa que ganhou a licitação do hospital tem alguma ligação com o político que aprovou a verba?"**

Hoje, para responder isso, você precisaria acessar dezenas de portais diferentes (Receita Federal, TSE, Portal da Transparência, Diários Oficiais...) e cruzar os dados manualmente.

O BR/ACC faz isso automaticamente. Ele:

1. **Coleta** dados de 38+ fontes oficiais do governo brasileiro
2. **Conecta** esses dados em um grafo de relacionamentos (quem é sócio de quem, quem doou para quem, quem contratou quem)
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
| Offshores (Panama Papers etc) | ICIJ | 4,8 mil entidades |
| Pessoas politicamente expostas | CGU + OpenSanctions | 252 mil registros |
| Processos no STF | STF | 2,38 milhões de casos |
| Patrimônio de candidatos | TSE Bens | 14,3 milhões de bens declarados |
| Filiações partidárias | TSE Filiados | 16,5 milhões de filiações |

**Total: 141 milhões de nós e 92 milhões de conexões.**

> **Importante:** Padrões encontrados nos dados são **sinais**, não prova jurídica. Toda conclusão de alto risco exige revisão humana.

---

## Como Funciona (Arquitetura)

```
[38+ Fontes Oficiais] → [ETL Python] → [Neo4j Grafo] → [API FastAPI] → [Frontend React]
```

- **Banco de Dados:** Neo4j 5 (banco de grafo — especializado em conexões)
- **Backend:** FastAPI (Python 3.12, assíncrono)
- **Frontend:** React 19 + Vite + visualização de grafo interativa
- **ETL:** Python com pandas — coleta, limpa e carrega os dados
- **Infra:** Docker Compose (roda tudo com um comando)

---

## Quero Usar! Como Começo?

### Opção 1: Usar os Bots (Sem Instalar Nada)

Os dados do BR/ACC estão disponíveis via bots de mensagem que explicam tudo em linguagem simples:

- **Discord:** [Servidor EGOS](https://discord.gg/egos) — bot `@EGOS Intelligence`
- **Telegram:** [@ethikin](https://t.me/ethikin)
- **WhatsApp:** Em breve

Basta perguntar: *"Quais os vínculos da empresa CNPJ 00.000.000/0001-00?"*

### Opção 2: Rodar Localmente (Para Desenvolvedores)

```bash
# 1. Clone o repositório
git clone https://github.com/World-Open-Graph/br-acc.git
cd br-acc

# 2. Configure
cp .env.example .env
# Edite o .env e defina NEO4J_PASSWORD

# 3. Suba tudo com Docker
make dev

# 4. Carregue os dados de exemplo
export NEO4J_PASSWORD=sua_senha
make seed
```

Depois de rodar:
- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000/health
- **Neo4j Browser:** http://localhost:7474

### Opção 3: Hospedar Seu Próprio Servidor (Para Organizações)

Para rodar o dataset completo (141M nós), você precisa de:
- **Mínimo:** 32GB RAM, 500GB SSD, 8 vCPUs
- **Recomendado:** 64GB RAM, 1TB NVMe, 16 vCPUs

Opções de hospedagem acessíveis:

| Provedor | Config | Preço/mês | Observação |
|---|---|---|---|
| Contabo VPS | 8 vCPU, 30GB RAM, 200GB | ~R$130/mês | Mais barato, pode ser apertado |
| Hetzner CCX33 | 8 vCPU, 32GB RAM, 240GB | ~R$170/mês | Melhor custo-benefício |
| Hetzner AX42 | Dedicated, 64GB RAM, 1TB NVMe | ~R$280/mês | Ideal para produção |
| Oracle Cloud Free | 4 ARM, 24GB RAM | Grátis | Limitado, apenas para testes |

---

## API Pública

| Método | Rota | O Que Faz |
|---|---|---|
| GET | `/health` | Verifica se o servidor está online |
| GET | `/api/v1/public/meta` | Mostra quantos dados estão carregados e saúde das fontes |
| GET | `/api/v1/public/graph/company/{cnpj}` | Retorna o grafo de vínculos de uma empresa (sócios, contratos, sanções) |
| GET | `/api/v1/public/patterns/company/{cnpj}` | Análise de padrões de risco (desabilitado no modo público por segurança) |

---

## Modos de Operação

O BR/ACC tem modos de segurança para proteger a privacidade:

| Variável | Padrão Público | O Que Controla |
|---|---|---|
| `PUBLIC_MODE` | `true` | Modo público ativado |
| `PUBLIC_ALLOW_PERSON` | `false` | Bloqueia busca por CPF/pessoa |
| `PATTERNS_ENABLED` | `false` | Desabilita engine de detecção de padrões |

Esses defaults existem para cumprir a LGPD e evitar uso indevido.

---

## Quero Contribuir!

Contribuições são muito bem-vindas. Leia o [CONTRIBUTING.md](CONTRIBUTING.md) para detalhes.

### Formas de Contribuir

| Nível | O Que Fazer | Precisa Programar? |
|---|---|---|
| **Iniciante** | Melhorar traduções, documentação, reportar bugs | Não |
| **Intermediário** | Criar pipelines ETL para novas fontes de dados | Sim (Python) |
| **Avançado** | Algoritmos de detecção de anomalias, otimização de queries Cypher | Sim (Python + Neo4j) |

### Issues Abertas para Tradução (Voluntários)

Veja as issues marcadas com `translation` e `good first issue` no [painel de issues](../../issues).

---

## Ética e Legal

Este projeto trata dados públicos com responsabilidade. Leia:

- [Política de Ética](ETHICS.md) — usos proibidos, linguagem não acusatória
- [LGPD](LGPD.md) — como tratamos dados pessoais
- [Termos de Uso](TERMS.md) — condições de uso da plataforma
- [Aviso Legal](DISCLAIMER.md) — sinais ≠ prova jurídica
- [Privacidade](PRIVACY.md) — política de privacidade
- [Segurança](SECURITY.md) — como reportar vulnerabilidades
- [Resposta a Abuso](ABUSE_RESPONSE.md) — o que acontece em caso de uso indevido

## Licença

[GNU Affero General Public License v3.0](../../LICENSE) — código aberto, copyleft.
Qualquer modificação distribuída publicamente deve manter a mesma licença.

---

*"Dados públicos são sinais, não prova jurídica. Nossa missão é torná-los acessíveis a todos."*
