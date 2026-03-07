# BR-ACC CLI

CLI oficial do projeto `br-acc` para operar o ambiente local, consultar a API publica, executar ETLs e acessar relatorios gerados pelo repositorio.

## O que ela faz

- Centraliza comandos de desenvolvimento que hoje estao espalhados entre `docker compose`, scripts shell e utilitarios do projeto.
- Facilita consultas rapidas ao grafo pela API publica.
- Encapsula comandos de ETL mais usados.
- Exibe relatorios locais gerados em `audit-results/`.

## Requisitos

- Python `>=3.12`
- Docker com `docker compose`
- Variaveis de ambiente do projeto configuradas, especialmente `NEO4J_PASSWORD`

## Instalacao

No diretorio raiz do repositorio:

```bash
python -m pip install -e ./cli
```

Depois disso, o comando `bracc` fica disponivel no ambiente Python em uso.

Se preferir rodar sem instalar o script global:

```bash
cd cli
python -m bracc_cli.main --help
```

## Configuracao

A CLI le configuracoes do ambiente e dos arquivos `.env` da raiz do repositorio e de `cli/`.

Variaveis suportadas:

- `BRACC_API_URL`: URL base da API. Default: `http://localhost:8000`
- `BRACC_REPO_ROOT`: caminho da raiz do repositorio. Normalmente nao precisa definir
- `NEO4J_PASSWORD`: senha usada para seed e comandos de ETL

Exemplo:

```bash
BRACC_API_URL=http://localhost:8000
NEO4J_PASSWORD=changeme
```

## Estrutura de comandos

```bash
bracc
├─ dev
│  ├─ up
│  ├─ down
│  ├─ restart
│  └─ seed
├─ health
├─ api
│  ├─ meta
│  ├─ company
│  └─ patterns
├─ etl
│  ├─ list
│  ├─ run
│  ├─ run-all
│  └─ status
└─ report
   ├─ latest
   └─ list
```

## Uso

### Ambiente local

Subir a stack principal:

```bash
bracc dev up
```

Parar a stack:

```bash
bracc dev down
```

Reiniciar:

```bash
bracc dev restart
```

Carregar seed de desenvolvimento:

```bash
bracc dev seed
```

Observacao: `bracc dev seed` exige `NEO4J_PASSWORD`. Em Windows, a CLI tenta usar `bash` ou `sh`; se nao encontrar, faz fallback para `docker exec` no container `bracc-neo4j`.

### Healthcheck

Verificar API e Neo4j:

```bash
bracc health
```

Saida esperada:

```text
API: OK
Neo4j: OK
```

### Consultas na API

Metadados publicos:

```bash
bracc api meta
```

Grafo de uma empresa:

```bash
bracc api company 12345678000199
```

Com profundidade customizada:

```bash
bracc api company 12345678000199 --depth 3
```

Padroes de uma empresa:

```bash
bracc api patterns 12345678000199
```

Trocar idioma da resposta:

```bash
bracc api patterns 12345678000199 --lang en
```

### ETL

Listar pipelines disponiveis:

```bash
bracc etl list
```

Executar um pipeline:

```bash
bracc etl run cnpj
```

Executar todos os pipelines padrao da CLI:

```bash
bracc etl run-all
```

Executar um subconjunto:

```bash
bracc etl run-all cnpj tse transparencia
```

Ver status de ingestao:

```bash
bracc etl status
```

Observacoes:

- Os comandos de ETL usam `uv run bracc-etl` quando `uv` estiver disponivel.
- Se `uv` nao existir no `PATH`, a CLI tenta usar `bracc-etl` diretamente.
- `bracc etl run` e `bracc etl status` exigem `NEO4J_PASSWORD`.

### Relatorios

Mostrar o ultimo resumo de `bootstrap-all`:

```bash
bracc report latest
```

Listar arquivos em `audit-results/`:

```bash
bracc report list
```

## Desenvolvimento

Arquivos principais:

- `cli/pyproject.toml`
- `cli/bracc_cli/main.py`
- `cli/bracc_cli/config.py`
- `cli/bracc_cli/commands/dev.py`
- `cli/bracc_cli/commands/health.py`
- `cli/bracc_cli/commands/api.py`
- `cli/bracc_cli/commands/etl.py`
- `cli/bracc_cli/commands/report.py`

Para inspecionar a arvore de comandos:

```bash
bracc --help
```

Ou:

```bash
python -m bracc_cli.main --help
```

## Estado atual

A implementacao atual cobre:

- operacao do ambiente local
- healthcheck da API e do Neo4j
- consultas `meta`, `company` e `patterns`
- execucao basica de ETL
- leitura de relatorios locais

Ainda depende de a stack local estar rodando para comandos HTTP e de os artefatos existirem para comandos de relatorio.
