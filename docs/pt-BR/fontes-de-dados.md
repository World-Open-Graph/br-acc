# Catálogo de Fontes de Dados — EGOS Inteligência

**38 carregadas | 3 pipelines aguardando dados | 60+ ainda não construídas**
Última atualização: 2026-03-03

---

## 1. CARREGADAS (38 fontes)

Todas as fontes abaixo possuem pipelines ETL funcionais em `etl/src/bracc_etl/pipelines/` e estão carregadas no Neo4j de produção.

| # | Fonte | Pipeline | Nós Criados | Relações Criadas | Notas |
|---|-------|----------|-------------|------------------|-------|
| 1 | CNPJ (Receita Federal) | `cnpj` | 53,6M Company, 1,98M Person | 24,6M SOCIO_DE | ~85GB descomprimido |
| 2 | TSE (Eleições + Doações) | `tse` | 7,1M Person, 101K Election | 8,2M DOOU, 2,93M CANDIDATO_EM | Histórico 2002-2024 |
| 3 | Transparência (Contratos) | `transparencia` | 38K Contract, 27,6K Amendment | 32K VENCEU, 29K AUTOR_EMENDA | Contratos federais |
| 4 | CEIS/CNEP (Sanções) | `sanctions` | 23,8K Sanction | 23,8K SANCIONADA | Empresas/pessoas impedidas |
| 5 | BNDES (Empréstimos) | `bndes` | 9,2K Finance | 8,7K RECEBEU_EMPRESTIMO | |
| 6 | PGFN (Dívida Ativa) | `pgfn` | 24M Finance | 24M DEVE | Dívida ativa da União |
| 7 | ComprasNet (Compras) | `comprasnet` | 1,08M Contract | 1,07M VENCEU | Licitações federais |
| 8 | TCU (Sanções de Auditoria) | `tcu` | 45K Sanction | 45K SANCIONADA | Inabilitados/inidôneos |
| 9 | TransfereGov | `transferegov` | 71K Amendment, 67K Convenio | 320K BENEFICIOU, 70K GEROU_CONVENIO | Transferências federais |
| 10 | RAIS (Estatísticas Trabalhistas) | `rais` | 29,5K LaborStats | -- | Agregado por CNAE+UF (sem CPF) |
| 11 | INEP (Educação) | `inep` | 224K Education | 18K MANTEDORA_DE | Censo educacional |
| 12 | DATASUS/CNES | `datasus` | 602K Health | 435K OPERA_UNIDADE | Cadastro de unidades de saúde |
| 13 | IBAMA (Embargos) | `ibama` | 79K Embargo | 79K EMBARGADA | Fiscalização ambiental |
| 14 | DOU (Diário Oficial) | `dou` | 3,98M DOUAct | 169K MENCIONOU, 13K PUBLICOU | Parquet via BigQuery |
| 15 | Câmara (Despesas) | `camara` | 4,6M Expense | 4,6M GASTOU, 4,9M FORNECEU | Despesas CEAP de deputados |
| 16 | Senado (Despesas) | `senado` | 272K Expense | 272K FORNECEU | Despesas CEAPS de senadores |
| 17 | ICIJ (Offshore Leaks) | `icij` | 4,8K OffshoreEntity, 6,6K OffshoreOfficer | 2,3K OFFICER_OF | Panama/Paradise/Pandora Papers |
| 18 | OpenSanctions (PEPs Globais) | `opensanctions` | 118K GlobalPEP | 7,6K GLOBAL_PEP_MATCH | Cruzamento por nome com entidades BR |
| 19 | CVM (Processos) | `cvm` | 522 CVMProceeding | 1,1K CVM_SANCIONADA | Sanções de valores mobiliários |
| 20 | CVM Fundos | `cvm_funds` | 41K Fund | -- | Cadastro de fundos de investimento |
| 21 | Servidores Públicos | *(transparencia)* | 635K PublicOffice | 636K RECEBEU_SALARIO | Servidores federais + salários |
| 22 | CEAF (Servidores Expulsos) | `ceaf` | 4,1K Expulsion | 4,1K EXPULSO | Demitidos por conduta irregular |
| 23 | CEPIM (ONGs Impedidas) | `cepim` | 3,6K BarredNGO | 3,6K IMPEDIDA | ONGs impedidas de convênios |
| 24 | CPGF (Cartão Corporativo) | `cpgf` | 1,46M GovCardExpense | -- | LGPD mascara CPFs |
| 25 | Viagens a Serviço | `viagens` | 3,71M GovTravel | -- | LGPD mascara CPFs |
| 26 | Renúncias Fiscais | `renuncias` | 291,8K TaxWaiver | 291,8K RECEBEU_RENUNCIA | R$414B+ em renúncias fiscais |
| 27 | Acordos de Leniência | `leniency` | 112 LeniencyAgreement | -- | Empresas que confessaram |
| 28 | BCB Penalidades | `bcb` | 3,5K BCBPenalty | -- | Multas a instituições financeiras |
| 29 | STF (Supremo Tribunal) | `stf` | 2,38M LegalCase | -- | Processos do STF |
| 30 | PEP CGU | `pep_cgu` | 133,8K PEPRecord | -- | Pessoas politicamente expostas |
| 31 | TSE Bens (Patrimônio) | `tse_bens` | 14,3M DeclaredAsset | 14,3M DECLAROU_BEM | Patrimônio declarado |
| 32 | TSE Filiados | `tse_filiados` | 16,5M PartyMembership | -- | Histórico de filiação partidária |
| 33 | OFAC SDN | `ofac` | 39,2K InternationalSanction* | -- | Sanções do Tesouro dos EUA |
| 34 | Sanções UE | `eu_sanctions` | *(incluído acima)* | -- | Sanções consolidadas da UE |
| 35 | Sanções ONU | `un_sanctions` | *(incluído acima)* | -- | Conselho de Segurança da ONU |
| 36 | Banco Mundial | `world_bank` | *(incluído acima)* | -- | Empresas impedidas |
| 37 | Holdings (derivado CNPJ) | `holdings` | -- | 59K HOLDING_DE | Derivado dos sócios do CNPJ |
| 38 | SIOP (Emendas Orçamentárias) | `siop` | 71,1K Amendment | -- | Execução de emendas parlamentares |
| 39 | Senado CPIs | `senado_cpis` | 3 CPI | -- | Investigações parlamentares |

*\* InternationalSanction: 39,2K no total entre OFAC + UE + ONU + Banco Mundial*

**Totais de produção (2026-02-26):** ~141M nós, ~92M relações em 35 tipos de nós e 33 tipos de relações.

---

## 2. PIPELINE EXISTE — DADOS PENDENTES (3 fontes)

| Fonte | Pipeline | Status | Bloqueio |
|-------|----------|--------|----------|
| PNCP (Publicações de Licitações) | `pncp` | Baixando — 35 arquivos (2021-08→2024-06) | Tempo — API pagina por mês |
| SICONFI (Finanças Municipais) | `siconfi` | Baixando dados de 2024 (~530K/700K linhas) | Tempo — 5.570 municípios × 5 anos |
| CAGED (Movimentações Trabalhistas) | `caged` | Pipeline reescrito como LaborStats agregado | Dados públicos sem CNPJ do empregador |

---

## 3. AINDA NÃO CONSTRUÍDAS (60+ fontes)

### 3.1 CGU / Portal da Transparência

| # | Fonte | Formato | Vol. Estimado | Valor | Notas |
|---|-------|---------|---------------|-------|-------|
| 1 | Bolsa Família/BPC | CSV | ~20M | BAIXO | CPFs mascarados pela LGPD |

### 3.2 BCB / Banco Central

| # | Fonte | Formato | Vol. Estimado | Valor | Notas |
|---|-------|---------|---------------|-------|-------|
| 2 | BCB Multas | CSV | ~5K | ALTO | Multas administrativas |
| 3 | ESTBAN | CSV | ~500K/mês | BAIXO | Balanços de agências bancárias |
| 4 | IF.data | CSV | ~2K trimestral | BAIXO | Métricas de instituições financeiras |
| 5 | BCB Liquidação | CSV | ~200 | MÉDIO | Instituições financeiras liquidadas |

### 3.3 Judiciário

| # | Fonte | Formato | Vol. Estimado | Valor | Notas |
|---|-------|---------|---------------|-------|-------|
| 6 | CNJ DataJud | API REST | Dezenas de milhões | MUITO ALTO | Processos de todos os tribunais |
| 7 | STJ Dados Abertos | CSV/XML | ~500K | ALTO | Decisões do tribunal superior |
| 8 | CNCIAI (Improbidade) | API | ~10K | MUITO ALTO | Condenações por improbidade |
| 9 | CARF (Recursos Fiscais) | Estruturado | ~500K | MÉDIO | Recursos fiscais federais |

### 3.4 Agências Reguladoras (11 fontes)

| # | Fonte | Formato | Vol. Estimado | Valor | Notas |
|---|-------|---------|---------------|-------|-------|
| 19 | ANP (Royalties Petróleo) | API + CSV | ~100K/ano | MÉDIO | Royalties + preços de combustíveis |
| 20 | ANEEL (Energia) | API | ~50K | MÉDIO | Concessões de energia |
| 21 | ANM (Mineração) | API + CSV | ~100K | ALTO | Ligado ao desmatamento |
| 22 | ANTT (Rodovias) | API | ~10K | BAIXO | Concessões de transporte |
| 23 | ANS (Planos de Saúde) | API | ~50K | BAIXO | Operadoras de saúde |
| 24 | ANVISA (Medicamentos) | API | ~100K | BAIXO | Registros de produtos |
| 25 | ANAC (Aviação) | API | ~10K | BAIXO | Concessões aeroportuárias |
| 26 | ANTAQ (Hidrovias) | API | ~5K | BAIXO | Autoridade portuária |
| 27 | ANA (Águas) | API | ~10K | BAIXO | Outorgas de recursos hídricos |
| 28 | ANATEL (Telecom) | API | ~50K | BAIXO | Licenças de telecomunicações |
| 29 | SUSEP (Seguros) | CSV | ~10K | BAIXO | Mercado de seguros |

### 3.5 Financeiro / Valores Mobiliários

| # | Fonte | Formato | Vol. Estimado | Valor | Notas |
|---|-------|---------|---------------|-------|-------|
| 30 | CVM Completa (Participações) | CSV | Milhões | ALTO | Cadeias de acionistas |
| 31 | Receita DIRBI | CSV | Grande | MÉDIO | Benefícios fiscais |

### 3.6 Ambiental (3 fontes)

| # | Fonte | Formato | Vol. Estimado | Valor | Notas |
|---|-------|---------|---------------|-------|-------|
| 32 | MapBiomas Alerta | API REST | 465K+ alertas | ALTO | Desmatamento validado |
| 33 | SiCAR (Cadastro Rural) | Shapefiles | ~7M propriedades | ALTO | Limites de imóveis rurais |
| 34 | ICMBio/CNUC | API | ~2,5K | BAIXO | Áreas de conservação |

### 3.7 Trabalho

| # | Fonte | Formato | Vol. Estimado | Valor | Notas |
|---|-------|---------|---------------|-------|-------|
| 35 | CAGED (Microdata) | BigQuery | ~2M/mês | MÉDIO | Sem CPF nos dados públicos |
| 36 | RAIS Microdata | BigQuery | ~50M/ano | MÉDIO | Requer autorização formal |

### 3.8 Orçamento / Fiscal

| # | Fonte | Formato | Vol. Estimado | Valor | Notas |
|---|-------|---------|---------------|-------|-------|
| 37 | SIOP Emendas | CSV + API | ~30K/ano | ALTO | Execução detalhada de emendas |
| 38 | SICONFI | API REST | ~5,5K municípios | MÉDIO | Finanças municipais/estaduais |
| 39 | Tesouro Emendas | CSV | ~50K | ALTO | Gastos de emendas pelo Tesouro |
| 40 | SIGA Brasil | CSV export | Massivo | MÉDIO | Execução orçamentária federal |

### 3.9 Legislativo

| # | Fonte | Formato | Vol. Estimado | Valor | Notas |
|---|-------|---------|---------------|-------|-------|
| 41 | Câmara Full API (Votações) | API REST | Milhões | MÉDIO | Votos e projetos de lei |
| 42 | Senado Full API (Votações/CPIs) | API REST | Grande | MÉDIO | Votações e CPIs |
| 43 | TSE Filiados | BigQuery | ~15M | MÉDIO | Histórico de filiação |
| 44 | TSE Bens (Patrimônio) | BigQuery | ~500K | ALTO | Patrimônio por eleição |

### 3.10 Sanções Internacionais

| # | Fonte | Formato | Vol. Estimado | Valor | Notas |
|---|-------|---------|---------------|-------|-------|
| 45 | OFAC SDN | CSV direto | ~12K | ALTO | Sanções do Tesouro dos EUA |
| 46 | Sanções UE | CSV direto | ~5K | ALTO | Sanções consolidadas da UE |
| 47 | Sanções ONU | XML direto | ~2K | ALTO | Conselho de Segurança |
| 48 | Banco Mundial | CSV | ~1K | MÉDIO | Empresas impedidas |
| 49 | INTERPOL (Alertas Vermelhos) | API REST | ~7K | MÉDIO | Requer chave API |

### 3.11 Estadual / Municipal (10+ fontes)

| # | Fonte | Formato | Vol. Estimado | Valor | Notas |
|---|-------|---------|---------------|-------|-------|
| 50 | PNCP Completo | API REST | Massivo | ALTO | Portal Nacional de Compras |
| 51 | TCE-SP | API REST | Grande | ALTO | Auditoria de São Paulo |
| 52 | TCE-PE | API REST | Grande | MÉDIO | Auditoria de Pernambuco |
| 53 | TCE-RJ | API REST | Grande | MÉDIO | Auditoria do Rio de Janeiro |
| 54 | TCE-RS | Bulk downloads | Grande | MÉDIO | Auditoria do Rio Grande do Sul |
| 55 | MiDES | BigQuery | Massivo | MUITO ALTO | 72% dos municípios cobertos |
| 56 | Querido Diário | API REST + ZIP | 104K+ edições | ALTO | Diários oficiais municipais |
| 57-66 | Portais Estaduais | Variados | Variados | MÉDIO | Cada estado tem portal próprio |

---

## 4. ATALHOS DO GITHUB (dados pré-processados)

Datasets e ferramentas mantidos pela comunidade que aceleram a ingestão.

| # | Repo / Fonte | O Que | Volume | Valor | Status |
|---|--------------|-------|--------|-------|--------|
| G1 | brasil-io-public (holding.csv.gz) | Cadeias de propriedade empresa→empresa | 787K relações, 9MB | ALTO | Pronto para carregar |
| G2 | SINARC | Grafo anti-corrupção pré-construído | 90GB | REFERÊNCIA | Formato incerto |
| G3 | cnpj-chat/cnpj-data-pipeline | CNPJ por estado em Parquet | Grande | MÉDIO | Formato alternativo |
| G4 | rictom/rede-cnpj | Relacionamentos CNPJ em SQLite | Grande | MÉDIO | Inclui cruzamentos TSE/Transparência |
| G5 | hackfestcc/dados-hackfestcc | Datasets anti-corrupção curados | Pequeno | BAIXO | Referência |
| G6 | DanielFillol/DataJUD_API_CALLER | Downloader bulk DataJud em Go | -- | ALTO | Acelera ingestão CNJ |
| G7 | Serenata de Amor (suspicions.xz) | Anomalias CEAP pré-analisadas | 8K registros | MÉDIO | Despesas de deputados |
| G8 | mcp-senado | Servidor MCP para API do Senado (56 tools) | -- | BAIXO | Ferramenta para devs |
| G9 | mcp-portal-transparencia | Servidor MCP para Portal da Transparência | -- | BAIXO | Ferramenta para devs |

---

## 5. DATASETS BIGQUERY (via Base dos Dados)

[basedosdados.org](https://basedosdados.org) fornece dados públicos brasileiros limpos e padronizados no BigQuery. Tier gratuito tem limites.

| Dataset BQ | Tabelas-Chave | Carregado? | Notas |
|------------|---------------|------------|-------|
| br_rf_cnpj | empresas, socios, estabelecimentos | SIM (CSV direto) | Usamos download direto da Receita |
| br_tse_eleicoes | candidatos, receitas, despesas, bens, filiação | PARCIAL | Candidatos + doações via TSE direto |
| br_me_rais | microdados_vinculos | PARCIAL | Agregado carregado; microdata requer auth |
| br_me_caged | microdados_movimentacao | NÃO | Dados mensais de trabalho |
| br_stf_corte_aberta | decisoes | NÃO | Decisões do STF |
| br_camara_dados_abertos | votacao, proposicao, deputado | PARCIAL | Despesas carregadas; votos não |
| br_senado_cpipedia | cpi | NÃO | Dados de CPIs |
| br_bd_diretorios_brasil | municipio, uf, setor_censitario | NÃO | Tabelas de referência |
| br_mides | licitacao, contrato, item | NÃO | Compras municipais (72% cobertura) |

---

## 6. MATRIZ DE PRIORIDADE DE INGESTÃO

Ordem recomendada baseada em: valor para detecção de padrões, esforço de implementação e volume.

| Prioridade | Fonte | Esforço | Volume | Valor | Justificativa |
|------------|-------|---------|--------|-------|---------------|
| 1 | CGU PEP List | Trivial (CSV) | ~100K | ALTO | Substitui PEP_ROLES hardcoded |
| 2 | CEAF (Servidores Expulsos) | Fácil (CSV) | ~10K | ALTO | Expulsos por má conduta |
| 3 | Acordos de Leniência | Trivial (CSV) | ~34 | MUITO ALTO | Empresas que confessaram — dataset minúsculo, valor imenso |
| 4 | OFAC SDN | Fácil (CSV) | ~12K | ALTO | Sanções internacionais |
| 5 | Brasil.IO Holdings | Trivial (9MB) | 787K relações | ALTO | Cadeias de propriedade empresa→empresa |
| 6 | DOU via IN XML | Médio (XML) | Grande | ALTO | Contorna Cloudflare; nomeações oficiais |
| 7 | TSE Bens (Patrimônio) | Fácil (BigQuery) | ~500K | ALTO | Detectar enriquecimento inexplicável |
| 8 | TSE Filiados | Fácil (BigQuery) | ~15M | MÉDIO | Mapeamento de redes políticas |
| 9 | CVM Full (Participações) | Médio (CSV) | Milhões | ALTO | Cadeias de acionistas ocultos |
| 10 | CNJ DataJud | Médio (API + chave) | Massivo | MUITO ALTO | Processos judiciais — maior lacuna no grafo |

### Escala de Esforço
- **Trivial**: Download CSV direto, schema compatível, <1 dia
- **Fácil**: CSV/BigQuery, transformações menores, 1-2 dias
- **Médio**: Paginação de API, conversão de formato, ou autenticação, 3-5 dias
- **Difícil**: Scraping, bypass Cloudflare, parsing complexo, ou pedido formal de dados, 1-2 semanas
