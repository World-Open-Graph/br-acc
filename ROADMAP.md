# BR/ACC — Roadmap de Integração de Dados

> **Visão:** Construir o maior grafo aberto de relações entre entidades públicas e privadas do Brasil,
> cruzando 79+ bases de dados públicas para detectar padrões de corrupção, conflitos de interesse e
> desvios — tudo open source, verificável e acessível a qualquer cidadão.

> **Inspiração:** OpenSanctions (2.1M entidades, 297 fontes), Aleph/OCCRP (270M entidades),
> ICIJ DataShare, GRAS (World Bank), Alice (CGU), Serenata de Amor.

---

## Status Atual (2026-03-02)

| Métrica | Valor |
|---|---|
| **Nós no grafo** | 317.583 (crescendo — CNPJ ETL em andamento, meta: 90M+) |
| **Relacionamentos** | 34.507 |
| **Empresas** | 11.597 (CNPJ 53.6M em carregamento via ETL) |
| **Sanções carregadas** | 23.847 (CEIS + CNEP) |
| **OpenSanctions** | 4.136.365 entidades |
| **PEP** | 133.859 Pessoas Expostas Politicamente |
| **TSE** | Candidaturas + Doações + Bens (2022+2024, 1.7GB) |
| **ICIJ Offshore Leaks** | 73MB baixado (Panama/Pandora Papers) |
| **CNPJ Receita Federal** | 🔄 26GB extraído no Contabo, ETL Phase 1 em andamento |
| **DataJud CNJ** | Script pronto para 80M+ processos judiciais |
| **Pipelines ETL prontos** | 46 |
| **Bot Discord** | 14 ferramentas OSINT + fallback de modelos |
| **Bot Telegram** | 14 ferramentas OSINT (@EGOSin_bot) |
| **Bot IA** | Gemini 2.0 Flash (free) → fallback pago, memória persistente |
| **Servidor** | Contabo Cloud VPS 40 SSD — 12 vCPU, 48GB RAM, 500GB SSD ($35/mo) |
| **Custo total** | $36/mês (100% autofinanciado, sem grants) |
| **Frontend** | bracc.egos.ia.br — público, sem login, stats em tempo real |
| **Investigações** | Patense v2 publicado (R$217M BNDES, 4 empresas, 563 ops) |
| **Performance** | Scripts prontos: Neo4j 16G heap + 22G pagecache + 12 indexes |
| **Framework** | Construído com EGOS (egos.ia.br) — 24 agentes, MCP tools |

---

## Mapa de Dados: 79 Fontes

### Legenda

- ✅ **Carregado** — Dados no Neo4j, consultáveis via API/bot
- 📥 **Baixado** — Dados no servidor, ETL pendente
- 🔧 **Pipeline pronto** — Script de download + ETL existe, precisa rodar
- ⬜ **Precisa pipeline** — Fonte identificada, pipeline não existe ainda
- 🚫 **Bloqueado** — Requer captcha/JS, download manual via navegador

### Grupo 1: Sanções e Controle (PRIORIDADE MÁXIMA)

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 21 | CEIS (CGU) | ✅ Carregado | 22k sanções | CPF/CNPJ → Empresa/Pessoa |
| 22 | CNEP (CGU) | ✅ Carregado | 1.5k sanções | CPF/CNPJ → Empresa/Pessoa |
| 23 | CEPIM (CGU) | ✅ Carregado | 3.5k ONGs | CNPJ → ONG bloqueada |
| 24 | CEAF (CGU) | ✅ Carregado | 4.1k servidores | CPF → Servidor expulso |
| 78 | TCU Auditorias | 🔧 Pipeline pronto | Variável | CNPJ → Irregularidade |
| 79 | TCEs/TCMs | ⬜ Precisa pipeline | Variável por estado | CNPJ/CPF → Auditoria estadual |
| — | Acordos de Leniência | ✅ Carregado | 146 acordos | CNPJ → Acordo |
| — | PEP CGU | ✅ Carregado | 133k PEPs | CPF → Cargo político |
| — | OpenSanctions | ✅ Carregado | 4.1M entidades | Global → BR cross-ref |
| — | ICIJ Offshore | 📥 Baixado | 73MB | Offshore → BR empresas |
| — | OFAC (EUA) | 🔧 Pipeline pronto | ~12k | Sanções US → BR |
| — | UN Sanctions | 🔧 Pipeline pronto | ~1k | Sanções ONU → BR |

### Grupo 2: Empresas e Sociedade

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 5 | CNPJ/QSA Receita | ⏳ Baixando (23% de 60GB) | 53.6M empresas | CNPJ → Sócios → CPF |
| 6 | Juntas Comerciais | ⬜ Precisa pipeline | Variável | Atos societários |
| — | Holdings (participações) | 🔧 Pipeline pronto | Variável | CNPJ → Controla → CNPJ |

### Grupo 3: Mercado Financeiro (CVM/B3/BCB)

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 7 | CVM Aberta | 🔧 Pipeline pronto | ~50k docs | CNPJ → Registro CVM |
| 8 | Form. Referência CVM | ⬜ Precisa pipeline | Grande | Administradores → CPF |
| 9 | Fatos Relevantes CVM | ⬜ Precisa pipeline | ~10k/ano | Empresa → Evento relevante |
| 10 | Insider Trading CVM | ⬜ Precisa pipeline | Variável | CPF → Negociação suspeita |
| 11 | Fundos CVM | 🔧 Pipeline pronto | ~30k fundos | CNPJ fundo → Gestor |
| 12 | B3 Negociações | ⬜ Precisa pipeline | Enorme | Ticker → Volume/Preço |
| 13 | BCB Câmbio/PTAX | 🔧 Pipeline pronto | Séries | Fluxo cambial |
| 14 | BCB Selic/Juros | 🔧 Pipeline pronto | Séries | Benchmark |
| 15 | BCB PIX | ⬜ Precisa pipeline | Agregado | Volume transacional |
| 16 | BCB Crédito | 🔧 Pipeline pronto | Séries | Crédito por setor |
| 17 | BCB IFData | 🔧 Pipeline pronto | ~2k IFs | CNPJ → Balanço IF |
| 18 | BCB Base Monetária | 🔧 Pipeline pronto | Séries | M1/M2/M3 |
| 19 | BCB Reservas | 🔧 Pipeline pronto | Séries | Reservas internacionais |
| 20 | BCB Capitais Estrangeiros | 🔧 Pipeline pronto | Variável | Fluxo estrangeiro |
| — | BNDES Financiamentos | 🔧 Pipeline pronto | ~500k | CNPJ → Financiamento público |

### Grupo 4: Compras Públicas e Orçamento

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 25 | ComprasNet/PNCP | 🔧 Pipeline pronto | Grande | CNPJ → Contrato gov |
| 26 | SIAFI | ⬜ Precisa pipeline | Enorme | Execução orçamentária |
| 27 | SICONFI | 🔧 Pipeline pronto | Variável | Município → Finanças |
| 28 | SIOP | 🔧 Pipeline pronto | Variável | Planejamento orçamentário |
| 1 | Portal Dados Abertos | 🔧 Pipeline pronto | Meta-dados | Hub de datasets |
| 2 | Portal Transparência | 🔧🚫 Pipeline pronto, download manual | Grande | Gastos federais |
| 3 | Tesouro Transparente | ⬜ Precisa pipeline | Séries | Dívida pública |
| 4 | Base dos Dados | ⬜ Precisa pipeline | Meta-plataforma | Acesso simplificado |
| — | CPGF (Cartão Gov) | ✅ Carregado | 9.6k transações | CPF servidor → Gasto |
| — | Viagens Gov | ✅ Carregado | 14.2k viagens | CPF → Viagem gov |
| — | TransfereGov | 🔧 Pipeline pronto | Grande | Transferências federais |
| — | Renúncias fiscais | 🔧 Pipeline pronto | ~100k | CNPJ → Incentivo fiscal |

### Grupo 5: Político-Eleitoral (TSE)

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 29 | TSE Candidaturas | ✅ Carregado (2022+2024) | ~500k/eleição | CPF → Candidato |
| 30 | TSE Bens | ✅ Carregado (2022+2024) | ~1M declarações | CPF → Patrimônio declarado |
| 31 | TSE Doações | ✅ Carregado (2022+2024) | ~5M doações | CNPJ/CPF → Doação → Candidato |
| 32 | TSE Resultados | ⬜ Precisa pipeline | ~500k | Candidato → Resultado |
| — | TSE Filiados | 🔧 Pipeline pronto | ~16M | CPF → Partido |

### Grupo 6: Legislativo

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| — | Câmara dos Deputados | 🔧 Pipeline pronto | ~50k gastos | Deputado → Gasto |
| — | Senado Federal | 🔧 Pipeline pronto | ~20k gastos | Senador → Gasto |
| — | CPIs (Câmara + Senado) | 🔧 Pipeline pronto | ~500 | CPI → Investigado |

### Grupo 7: Diários Oficiais

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 33 | DOU | 🔧 Pipeline pronto | ~10k/dia | Texto → Entidade citada |
| 34 | DOEs Estaduais | ⬜ Precisa pipeline | Variável | Texto → Entidade citada |
| 35 | Querido Diário | 🔧 Pipeline pronto | 5.570+ municípios | Texto → Entidade citada |

### Grupo 8: Judiciário

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 42 | DataJud CNJ | 🔧 Pipeline pronto | ~80M processos | CPF/CNPJ → Processo |
| — | STF Decisões | 🔧 Pipeline pronto | ~200k | Processo → Decisão |

### Grupo 9: Saúde

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 36 | DATASUS SIH | 🔧 Pipeline pronto | Grande | CNES → Internação |
| 37 | DATASUS SIM | 🔧 Pipeline pronto | ~1.5M/ano | Mortalidade |
| 38 | DATASUS CNES | 🔧 Pipeline pronto | ~330k estab. | CNPJ → Estabelecimento saúde |
| 39 | DATASUS SINAN | 🔧 Pipeline pronto | Variável | Notificações compulsórias |

### Grupo 10: Educação

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 51 | INEP Censo Escolar | 🔧 Pipeline pronto | ~200k escolas | CNPJ → Escola |
| 52 | INEP ENEM | 🔧 Pipeline pronto | ~5M/ano | Dados educacionais |
| 53 | FNDE Repasses | ⬜ Precisa pipeline | Grande | Município → Repasse educação |

### Grupo 11: Trabalho e Previdência

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 54 | RAIS | 🔧 Pipeline pronto | ~50M vínculos | CNPJ → Empregados |
| 55 | CAGED | 🔧 Pipeline pronto | ~2M/mês | CNPJ → Admissões/Demissões |
| 40 | INSS/DATAPREV | ⬜ Precisa pipeline | Enorme | CPF → Benefício |
| 41 | PREVIC | ⬜ Precisa pipeline | ~300 fundos | Previdência complementar |

### Grupo 12: Meio Ambiente

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 56 | IBAMA Embargos | 🔧 Pipeline pronto | ~10k | CPF/CNPJ → Embargo ambiental |
| 57 | IBAMA Licenciamento | ⬜ Precisa pipeline | Variável | CNPJ → Licença ambiental |
| 58 | IBAMA SINAFLOR | ⬜ Precisa pipeline | Variável | Controle florestal |
| 59 | INPE DETER | ⬜ Precisa pipeline | Geoespacial | Alertas desmatamento |
| 60 | INPE PRODES | ⬜ Precisa pipeline | Geoespacial | Desmatamento anual |
| 61 | CAR/Sicar | ⬜ Precisa pipeline | ~7M imóveis | Imóvel rural → Proprietário |
| 62 | INCRA | ⬜ Precisa pipeline | ~6M imóveis | Cadastro rural |

### Grupo 13: Geologia e Infraestrutura

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 63 | CPRM | ⬜ Precisa pipeline | Geológico | Recursos minerais |
| 64 | INDE | ⬜ Precisa pipeline | Geoespacial | Infraestrutura nacional |
| 65 | DENATRAN/RENAVAM | ⬜ Precisa pipeline | ~110M veículos | CPF/CNPJ → Veículo |
| 66 | ANAC RAB | ⬜ Precisa pipeline | ~25k aeronaves | Registro aeronáutico |
| 67 | ANTT | ⬜ Precisa pipeline | Variável | Transporte terrestre |
| 68 | ANTAQ | ⬜ Precisa pipeline | Variável | Transporte aquaviário |
| 69 | DNIT | ⬜ Precisa pipeline | Variável | Infraestrutura rodoviária |
| 70 | PRF Acidentes | ⬜ Precisa pipeline | ~70k/ano | Geolocalização acidentes |

### Grupo 14: Regulação Setorial

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 71 | ANEEL | ⬜ Precisa pipeline | Variável | CNPJ → Concessão energia |
| 72 | ANP | ⬜ Precisa pipeline | Variável | CNPJ → Petróleo/gás |
| 73 | ANATEL | ⬜ Precisa pipeline | Variável | CNPJ → Telecomunicações |
| 74 | ANVISA | ⬜ Precisa pipeline | ~100k registros | CNPJ → Registro sanitário |
| 75 | ANS | ⬜ Precisa pipeline | ~700 operadoras | CNPJ → Plano de saúde |
| 76 | ANCINE | ⬜ Precisa pipeline | Variável | Produção audiovisual |

### Grupo 15: Estatísticas e Pesquisa

| # | Fonte | Status | Tamanho | Cruzamento |
|---|---|---|---|---|
| 43-50 | IBGE (Censo, PNAD, IPCA, PIB, etc.) | ⬜ Precisa pipeline | Grande | Contextualização socioeconômica |
| 77 | IPEAData | ⬜ Precisa pipeline | ~7k séries | Indicadores macro |
| — | World Bank | 🔧 Pipeline pronto | Variável | Indicadores internacionais |
| — | MIDES (Social) | 🔧 Pipeline pronto | Variável | Programas sociais |

### Grupo EXTRA: Fontes Internacionais

| Fonte | Status | Entidades | Cruzamento |
|---|---|---|---|
| OpenSanctions | ✅ Carregado | 4.136.365 | Sanções globais → BR |
| ICIJ Offshore Leaks | 📥 Baixado | ~800k | Panama/Pandora → BR |
| OFAC (EUA) | 🔧 Pipeline pronto | ~12k | Sanções US → BR |
| UN Sanctions | 🔧 Pipeline pronto | ~1k | Sanções ONU → BR |
| EU Sanctions | 🔧 Pipeline pronto | ~2k | Sanções EU → BR |
| World Bank | 🔧 Pipeline pronto | Variável | Debarment list |

---

## Fases de Implementação

### Fase 1 — Fundação ✅ CONCLUÍDA

**Objetivo:** Carregar as bases de maior valor para cruzamento imediato.

| Tarefa | Status | Responsável |
|---|---|---|
| CEIS/CNEP → Neo4j | ✅ Feito | Automático |
| OpenSanctions → Neo4j | ✅ Feito (4.1M entidades) | Automático |
| ICIJ Offshore → Neo4j | 📥 Baixado, ETL pendente | Automático |
| PEP CGU → Neo4j | ✅ Feito (133k PEPs) | Automático |
| CEAF → Neo4j | ✅ Feito (4.1k servidores) | Automático |
| CEPIM → Neo4j | ✅ Feito (3.5k ONGs) | Automático |
| Leniência → Neo4j | ✅ Feito (146 acordos) | Automático |
| CPGF → Neo4j | ✅ Feito (9.6k transações) | Automático |
| Viagens → Neo4j | ✅ Feito (14.2k viagens) | Automático |
| TSE 2022+2024 → Neo4j | ✅ Feito (candidaturas+doações+bens) | Automático |
| Discord bot com dados reais | ✅ Feito (13 ferramentas, modo agente) | Automático |
| Telegram bot com dados reais | ✅ Feito (@EGOSin_bot, 13 ferramentas) | Automático |
| API pública com dados reais | ✅ Feito | Automático |
| Frontend público (bracc.egos.ia.br) | ✅ Feito (sem login) | Automático |

**Resultado:** 210k+ nós nativos + 4.1M OpenSanctions = maior grafo aberto de entidades BR. 10 bases carregadas, 2 bots 24/7, frontend público.

### Fase 2 — Expansão Política (Semana 3-4)

**Objetivo:** Integrar dados eleitorais e legislativos para mapear rede política.

| Tarefa | Responsável |
|---|---|
| TSE Candidaturas + Doações → Neo4j | Download manual + ETL automático |
| Câmara + Senado (gastos CEAP) → Neo4j | ETL automático |
| CPIs → Neo4j | ETL automático |
| DOU + Querido Diário → Neo4j | ETL automático |
| CPGF (Cartão gov) → Neo4j | ETL automático |
| Viagens do governo → Neo4j | ETL automático |

**Resultado esperado:** Rede completa Político → Doador → Empresa → Contrato → Sanção.

### Fase 3 — Corpo Empresarial (Mês 2)

**Objetivo:** CNPJ completo + compras públicas para mapear toda a economia.

| Tarefa | Responsável |
|---|---|
| CNPJ/QSA Receita Federal (25GB) → Neo4j | Download manual + ETL |
| ComprasNet/PNCP → Neo4j | ETL automático |
| TransfereGov → Neo4j | ETL automático |
| BNDES → Neo4j | ETL automático |
| RAIS + CAGED → Neo4j | ETL automático |
| CVM + Fundos → Neo4j | ETL automático |
| BCB séries → Neo4j | ETL automático |

**Resultado esperado:** 53M+ empresas, cruzamento Empresa → Sócio → Político → Contrato → Sanção.

### Fase 4 — Análise Avançada (Mês 3-4)

**Objetivo:** Algoritmos de inteligência sobre o grafo.

| Capacidade | Descrição |
|---|---|
| **Entity Resolution** | Fuzzy matching para unificar entidades com nomes diferentes (ex: "JOSÉ DA SILVA" vs "JOSE DA SILVA LTDA") |
| **Network Centrality** | PageRank, Betweenness, Closeness para identificar nós mais influentes |
| **Community Detection** | Louvain/Label Propagation para encontrar clusters de corrupção |
| **Anomaly Detection** | Padrões incomuns: empresa criada 30 dias antes de contrato, doação → contrato em <6 meses |
| **Temporal Analysis** | Timeline de relacionamentos: quando se formaram, quando se dissolveram |
| **Geographic Clustering** | Mapas de calor de irregularidades por município/estado |
| **Red Flag Scoring** | Score 0-100 baseado nos 60 indicadores do GRAS (World Bank) |
| **Cross-Dataset Correlation** | Doação TSE → Contrato ComprasNet → Sanção CEIS (o "triângulo da corrupção") |

### Fase 5 — Ecossistema Global (Mês 5+)

**Objetivo:** Interoperabilidade com ferramentas internacionais.

| Integração | Descrição |
|---|---|
| **FollowTheMoney** | Exportar entidades BR/ACC no formato FtM para compatibilidade com Aleph/OpenSanctions |
| **Aleph Connector** | Permitir busca no BR/ACC diretamente do Aleph (OCCRP) |
| **ICIJ DataShare** | Integrar com a plataforma de jornalismo investigativo do ICIJ |
| **Serenata de Amor** | Integrar modelos de ML para detecção de anomalias em CEAP |
| **GRAS Red Flags** | Implementar os 60 indicadores de risco do World Bank |
| **Intelink Intelligence** | Reuso do motor de resolução de entidades, visualização de grafos e análise temporal |

---

## Ferramentas de Referência Mundial

| Ferramenta | Org | Entidades | Open Source | Foco |
|---|---|---|---|---|
| [OpenSanctions](https://opensanctions.org) | OpenSanctions.org | 2.1M | ✅ MIT | Sanções + PEPs globais |
| [Aleph](https://aleph.occrp.org) | OCCRP | 270M | ✅ MIT | Documentos + entidades investigativas |
| [ICIJ DataShare](https://datashare.icij.org) | ICIJ | Leaks globais | ✅ AGPL | Panama/Pandora Papers |
| [FollowTheMoney](https://followthemoney.tech) | OpenSanctions | Modelo de dados | ✅ MIT | Ontologia para dados investigativos |
| [Investigraph](https://investigraph.dev) | Investigativedata | ETL europeu | ✅ MIT | Pipeline FtM para dados europeus |
| [Serenata de Amor](https://github.com/okfn-brasil/serenata-de-amor) | OKFN Brasil | Gastos CEAP | ✅ MIT | ML para gastos parlamentares |
| [Alice](https://www.gov.br/cgu) | CGU Brasil | Licitações | ❌ Interno | 40 categorias de risco em compras |
| [GRAS](https://worldbank.org) | World Bank | Procurement | ❌ Interno | 60 red flags em procurement |
| [Querido Diário](https://queridodiario.ok.org.br) | OKFN Brasil | 5.570 municípios | ✅ MIT | Diários oficiais municipais |
| [DadosJusBr/Extrateto](https://github.com/dadosjusbr) | DadosJusBr | Judiciário | ✅ | Salários do judiciário |
| **BR/ACC** | **EGOS + World-Open-Graph** | **40k+ (crescendo)** | **✅ MIT** | **Grafo completo Brasil** |

---

## Matriz de Cruzamento (O Poder Real)

O verdadeiro valor está no **cruzamento entre bases**. Cada linha abaixo é um tipo de análise que nenhuma ferramenta individual consegue fazer:

| Cruzamento | Fontes | Pergunta que responde |
|---|---|---|
| **Doação → Contrato** | TSE + ComprasNet | "Empresa X doou para Político Y e depois ganhou contrato de R$Z?" |
| **Sanção → Contrato** | CEIS + ComprasNet | "Empresa sancionada continua ganhando licitações?" |
| **PEP → Empresa** | PEP + CNPJ | "Político é sócio de empresa que recebe dinheiro público?" |
| **Offshore → Político** | ICIJ + TSE | "Candidato tem empresa em paraíso fiscal?" |
| **Servidor → Empresa** | CEAF + CNPJ | "Servidor expulso é sócio de empresa com contratos gov?" |
| **Doação → Patrimônio** | TSE Doações + TSE Bens | "Doador tem patrimônio compatível com a doação?" |
| **Empresa → Sanção Global** | OpenSanctions + CNPJ | "Empresa brasileira está em lista de sanções internacionais?" |
| **ONG → Repasses** | CEPIM + TransfereGov | "ONG bloqueada continua recebendo repasses?" |
| **Fundo → Político** | CVM + TSE | "Fundo de investimento é controlado por político?" |
| **Leniência → Novos contratos** | Leniência + ComprasNet | "Empresa com acordo de leniência voltou a contratar com gov?" |
| **Viagem → Empresa** | Viagens Gov + CNPJ | "Servidor viaja para cidade onde tem empresa?" |
| **DOU → Nomeação** | DOU + PEP + CNPJ | "Pessoa nomeada em DOU é sócia de empresa contratada?" |

---

## Como Contribuir

### Para Desenvolvedores

```bash
# Clone o repositório
git clone https://github.com/World-Open-Graph/br-acc.git
cd br-acc

# Setup do ambiente ETL
cd etl
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Rode um pipeline existente
python scripts/download_sanctions.py
python -c "from bracc_etl.pipelines.sanctions import SanctionsPipeline; ..."

# Crie um novo pipeline
cp etl/src/bracc_etl/pipelines/_template.py etl/src/bracc_etl/pipelines/nova_fonte.py
```

### Para Cidadãos (Não-Técnicos)

1. **Baixe dados manualmente** — Muitas fontes do governo precisam de download via navegador (captcha). Você pode ajudar baixando e compartilhando!
2. **Teste o bot no Discord** — Mande uma DM para `@EGOS Intelligence` e teste consultas
3. **Reporte bugs** — Abra issues em [github.com/enioxt/br-acc/issues](https://github.com/enioxt/br-acc/issues)
4. **Sugira cruzamentos** — Que perguntas você quer que o grafo responda?

### Para Jornalistas

1. Use a API pública: `http://217.216.95.126/api/v1/public/`
2. Consulte via Discord bot (DM para privacidade)
3. Os dados são 100% públicos — cite as fontes originais
4. Abra issues para pedir novos tipos de consulta

### Issues Abertas para Contribuição

Cada fonte sem pipeline é uma oportunidade. Procure issues com label `data-source`:

- `good-first-issue` — Fontes com API simples (BCB, IBGE)
- `help-wanted` — Fontes complexas (CNPJ, DATASUS)
- `research-needed` — Fontes que precisam de investigação (Juntas Comerciais, DENATRAN)

---

## Reuso de Inteligência do Intelink

O projeto [Intelink](https://intelink.ia.br) (EGOS) já implementou capacidades avançadas que podem ser reaproveitadas:

| Capacidade Intelink | Aplicação no BR/ACC |
|---|---|
| **Entity Resolution** (fuzzy matching + dedup) | Unificar nomes de empresas/pessoas entre bases |
| **Grafo de Vínculos** (React + vis.js) | Visualização interativa do grafo Neo4j |
| **Jurista** (análise legal com IA) | Interpretar fundamentação legal de sanções |
| **Cronos** (timeline analysis) | Timeline de relações empresa→político→contrato |
| **Confidence Scoring** (Pramana) | Score de confiabilidade dos dados |
| **Document Extraction** | Extrair entidades de documentos PDF (DOU, DOE) |
| **Intelligence Dashboard** | Dashboard unificado de alertas e indicadores |

---

## Princípios

1. **100% Open Source** — Código, dados, prompts, tudo público
2. **Dados Públicos** — Usamos apenas dados disponíveis por lei (LAI, dados abertos)
3. **Linguagem Neutra** — Não acusamos, apresentamos fatos e conexões verificáveis
4. **Reprodutível** — Qualquer pessoa pode rodar os pipelines e verificar os resultados
5. **Descentralizado** — Qualquer um pode fazer fork e adaptar para seu contexto
6. **Interoperável** — Compatível com padrões internacionais (FollowTheMoney)

---

## Fase 6: MCP — Ferramentas para Qualquer IDE (PRÓXIMA)

> **Estratégia:** Os bots Discord/Telegram são ótimos para consultas rápidas, mas limitados para
> análises profundas com memória persistente. A solução: empacotar nossas ferramentas OSINT como
> **MCP Servers** (Model Context Protocol) para que qualquer pessoa com uma IDE (VS Code, Cursor,
> Windsurf, etc.) tenha acesso completo a todas as capacidades — com memória infinita da IDE.

| # | Task | Status | Complexidade | Issue |
|---|---|---|---|---|
| 1 | **egos-mcp**: MCP Server com 13 ferramentas OSINT | ⬜ Precisa fazer | Alta | `help-wanted` |
| 2 | **Busca CNPJ**: Tool para buscar CNPJ a partir de nome de empresa | ⬜ Precisa fazer | Média | `good-first-issue` |
| 3 | **MCP no egos.ia.br**: Suporte a MCP no website | ⬜ Precisa fazer | Alta | `help-wanted` |
| 4 | **Documentação MCP**: Guia de instalação e uso | ⬜ Precisa fazer | Baixa | `good-first-issue` |
| 5 | **Auto-learning**: Tasks criadas automaticamente pelo bot a partir de feedback | ✅ Implementado | — | — |
| 6 | **Bot autônomo**: Modo agente — executa sem pedir permissão | ✅ Implementado | — | — |
| 7 | **Memória estendida**: 40 msgs, 16k chars, 30min janela | ✅ Implementado | — | — |

### Por que MCP?

- **Memória persistente**: IDEs mantêm contexto muito maior que Discord/Telegram
- **Ecossistema existente**: 100k+ devs já usam MCP no VS Code, Cursor, Windsurf
- **Zero infraestrutura**: Usuário instala, configura e usa — sem servidor adicional
- **Composabilidade**: Usuário pode combinar EGOS MCP com outros MCPs (filesystem, database, etc.)
- **Open source**: Qualquer um pode criar novos tools e contribuir

---

## Fase 7: Sistema Completo de Análise (Palantir-level)

> **Meta:** Transformar BR/ACC de "consulta de dados" para "análise investigativa real" com expansão de entidades, cruzamentos multi-hop e detecção de anomalias.

### 7.1 — Algoritmos de Grafo (PRIORIDADE MÁXIMA)

| # | Task | Descrição | Depende de | Status |
|---|------|-----------|------------|--------|
| 7.1.1 | **PageRank** | Identificar entidades mais influentes no grafo (quem tem mais conexões) | CNPJ carregado | ⬜ |
| 7.1.2 | **Community Detection** (Louvain) | Agrupar empresas/pessoas em clusters — detectar "famílias" de empresas | CNPJ carregado | ⬜ |
| 7.1.3 | **Shortest Path** | Mostrar caminho mais curto entre qualquer par de entidades (ex: político ↔ empresa) | CNPJ carregado | ⬜ |
| 7.1.4 | **Betweenness Centrality** | Detectar "pontes" — entidades que conectam grupos que não deveriam estar conectados | CNPJ carregado | ⬜ |
| 7.1.5 | **Degree Distribution** | Encontrar outliers — entidades com número anormal de conexões | CNPJ carregado | ⬜ |

### 7.2 — Expansão de Entidades (Click-to-Expand)

| # | Task | Descrição | Status |
|---|------|-----------|--------|
| 7.2.1 | **1º grau** | Clicar em pessoa/empresa → ver todas as conexões diretas | ⬜ |
| 7.2.2 | **2º grau** | Expandir conexões dos vizinhos → rede de 2 hops | ⬜ |
| 7.2.3 | **3º grau** | Rede completa de 3 hops — máximo útil antes de "tudo se conecta" | ⬜ |
| 7.2.4 | **Filtros por tipo** | Expandir apenas: SOCIO_DE, DOOU_PARA, SANCIONADO, PEP, etc. | ⬜ |
| 7.2.5 | **Timeline de conexões** | Quando cada conexão foi criada/desfeita (data_entrada em QSA) | ⬜ |

### 7.3 — Cross-Case Analysis (Padrões entre Investigações)

| # | Task | Descrição | Status |
|---|------|-----------|--------|
| 7.3.1 | **Entity overlap** | Detectar entidades que aparecem em 2+ investigações diferentes | ⬜ |
| 7.3.2 | **Pattern matching** | Encontrar padrões repetidos: mesma estrutura de SPEs, mesmo advogado, etc. | ⬜ |
| 7.3.3 | **Temporal correlation** | Eventos que acontecem em datas próximas em investigações diferentes | ⬜ |
| 7.3.4 | **Geographic clustering** | Concentração de entidades suspeitas na mesma região | ⬜ |

### 7.4 — Detecção de Anomalias

| # | Task | Descrição | Algoritmo | Status |
|---|------|-----------|-----------|--------|
| 7.4.1 | **Benford's Law** | Distribuição dos primeiros dígitos em valores de contratos/BNDES | Estatístico | ⬜ |
| 7.4.2 | **HHI (Herfindahl)** | Concentração de contratos em poucos fornecedores por órgão | Estatístico | ⬜ |
| 7.4.3 | **Temporal spikes** | Picos anormais de atividade (ex: 147 operações BNDES em 1 ano) | Z-score | ⬜ |
| 7.4.4 | **Shell company detection** | Muitas empresas, poucos funcionários, mesmo endereço | Heurístico | ⬜ |
| 7.4.5 | **Fragmentation detection** | Contratos divididos para ficar abaixo do limite de licitação | Clustering | ⬜ |
| 7.4.6 | **Circular ownership** | Empresa A → sócia de B → sócia de C → sócia de A | Cycle detection | ⬜ |

### 7.5 — Entity Resolution (Unificar Identidades)

| # | Task | Descrição | Status |
|---|------|-----------|--------|
| 7.5.1 | **CPF/CNPJ exact match** | Mesma pessoa/empresa em CNPJ, TSE, CEIS, PEP | ⬜ |
| 7.5.2 | **Fuzzy name matching** | Jaro-Winkler > 0.85 + data nascimento (portar do Intelink) | ⬜ |
| 7.5.3 | **Address matching** | Parse de endereço + comparação fuzzy (portar do Intelink) | ⬜ |
| 7.5.4 | **Merge nodes** | Criar nó unificado com todas as fontes como evidência | ⬜ |
| 7.5.5 | **Conflict detection** | Alertar quando CPF+Nome não batem (erro de dados) | ⬜ |

### 7.6 — Visualização de Grafo (Frontend)

| # | Task | Descrição | Status |
|---|------|-----------|--------|
| 7.6.1 | **Force-directed graph** | Visualização interativa de rede (D3.js ou vis.js) | ⬜ |
| 7.6.2 | **Color by type** | Pessoa=azul, Empresa=verde, Sanção=vermelho, PEP=amarelo | ⬜ |
| 7.6.3 | **Size by importance** | Nós maiores = mais conexões (PageRank) | ⬜ |
| 7.6.4 | **Click-to-expand** | Clicar em nó → carregar vizinhos → expandir grafo | ⬜ |
| 7.6.5 | **Search + highlight** | Buscar entidade → destacar no grafo | ⬜ |
| 7.6.6 | **Export** | Exportar subgrafo como PNG, PDF, ou CSV | ⬜ |

### 7.7 — Relatórios de Investigação (Padronizados)

| # | Task | Descrição | Status |
|---|------|-----------|--------|
| 7.7.1 | **Template de relatório** | Header, resumo, entidades, conexões, red flags, fontes | ⬜ |
| 7.7.2 | **Shareable permalinks** | Cada relatório tem URL única (anônimo) | ⬜ |
| 7.7.3 | **Crowd corrections** | Qualquer pessoa pode sugerir correções (moderado) | ⬜ |
| 7.7.4 | **Confidence scores** | Cada achado tem score de confiança (alto/médio/baixo) | ⬜ |
| 7.7.5 | **Source attribution** | Cada dado cita a fonte oficial exata | ⬜ |

### 7.8 — Bases de Dados Adicionais (Próximas Prioridades)

| # | Base | Volume | Cruzamento | Prioridade |
|---|------|--------|------------|------------|
| 7.8.1 | **DataJud** (processos judiciais) | 80M+ processos | CPF/CNPJ → quem processa quem | Alta |
| 7.8.2 | **ICIJ Offshore** (Panama/Paradise Papers) | 4.8k entidades BR | CNPJ/Nome → offshores | Alta |
| 7.8.3 | **ComprasNet/PNCP** (contratos federais) | 1.1M contratos | CNPJ → quem vende pro governo | Alta |
| 7.8.4 | **CVM** (fundos/valores mobiliários) | 500k+ registros | CNPJ → mercado financeiro | Média |
| 7.8.5 | **RAIS/CAGED** (emprego formal) | 100M+ registros | CNPJ → quantos empregados | Média |
| 7.8.6 | **DataSUS** (saúde pública) | Hospitais, leitos, gastos | CNPJ → saúde | Média |
| 7.8.7 | **IBAMA** (multas ambientais) | Infrações, embargos | CNPJ → ambiental | Média |
| 7.8.8 | **STF/STJ** (supremas cortes) | 2.4M+ processos | Nome/CPF → jurisprudência | Baixa |
| 7.8.9 | **DOU via NLP** (diários oficiais) | 4M+ atos | NER → extrair entidades | Baixa |
| 7.8.10 | **BCB** (dados financeiros) | Taxa de câmbio, PIX stats | Contextual | Baixa |

---

## Fork Divergence Plan: br-acc → Intelink

> **Status:** Divergência em andamento. Rename planejado para quando atingir >80% de código próprio.

### O que já divergiu do upstream (Bruno/World-Open-Graph)

| Área | Upstream | EGOS Fork |
|------|----------|-----------|
| **Bots** | ❌ Nenhum | ✅ Discord + Telegram (14 tools cada, 24/7) |
| **IA** | ❌ Nenhuma | ✅ Model fallback (free→paid), memória persistente (Supabase) |
| **Investigações** | ❌ Nenhuma | ✅ 11 relatórios reais (incl. Patense R$217M BNDES) |
| **API BNDES** | ❌ | ✅ Consulta automática de financiamentos (2002-presente) |
| **CNPJ** | Demo data | 🔄 53.6M empresas em carregamento (ETL pronto) |
| **Custos** | Não publicado | ✅ $36/mo transparente, 100% autofinanciado |
| **Comunidade** | Discord básico | ✅ Discord, Telegram, GitHub Issues automáticos |
| **Dados** | ~40k nós (demo) | 278k nós reais + 4.1M OpenSanctions |
| **Docs** | README básico | ROADMAP + SHOWCASE + INVESTIGATIONS + DIAGNOSTIC + COMPARISON |
| **CI/CD** | ❌ | ✅ Gitleaks + Bandit + Privacy Gate |

### Plano de Rename

1. **Agora:** Manter `enioxt/br-acc` no GitHub (rastrear upstream)
2. **Agora:** Branding público como "Intelink" no README e website
3. **Mês 2:** Quando frontend divergir >80%, criar repo `enioxt/intelink`
4. **Mês 2:** Redirect `bracc.egos.ia.br` → `intelink.egos.ia.br`
5. **Contínuo:** Monitorar forks do upstream para cherry-pick de melhorias

### O que monitorar no upstream

- BigQuery CNPJ pipeline (se alguém implementar)
- Novos padrões de detecção de corrupção
- Melhorias no Entity Resolution
- Novos pipelines ETL para fontes que não temos

### Por que "Intelink"?

- **Intel** (intelligence) + **Link** (conexões no grafo)
- Já é o nome do app principal no egos-lab
- Forte identidade visual (police intelligence style)
- Diferenciação clara do upstream

---

## Modelos de IA para Investigacao (Atualizado Marco 2026)

> Fonte: [LM Arena](https://lmarena.ai), [Awesome Agents](https://awesomeagents.ai), [WhatLLM](https://whatllm.org)

### Ranking Global Marco 2026

| # | Modelo | Provider | Input/Output per 1M | Melhor para |
|---|--------|----------|---------------------|-------------|
| 1 | **GPT-5.2 Pro** | OpenAI | $10 / $30 | Raciocinio complexo, #1 overall |
| 2 | **Claude Opus 4.6** | Anthropic | $15 / $75 | Coding (#1 SWE-Bench 72.5%), investigacoes longas |
| 3 | **Gemini 3.1 Pro** | Google | $1.25 / $5 | Melhor custo-beneficio, multimodal, tool calling |
| 4 | **Grok 4 Heavy** | xAI | $3 / $15 | Raciocinio, noticias em tempo real |
| 5 | **DeepSeek V3.2** | DeepSeek | $0.14 / $0.28 | Budget king, open source |
| 6 | **GLM-4.7 Thinking** | Zhipu | Open source | Melhor open-source para raciocinio |
| 7 | **Kimi K2.5** | Moonshot | Open source | Open source, contexto longo |

### Como Usamos

| Funcao | Modelo Atual | Modelo Ideal | Por que |
|--------|-------------|-------------|---------|
| **Bot Discord/Telegram** | Gemini 2.0 Flash | **Gemini 3.1 Pro** | 10x melhor raciocinio, mesmo preco |
| **Relatorios de investigacao** | Claude Sonnet (via Cascade) | **Claude Opus 4.6** | Chain-of-thought superior |
| **Tool calling (bot)** | Gemini 2.0 Flash | **Gemini 3.1 Pro** | Melhor function calling |
| **Analise de documentos longos** | N/A | **Gemini 3.1 Pro** (1M ctx) | Contexto massivo |
| **Budget / self-hosted** | N/A | **DeepSeek V3.2** | R$0.70/1M tokens |

### Acao Imediata

- [ ] Migrar bot de `google/gemini-2.0-flash-001` para `google/gemini-3.1-pro` via OpenRouter
- [ ] Testar `deepseek/deepseek-v3.2` como fallback barato
- [ ] Para relatorios premium: usar `anthropic/claude-opus-4.6` ou `openai/gpt-5.2`

---

## Estratégia de Performance: O que as Big Techs fazem

| Empresa | Técnica | Nosso Equivalente | Issue |
|---|---|---|---|
| **LinkedIn** | RAM-first + index every queried property | pagecache=22G + 12 indexes | TASK-002 |
| **Palantir Gotham** | Bounded traversals (max 3 hops) + anomaly scores pré-computados | GDS PageRank + bounded queries | [#22](https://github.com/enioxt/br-acc/issues/22) |
| **Facebook TAO** | Cache-aside pattern — Redis na frente do banco | Redis 512MB + cache-aside nas API routes | [#19](https://github.com/enioxt/br-acc/issues/19) |
| **Google Knowledge Graph** | Lucene fulltext + entity linking | Neo4j fulltext indexes + entity resolution (Phase 7.5) | [#17](https://github.com/enioxt/br-acc/issues/17) |

### Infraestrutura Atual

```
Contabo VPS: 12 vCPU, 48GB RAM, 500GB SSD ($35/mo)
├── Neo4j 5 Community (heap 16G, pagecache 22G) — APÓS ETL
├── Redis 7 Alpine (512MB LRU cache) — PRONTO
├── FastAPI (Python) — API backend
├── React + Vite — Frontend (bracc.egos.ia.br)
└── Caddy — Reverse proxy + TLS
```

### GitHub Issues Abertas (23 total)

| Categoria | Issues |
|---|---|
| **Performance** | #19 Redis, #20 GDS, #22 Bounded traversals |
| **Pipelines ETL** | #5 Extrateto, #12 IBGE, #13 DENATRAN, #14 Reguladoras, #15 Meio Ambiente, #16 SIAFI |
| **Algoritmos** | #6 Benford, #7 HHI, #17 Entity Resolution |
| **Frontend** | #21 Website Redesign (help wanted) |
| **Infra** | #8 Bots, #9 Fork Monitor, #11 PR Coordination |
| **i18n/Docs** | #1 Frontend PT-BR, #2 API PT-BR, #3 Tradução, #4 FAQ |
| **Agentes** | #23 Gem Hunter |
| **Global** | #18 Interoperabilidade (FtM, Aleph, ICIJ) |

---

## Links

- **Código:** [github.com/enioxt/br-acc](https://github.com/enioxt/br-acc) (fork ativo, futuro "Intelink")
- **Upstream:** World-Open-Graph/br-acc (monitorando)
- **API ao vivo:** http://217.216.95.126/api/v1/public/
- **Frontend:** [bracc.egos.ia.br](https://bracc.egos.ia.br) (público, sem login)
- **Bot Discord:** EGOS Intelligence#2881 (DMs abertas, 13 tools)
- **Bot Telegram:** [@EGOSin_bot](https://t.me/EGOSin_bot) (13 tools)
- **Ecossistema EGOS:** [egos.ia.br](https://egos.ia.br)
- **Comunidade Telegram:** [@ethikin](https://t.me/ethikin)

---

*"Transparência não é sobre acusar. É sobre dar a cada cidadão o poder de entender como seu dinheiro é usado."*
