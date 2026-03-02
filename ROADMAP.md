# BR/ACC — Roadmap de Integração de Dados

> **Visão:** Construir o maior grafo aberto de relações entre entidades públicas e privadas do Brasil,
> cruzando 79+ bases de dados públicas para detectar padrões de corrupção, conflitos de interesse e
> desvios — tudo open source, verificável e acessível a qualquer cidadão.

> **Inspiração:** OpenSanctions (2.1M entidades, 297 fontes), Aleph/OCCRP (270M entidades),
> ICIJ DataShare, GRAS (World Bank), Alice (CGU), Serenata de Amor.

---

## Status Atual

| Métrica | Valor |
|---|---|
| **Nós no grafo** | 210.596+ (crescendo — de 40k em fev/2026) |
| **Relacionamentos** | 23.870+ |
| **Empresas** | 9.645+ |
| **Sanções carregadas** | 23.847 (CEIS + CNEP) |
| **OpenSanctions** | 4.136.365 entidades (ETL rodando) |
| **PEP** | 133.859 Pessoas Expostas Politicamente |
| **TSE** | Candidaturas + Doações + Bens (2022+2024, 1.7GB) |
| **ICIJ Offshore Leaks** | 73MB baixado (Panama/Pandora Papers) |
| **DataJud CNJ** | Script pronto para 80M+ processos judiciais |
| **Pipelines ETL prontos** | 46 |
| **Scripts de download** | 39 + download-datajud.sh |
| **Servidor** | VPS Contabo 48GB RAM, Neo4j + bots 24/7 |
| **Bot Discord** | 13 ferramentas OSINT, modo agente autônomo |
| **Bot Telegram** | 13 ferramentas OSINT (@EGOSin_bot) |
| **Frontend** | bracc.egos.ia.br — público, sem login |
| **Download guide** | docs/pt-BR/DOWNLOAD_DADOS.md (33 datasets) |

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

## Fork Divergence Plan: br-acc → Intelink

> **Status:** Divergência em andamento. Rename planejado para quando atingir >80% de código próprio.

### O que já divergiu do upstream (Bruno/World-Open-Graph)

| Área | Upstream | EGOS Fork |
|------|----------|-----------|
| **Bots** | ❌ Nenhum | ✅ Discord + Telegram (13 tools cada) |
| **IA** | ❌ Nenhuma | ✅ Chat com RAG, Entity Resolution, Tool Calling |
| **Investigações** | ❌ Nenhuma | ✅ 11 relatórios reais com dados do Neo4j |
| **API BNDES** | ❌ | ✅ Consulta automática de operações (ex: Patense) |
| **Token** | ❌ | ✅ ETHIK token com price ticker |
| **Comunidade** | ❌ Abandonado | ✅ Discord, Telegram, GitHub Issues automáticos |
| **Dados** | ~40k nós | 278k nós + 4.1M OpenSanctions |
| **Docs** | README básico | ROADMAP + SHOWCASE + INVESTIGATIONS + DIAGNOSTIC |
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

## Sobre Modelos de IA para Investigação

> **Conclusão dos testes com Patense (2026-03-02):** Relatórios de investigação exigem modelos com raciocínio em cadeia (Chain of Thought). Modelos baratos funcionam para consultas individuais, mas a síntese (BNDES → pulverização → SPEs → perguntas investigativas) requer capacidade avançada.

| Modelo | Adequação | Custo/1M tokens | Melhor para |
|--------|-----------|-----------------|-------------|
| Claude 3.5 Sonnet | ⭐⭐⭐⭐⭐ | ~$3.00 | Relatórios de investigação |
| GPT-4o | ⭐⭐⭐⭐ | ~$2.50 | Análise de documentos |
| Gemini 2.0 Flash | ⭐⭐⭐ | ~$0.10 | Bots, tool calling, busca |
| Gemini 1.5 Pro | ⭐⭐⭐⭐ | ~$1.25 | Documentos longos (1M ctx) |
| Llama 3.1 70B | ⭐⭐⭐ | ~$0.20 | Consultas simples |

**Custo de um relatório completo (como o Patense):** ~$0.16 (Exa + APIs públicas + Claude)

**Plano de financiamento:** Créditos da comunidade para gerar relatórios avançados com modelos premium. Ver [CREDIT_SYSTEM_PLAN.md](../docs/plans/CREDIT_SYSTEM_PLAN.md).

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
