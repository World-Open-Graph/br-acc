# ICARUS Data Source Catalog

**38 loaded | 3 pipelines pending data | 60+ not yet built**
Last updated: 2026-02-26

---

## 1. LOADED (38 sources)

All sources below have working ETL pipelines in `etl/src/icarus_etl/pipelines/` and are loaded into production Neo4j.

| # | Source | Pipeline | Nodes Created | Rels Created | Notes |
|---|--------|----------|---------------|--------------|-------|
| 1 | CNPJ (Receita Federal) | `cnpj` | 53.6M Company, 1.98M Person | 24.6M SOCIO_DE | ~85GB uncompressed |
| 2 | TSE (Elections + Donations) | `tse` | 7.1M Person, 101K Election | 8.2M DOOU, 2.93M CANDIDATO_EM | 2002-2024 historical |
| 3 | Transparencia (Contracts) | `transparencia` | 38K Contract, 27.6K Amendment | 32K VENCEU, 29K AUTOR_EMENDA | Federal contracts |
| 4 | CEIS/CNEP (Sanctions) | `sanctions` | 23.8K Sanction | 23.8K SANCIONADA | Banned companies/persons |
| 5 | BNDES (Dev. Bank Loans) | `bndes` | 9.2K Finance | 8.7K RECEBEU_EMPRESTIMO | |
| 6 | PGFN (Tax Debt) | `pgfn` | 24M Finance | 24M DEVE | Divida ativa da Uniao |
| 7 | ComprasNet (Contracts) | `comprasnet` | 1.08M Contract | 1.07M VENCEU | Federal procurement |
| 8 | TCU (Audit Sanctions) | `tcu` | 45K Sanction | 45K SANCIONADA | Inabilitados/inidoneos |
| 9 | TransfereGov | `transferegov` | 71K Amendment, 67K Convenio | 320K BENEFICIOU, 70K GEROU_CONVENIO | Federal transfers |
| 10 | RAIS (Labor Stats) | `rais` | 29.5K LaborStats | -- | Aggregate by CNAE+UF (no CPF) |
| 11 | INEP (Education) | `inep` | 224K Education | 18K MANTEDORA_DE | Education census |
| 12 | DATASUS/CNES | `datasus` | 602K Health | 435K OPERA_UNIDADE | Health facility registry |
| 13 | IBAMA (Embargoes) | `ibama` | 79K Embargo | 79K EMBARGADA | Environmental enforcement |
| 14 | DOU (Official Gazette) | `dou` | 3.98M DOUAct | 169K MENCIONOU, 13K PUBLICOU | Parquet via BigQuery |
| 15 | Camara (Expenses) | `camara` | 4.6M Expense | 4.6M GASTOU, 4.9M FORNECEU | Deputy CEAP expenses |
| 16 | Senado (Expenses) | `senado` | 272K Expense | 272K FORNECEU | Senator CEAPS expenses |
| 17 | ICIJ (Offshore Leaks) | `icij` | 4.8K OffshoreEntity, 6.6K OffshoreOfficer | 2.3K OFFICER_OF | Panama/Paradise/Pandora papers |
| 18 | OpenSanctions (Global PEPs) | `opensanctions` | 118K GlobalPEP | 7.6K GLOBAL_PEP_MATCH | Name-matched to Brazilian entities |
| 19 | CVM (Proceedings) | `cvm` | 522 CVMProceeding | 1.1K CVM_SANCIONADA | Securities sanctions |
| 20 | CVM Funds | `cvm_funds` | 41K Fund | -- | Investment fund registry |
| 21 | Servidores (Public Servants) | *(transparencia)* | 635K PublicOffice | 636K RECEBEU_SALARIO | Federal servants + salaries |
| 22 | CEAF (Expelled Servants) | `ceaf` | 4.1K Expulsion | 4.1K EXPULSO | Fired for misconduct |
| 23 | CEPIM (Barred NGOs) | `cepim` | 3.6K BarredNGO | 3.6K IMPEDIDA | NGOs barred from agreements |
| 24 | CPGF (Govt Credit Cards) | `cpgf` | 1.46M GovCardExpense | -- | LGPD masks CPFs |
| 25 | Viagens a Servico | `viagens` | 3.71M GovTravel | -- | LGPD masks CPFs |
| 26 | Renuncias Fiscais | `renuncias` | 291.8K TaxWaiver | 291.8K RECEBEU_RENUNCIA | R$414B+ in tax waivers |
| 27 | Acordos de Leniencia | `leniency` | 112 LeniencyAgreement | -- | Companies that confessed |
| 28 | BCB Penalidades | `bcb` | 3.5K BCBPenalty | -- | Fines on financial institutions |
| 29 | STF (Supreme Court) | `stf` | 2.38M LegalCase | -- | Supreme court proceedings |
| 30 | PEP CGU | `pep_cgu` | 133.8K PEPRecord | -- | Politically exposed persons |
| 31 | TSE Bens (Candidate Assets) | `tse_bens` | 14.3M DeclaredAsset | 14.3M DECLAROU_BEM | Declared patrimony |
| 32 | TSE Filiados | `tse_filiados` | 16.5M PartyMembership | -- | Party membership history |
| 33 | OFAC SDN | `ofac` | 39.2K InternationalSanction* | -- | US Treasury sanctions |
| 34 | EU Sanctions | `eu_sanctions` | *(merged above)* | -- | EU consolidated sanctions |
| 35 | UN Sanctions | `un_sanctions` | *(merged above)* | -- | UN Security Council sanctions |
| 36 | World Bank Debarment | `world_bank` | *(merged above)* | -- | Debarred firms |
| 37 | Holdings (CNPJ derived) | `holdings` | -- | 59K HOLDING_DE | Derived from CNPJ socios |
| 38 | SIOP (Budget Amendments) | `siop` | 71.1K Amendment | -- | Parliamentary amendment execution |
| 39 | Senado CPIs | `senado_cpis` | 3 CPI | -- | Congressional investigations |

*\* InternationalSanction: 39.2K total across OFAC + EU + UN + World Bank*

**Production totals (2026-02-26):** ~141M nodes, ~92M relationships across 35 node labels and 33 relationship types.

---

## 2. PIPELINE EXISTS — DATA PENDING (3 sources)

| Source | Pipeline | Status | Blocker |
|--------|----------|--------|---------|
| PNCP (Bid Publications) | `pncp` | Downloading — 35 files (2021-08→2024-06), still running to 2026-02 | Time — API paginates by month |
| SICONFI (Municipal Finance) | `siconfi` | Downloading 2024 data (~530K/700K rows), pipeline fixed (CSV not JSON) | Time — 5,570 municipalities × 5 years |
| CAGED (Labor Movements) | `caged` | Pipeline rewritten as aggregate LaborStats. Needs re-download from PDET FTP | Public data has no employer CNPJ. FTP URL: `ftp://ftp.mtps.gov.br/pdet/microdados/NOVO CAGED/` |

---

## 3. NOT YET BUILT (60+ sources)

### 3.1 CGU / Transparencia Portal

| # | Source | URL | Format | Est. Volume | Nodes/Rels | Value | Notes |
|---|--------|-----|--------|-------------|------------|-------|-------|
| 1 | Bolsa Familia/BPC | portaldatransparencia.gov.br/download-de-dados/bolsa-familia-pagamentos | CSV | ~20M | SocialBenefit nodes | LOW | CPFs masked by LGPD |

### 3.2 BCB / Central Bank

| # | Source | URL | Format | Est. Volume | Nodes/Rels | Value | Notes |
|---|--------|-----|--------|-------------|------------|-------|-------|
| 2 | BCB Multas | dados.bcb.gov.br | CSV | ~5K | BankFine nodes | HIGH | Administrative fines |
| 3 | ESTBAN | dados.bcb.gov.br | CSV | ~500K/mo | BankingStats nodes | LOW | Bank branch balance sheets |
| 4 | IF.data | dados.bcb.gov.br | CSV | ~2K quarterly | FinancialInstitution nodes | LOW | Financial institution metrics |
| 5 | BCB Liquidacao | dados.bcb.gov.br | CSV | ~200 | BankLiquidation nodes | MEDIUM | Liquidated financial institutions |

### 3.3 Judiciary

| # | Source | URL | Format | Est. Volume | Nodes/Rels | Value | Notes |
|---|--------|-----|--------|-------------|------------|-------|-------|
| 6 | CNJ DataJud | api-publica.datajud.cnj.jus.br | REST API (self-service key) | Tens of millions | LegalCase nodes | VERY HIGH | Proceedings across all courts |
| 7 | STJ Dados Abertos | dadosabertos.stj.jus.br | CSV/XML | ~500K | LegalCase nodes | HIGH | Superior court decisions |
| 8 | CNCIAI (Improbidade) | cnj.jus.br (part of DataJud) | API | ~10K | ImprobityCase nodes | VERY HIGH | Administrative misconduct convictions |
| 9 | CARF (Tax Appeals) | carf.fazenda.gov.br | Structured | ~500K | TaxAppeal nodes | MEDIUM | Federal tax appeal decisions |

### 3.4 Regulatory Agencies (11 sources)

| # | Source | URL | Format | Est. Volume | Nodes/Rels | Value | Notes |
|---|--------|-----|--------|-------------|------------|-------|-------|
| 19 | ANP (Oil/Gas Royalties) | dados.gov.br/dados/conjuntos-dados/anp | API + CSV | ~100K/yr | Royalty, FuelPrice nodes | MEDIUM | Oil royalties + fuel pricing |
| 20 | ANEEL (Energy) | dadosabertos.aneel.gov.br | API | ~50K | EnergyContract nodes | MEDIUM | Energy concessions and contracts |
| 21 | ANM (Mining) | dados.gov.br/dados/conjuntos-dados/anm | API + CSV | ~100K | MiningConcession nodes | HIGH | Mining rights, often tied to deforestation |
| 22 | ANTT (Roads) | dados.gov.br/dados/conjuntos-dados/antt | API | ~10K | TransportContract nodes | LOW | Transport concessions |
| 23 | ANS (Health Insurance) | dados.gov.br/dados/conjuntos-dados/ans | API | ~50K | HealthPlan nodes | LOW | Health plan operators |
| 24 | ANVISA (Drug/Food) | dados.gov.br/dados/conjuntos-dados/anvisa | API | ~100K | RegulatoryApproval nodes | LOW | Product registrations |
| 25 | ANAC (Aviation) | dados.gov.br/dados/conjuntos-dados/anac | API | ~10K | AviationConcession nodes | LOW | Airport concessions |
| 26 | ANTAQ (Waterways) | dados.gov.br/dados/conjuntos-dados/antaq | API | ~5K | PortContract nodes | LOW | Port authority contracts |
| 27 | ANA (Water) | dados.gov.br/dados/conjuntos-dados/ana | API | ~10K | WaterConcession nodes | LOW | Water resource grants |
| 28 | ANATEL (Telecom) | dados.gov.br/dados/conjuntos-dados/anatel | API | ~50K | TelecomLicense nodes | LOW | Telecom licenses |
| 29 | SUSEP (Insurance) | dados.gov.br/dados/conjuntos-dados/susep | CSV | ~10K | InsuranceEntity nodes | LOW | Insurance market data |

### 3.5 Financial / Securities (2 sources)

| # | Source | URL | Format | Est. Volume | Nodes/Rels | Value | Notes |
|---|--------|-----|--------|-------------|------------|-------|-------|
| 30 | CVM Full (Ownership/Funds) | dados.cvm.gov.br | CSV | Millions | DETEM_PARTICIPACAO rels | HIGH | Shareholder chains, fund ownership |
| 31 | Receita DIRBI | dados.gov.br | CSV | Large | TaxBenefit nodes | MEDIUM | Tax benefit declarations |

### 3.6 Environmental (3 sources)

| # | Source | URL | Format | Est. Volume | Nodes/Rels | Value | Notes |
|---|--------|-----|--------|-------------|------------|-------|-------|
| 32 | MapBiomas Alerta | alerta.mapbiomas.org/api | REST API | 465K+ alerts | DeforestationAlert nodes | HIGH | Validated deforestation, property overlap |
| 33 | SiCAR (Rural Registry) | car.gov.br/publico/municipios/downloads | Bulk shapefiles | ~7M properties | RuralProperty nodes | HIGH | Rural property boundaries + owners |
| 34 | ICMBio/CNUC | icmbio.gov.br | API | ~2.5K | ConservationUnit nodes | LOW | Protected area boundaries |

### 3.7 Labor (2 sources)

| # | Source | URL | Format | Est. Volume | Nodes/Rels | Value | Notes |
|---|--------|-----|--------|-------------|------------|-------|-------|
| 35 | CAGED | basedosdados.org (br_me_caged) | BigQuery | ~2M/mo | LaborMovement nodes | MEDIUM | Monthly hiring/firing (no CPF in public data) |
| 36 | RAIS Microdata | basedosdados.org (br_me_rais) | BigQuery | ~50M/yr | DetailedLabor nodes | MEDIUM | Identified data requires formal authorization |

### 3.8 Budget / Fiscal (4 sources)

| # | Source | URL | Format | Est. Volume | Nodes/Rels | Value | Notes |
|---|--------|-----|--------|-------------|------------|-------|-------|
| 37 | SIOP Emendas | siop.planejamento.gov.br | CSV + API | ~30K/yr | DetailedAmendment nodes | HIGH | Parliamentary amendment execution details |
| 38 | SICONFI | siconfi.tesouro.gov.br | REST API (siconfipy) | ~5.5K municipalities | MunicipalFinance nodes | MEDIUM | Municipal/state fiscal data |
| 39 | Tesouro Emendas | tesouro.gov.br | CSV | ~50K | TreasuryAmendment nodes | HIGH | Treasury-tracked amendment spending |
| 40 | SIGA Brasil | www12.senado.leg.br/orcamento/sigabrasil | CSV export | Massive | BudgetExecution nodes | MEDIUM | Full federal budget execution |

### 3.9 Legislative (4 sources)

| # | Source | URL | Format | Est. Volume | Nodes/Rels | Value | Notes |
|---|--------|-----|--------|-------------|------------|-------|-------|
| 41 | Camara Full API (Votes/Bills) | dadosabertos.camara.leg.br/api/v2 | REST API + BigQuery | Millions | Vote, Bill nodes | MEDIUM | Deputy votes, bill authorship |
| 42 | Senado Full API (Votes/CPIs) | legis.senado.leg.br/dadosabertos | REST API + BigQuery | Large | SenateVote, CPI nodes | MEDIUM | Senate votes, CPI details |
| 43 | TSE Filiados | basedosdados.org (br_tse_eleicoes.filiacao_partidaria) | BigQuery | ~15M | PartyMember edges | MEDIUM | Party membership history |
| 44 | TSE Bens (Candidate Assets) | basedosdados.org (br_tse_eleicoes.bens_candidato) | BigQuery | ~500K | DeclaredAsset nodes | HIGH | Declared patrimony per election |

### 3.10 International Sanctions (5 sources)

| # | Source | URL | Format | Est. Volume | Nodes/Rels | Value | Notes |
|---|--------|-----|--------|-------------|------------|-------|-------|
| 45 | OFAC SDN | sanctionssearch.ofac.treas.gov | Direct CSV | ~12K | InternationalSanction nodes | HIGH | US Treasury sanctions list |
| 46 | EU Sanctions | data.europa.eu/data/datasets/consolidated-list-of-persons | Direct CSV | ~5K | InternationalSanction nodes | HIGH | EU consolidated sanctions |
| 47 | UN Sanctions | scsanctions.un.org/resources/xml | Direct XML | ~2K | InternationalSanction nodes | HIGH | UN Security Council sanctions |
| 48 | World Bank Debarment | worldbank.org/en/projects-operations/procurement/debarred-firms | CSV (OpenSanctions mirror) | ~1K | InternationalSanction nodes | MEDIUM | Debarred firms/individuals |
| 49 | INTERPOL Red Notices | interpol.int/How-we-work/Notices/Red-Notices | REST API | ~7K | InternationalNotice nodes | MEDIUM | Requires API key |

### 3.11 State / Municipal (10+ sources)

| # | Source | URL | Format | Est. Volume | Nodes/Rels | Value | Notes |
|---|--------|-----|--------|-------------|------------|-------|-------|
| 50 | PNCP Full | pncp.gov.br/api/consulta | Swagger REST API | Massive | Procurement nodes | HIGH | National procurement portal, paginate by date |
| 51 | TCE-SP | transparencia.tce.sp.gov.br | REST API | Large | StateProcurement nodes | HIGH | Sao Paulo state audit court |
| 52 | TCE-PE | sistemas.tce.pe.gov.br | REST API (CPF/CNPJ search) | Large | StateProcurement nodes | MEDIUM | Pernambuco audit court |
| 53 | TCE-RJ | dados.tce.rj.gov.br | REST API | Large | StateProcurement nodes | MEDIUM | Rio de Janeiro audit court |
| 54 | TCE-RS | portal.tce.rs.gov.br | Bulk downloads | Large | StateProcurement nodes | MEDIUM | Rio Grande do Sul audit court |
| 55 | MiDES | basedosdados.org (br_mides) | BigQuery | Massive | MunicipalProcurement nodes | VERY HIGH | 72% of municipalities covered |
| 56 | Querido Diario | queridodiario.ok.org.br/api | REST API + bulk ZIPs | 104K+ issues | MunicipalGazetteAct nodes | HIGH | Municipal gazette full text |
| 57-66 | State Transparency Portals | (SP, MG, BA, CE, GO, PR, SC, RS, PE, RJ) | Varies | Varies | StateExpense nodes | MEDIUM | Each state has its own portal |

---

## 4. GITHUB SHORTCUTS (pre-processed data)

Community-maintained datasets and tools that accelerate ingestion.

| # | Repo / Source | What | Volume | Value | Status |
|---|---------------|------|--------|-------|--------|
| G1 | brasil-io-public.s3.amazonaws.com (holding.csv.gz) | Company-to-company ownership chains | 787K rels, 9MB | HIGH | Ready to load |
| G2 | SINARC | Pre-built anti-corruption graph | 90GB | REFERENCE | Format unclear, use as validation |
| G3 | cnpj-chat/cnpj-data-pipeline | State-level CNPJ Parquet from GitHub Releases | Large | MEDIUM | Alternative CNPJ format |
| G4 | rictom/rede-cnpj | Pre-computed CNPJ relationship SQLite | Large | MEDIUM | Includes TSE/Transparencia crosslinks |
| G5 | hackfestcc/dados-hackfestcc | Curated anti-corruption datasets | Small | LOW | Reference datasets |
| G6 | DanielFillol/DataJUD_API_CALLER | Go-based DataJud bulk downloader | -- | HIGH | Speeds up CNJ ingestion |
| G7 | Serenata de Amor (suspicions.xz) | Flagged CEAP anomalies | 8K records | MEDIUM | Pre-analyzed deputy expenses |
| G8 | mcp-senado | MCP server wrapping Senate API (56 tools) | -- | LOW | Developer tool, not data |
| G9 | mcp-portal-transparencia | MCP server wrapping Transparency Portal API | -- | LOW | Developer tool, not data |

---

## 5. BIGQUERY DATASETS (via Base dos Dados)

[basedosdados.org](https://basedosdados.org) provides cleaned, standardized Brazilian public data in BigQuery. Free tier has limits; paid plans for heavy use.

| BQ Dataset ID | Key Tables | Loaded? | Notes |
|---------------|------------|---------|-------|
| br_rf_cnpj | empresas, socios, estabelecimentos | YES (direct CSV) | Used direct Receita download instead |
| br_tse_eleicoes | candidatos, receitas, despesas, bens_candidato, filiacao_partidaria | PARTIAL | Candidates + donations loaded via TSE direct; bens + filiados not yet |
| br_me_rais | microdados_vinculos | PARTIAL | Aggregate loaded; microdata requires formal auth |
| br_me_caged | microdados_movimentacao | NO | Monthly labor data |
| br_stf_corte_aberta | decisoes | NO | Supreme court decisions |
| br_camara_dados_abertos | votacao, proposicao, deputado | PARTIAL | Expenses loaded; votes/bills not yet |
| br_senado_cpipedia | cpi | NO | CPI investigation data |
| br_bd_diretorios_brasil | municipio, uf, setor_censitario | NO | Reference tables for joins |
| br_mides | licitacao, contrato, item | NO | Municipal procurement (72% coverage) |

---

## 6. INGESTION PRIORITY MATRIX

Recommended build order based on: value for pattern detection, implementation effort, and data volume.

| Priority | Source | Effort | Volume | Value | Rationale |
|----------|--------|--------|--------|-------|-----------|
| 1 | CGU PEP List | Trivial (CSV) | ~100K | HIGH | Replaces hardcoded PEP_ROLES; authoritative PEP classification |
| 2 | CEAF (Expelled Servants) | Easy (CSV) | ~10K | HIGH | Servants expelled for misconduct; cross-ref with companies |
| 3 | Acordos de Leniencia | Trivial (CSV) | ~34 | VERY HIGH | Companies that admitted wrongdoing; tiny dataset, immense value |
| 4 | OFAC SDN | Easy (CSV) | ~12K | HIGH | International sanctions; direct download, well-structured |
| 5 | Brasil.IO Holdings | Trivial (9MB download) | 787K rels | HIGH | Company-to-company ownership chains; immediate graph enrichment |
| 6 | DOU via IN XML | Medium (XML parsing) | Large | HIGH | Bypasses Cloudflare; official gazette appointments and acts |
| 7 | TSE Bens (Candidate Assets) | Easy (BigQuery) | ~500K | HIGH | Declared patrimony; detect unexplained wealth growth |
| 8 | TSE Filiados (Party Members) | Easy (BigQuery) | ~15M | MEDIUM | Party membership history; useful for political network mapping |
| 9 | CVM Full Ownership | Medium (CSV) | Millions | HIGH | Shareholder chains reveal hidden beneficial ownership |
| 10 | CNJ DataJud | Medium (API + key) | Massive | VERY HIGH | Judicial proceedings; largest gap in current graph |

### Effort Scale
- **Trivial**: Direct CSV download, schema matches existing patterns, <1 day
- **Easy**: CSV/BigQuery, minor transforms needed, 1-2 days
- **Medium**: API pagination, format conversion, or authentication required, 3-5 days
- **Hard**: Scraping, Cloudflare bypass, complex parsing, or formal data request, 1-2 weeks
