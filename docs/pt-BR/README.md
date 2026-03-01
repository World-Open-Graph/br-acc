# BR/ACC Open Graph

[![BRACC Header](../brand/bracc-header.jpg)](../brand/bracc-header.jpg)

Idioma: [English](../../README.md) | **Português (Brasil)**

[![CI](https://github.com/World-Open-Graph/br-acc/actions/workflows/ci.yml/badge.svg)](https://github.com/World-Open-Graph/br-acc/actions/workflows/ci.yml)
[![Licença: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

BR/ACC Open Graph é uma infraestrutura open source de grafo para inteligência de dados públicos.  
Site principal: [bracc.org](https://bracc.org)

BR/ACC Open Graph é uma iniciativa da [World Open Graph](https://worldopengraph.com).  
Este repositório contém o código completo da edição pública do BR/ACC.

## O Que o BR/ACC Representa

- Infraestrutura de interesse público para transparência.
- Ingestão e processamento reprodutíveis de registros públicos.
- Sinais investigativos com cautela metodológica explícita.

Padrões em dados públicos são sinais, não prova jurídica.

## O Que Existe Neste Repositório

- API pública (`api/`)
- Pipelines ETL e downloaders (`etl/`, `scripts/`)
- Frontend de exploração (`frontend/`)
- Infraestrutura e bootstrap de schema (`infra/`)
- Documentação, pacote legal e gates de release (`docs/`, políticas na raiz)

## Arquitetura (Resumo)

- Banco de Grafo: Neo4j 5 Community
- Backend: FastAPI (Python 3.12+, async)
- Frontend: Vite + React 19 + TypeScript
- ETL: Python (pandas, httpx)
- Infra: Docker Compose

## Quick Start

```bash
cp .env.example .env
# defina ao menos NEO4J_PASSWORD

make dev

export NEO4J_PASSWORD=sua_senha
make seed
```

## Docker (Local)

Suba tudo com Docker Compose (Neo4j + API + Frontend):

```bash
cp .env.example .env
# defina ao menos NEO4J_PASSWORD (e JWT_SECRET_KEY se for criar usuários)

docker compose -f infra/docker-compose.yml --env-file .env up --build
```

- API: `http://localhost:8000/health`
- Frontend: `http://localhost:3000`
- Neo4j Browser: `http://localhost:7474`

## Criar Usuário (API)

O cadastro é via `/api/v1/auth/register`. Se `INVITE_CODE` estiver definido, envie no payload.

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"<development-email>","password":"<development-pass>","invite_code":""}'
```

Para login e obtenção do token:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=<development-email>&password=<development-pass>'
```

- API: `http://localhost:8000/health`
- Frontend: `http://localhost:3000`
- Neo4j Browser: `http://localhost:7474`

## Mapa do Repositório

- `api/`: app FastAPI, rotas e carregamento de queries Cypher
- `etl/`: definição de pipelines e runtime ETL
- `frontend/`: aplicação React para exploração do grafo
- `infra/`: inicialização do Neo4j e infra relacionada
- `scripts/`: scripts operacionais e de validação
- `docs/`: documentação legal, de release e de datasets

## Modos de Operação / Defaults Públicos

Use estes defaults para deploy público:

- `PRODUCT_TIER=community`
- `PUBLIC_MODE=true`
- `PUBLIC_ALLOW_PERSON=false`
- `PUBLIC_ALLOW_ENTITY_LOOKUP=false`
- `PUBLIC_ALLOW_INVESTIGATIONS=false`
- `PATTERNS_ENABLED=false`
- `VITE_PUBLIC_MODE=true`
- `VITE_PATTERNS_ENABLED=false`

## Desenvolvimento

```bash
# dependências
cd api && uv sync --dev
cd ../etl && uv sync --dev
cd ../frontend && npm install

# qualidade
make check
make neutrality
```

## Superfície da API

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/v1/public/meta` | Métricas agregadas e saúde das fontes |
| GET | `/api/v1/public/graph/company/{cnpj_or_id}` | Subgrafo público de empresa |
| GET | `/api/v1/public/patterns/company/{cnpj_or_id}` | Retorna `503` enquanto o engine de patterns está desabilitado |

## Como Contribuir

Contribuições são bem-vindas. Comece por [CONTRIBUTING.md](CONTRIBUTING.md) para fluxo, gates de qualidade e expectativas de revisão.

## Contribuidores

- Time Core do BR/ACC — mantenedores
- OpenAI Codex — colaborador de engenharia com assistência de IA

## Legal e Ética

- [../../ETHICS.md](../../ETHICS.md) / [ETHICS.md](ETHICS.md)
- [../../LGPD.md](../../LGPD.md) / [LGPD.md](LGPD.md)
- [../../PRIVACY.md](../../PRIVACY.md) / [PRIVACY.md](PRIVACY.md)
- [../../TERMS.md](../../TERMS.md) / [TERMS.md](TERMS.md)
- [../../DISCLAIMER.md](../../DISCLAIMER.md) / [DISCLAIMER.md](DISCLAIMER.md)
- [../../SECURITY.md](../../SECURITY.md) / [SECURITY.md](SECURITY.md)
- [../../ABUSE_RESPONSE.md](../../ABUSE_RESPONSE.md) / [ABUSE_RESPONSE.md](ABUSE_RESPONSE.md)
- [../legal/legal-index.md](../legal/legal-index.md) / [legal-index.md](legal-index.md)

## Licença

[GNU Affero General Public License v3.0](LICENSE)
