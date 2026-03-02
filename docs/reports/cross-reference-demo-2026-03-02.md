# Relatório de Demonstração: Cross-Reference com 18 Ferramentas

> **Data:** 02/03/2026 | **Status:** Demonstração de Capacidades
> **Plataforma:** EGOS Inteligência (inteligencia.egos.ia.br)

---

## 1. Visão Geral do Grafo

| Métrica | Valor |
|---------|-------|
| **Total de nós** | 317.583 |
| **Relacionamentos** | 34.507 |
| **Pessoas** | 7.074 |
| **Empresas** | 11.597 |
| **Sanções (CEIS/CNEP/OpenSanctions)** | 23.848 |
| **PEPs (Pessoas Expostas Politicamente)** | 133.859 + 117.901 globais |
| **Gastos CPGF (Cartão Corporativo)** | 6.483 |
| **Viagens a Serviço** | 13.184 |
| **ONGs Impedidas (CEPIM)** | 3.590 |
| **Fontes de Dados** | 108 catalogadas, 36 carregadas |

---

## 2. Demonstração: Município de Patos de Minas (MG)

### 2.1. Emendas Parlamentares Direcionadas

Consultando o Portal da Transparência (API com chave):

| Autor | Ano | Tipo |
|-------|-----|------|
| VINICIUS GURGEL | 2018 | Emenda Individual - Transferências com Finalidade Definida |
| COMISSAO DE FINANCAS E TRIBUTACAO - CFT | 2020 | Emenda de Comissão |
| RAUL HENRY | 2015 | Emenda Individual - Transferências com Finalidade Definida |
| RELATOR GERAL | 2020 | Emenda de Relator |
| CABUCU BORGES | 2019 | Emenda Individual - Transferências com Finalidade Definida |

> **15 emendas federais** direcionadas ao município de Patos de Minas (IBGE 3148004).
> **Investigação sugerida:** Quem são esses deputados? Qual a relação com fornecedores locais?

### 2.2. Processos Judiciais (DataJud — TJMG)

Comarca de Patos de Minas: **10.000+ processos** indexados.

| Número | Classe | Data | Assuntos |
|--------|--------|------|----------|
| 10023874... | Inventário | 25/02/2026 | Inventário e Partilha |
| 10023865... | Procedimento Comum Cível | 25/02/2026 | Responsabilidade Civil |
| 10023848... | Procedimento Comum Cível | 25/02/2026 | Liminar |
| 10023787... | Mandado de Segurança | 25/02/2026 | Abuso de Poder |
| 10023735... | Execução de Título Extrajudicial | 25/02/2026 | Cédula de Crédito Rural |

### 2.3. Empresas no Grafo (Neo4j)

Empresas com "Minas" (amostra):
- MINAS CAPITAL COMERCIO DE ALIMENTOS LTDA
- MINAS MED DISTRIBUIDORA DE MEDICAMENTOS LTDA
- MINAS BRAZIL DISTRIBUIDORA EIRELI
- SUDESTE MINAS CONSTRUTORA LTDA - ME

### 2.4. Sanções CEIS

- **GUILHERME CARRAPATOSO GARCIA SERVICOS ADMINISTRATIVOS** — Sancionado pelo TJTO em 28/11/2024

---

## 3. Demonstração: Recuperação Judicial (DataJud TJMG)

**1.180 processos de Recuperação Judicial** no TJMG.

| Número | Orgão Julgador | Data | Assuntos |
|--------|---------------|------|----------|
| 10287957... | 1ª Vara Empresarial BH | 24/02/2026 | Recuperação Judicial e Falência |
| 50004531... | 2ª Vara Cível Tupaciguara | 11/02/2026 | Classificação de créditos |
| 10001552... | Vara Única Camanducaia | 02/02/2026 | Concurso de Credores |

> **Cross-reference:** Cruzar empresas em RJ com fornecedores do governo federal.

---

## 4. Empresas Sancionadas (Portal da Transparência)

| Empresa | Órgão Sancionador | Tipo | Data |
|---------|-------------------|------|------|
| GK3 Soluções e Consultoria LTDA | DATAPREV | Impedimento de contratar | 30/12/2024 |
| BELART TECNOLOGIA EM CONSTRUCOES LTDA | TJSC | Suspensão | 21/11/2025 |
| FB MULTI NEGOCIOS LTDA | Pref. Ibiraiaras-RS | Impedimento de contratar | 18/07/2023 |

---

## 5. Fluxo de Investigação: "Puxar o Fio"

```
ENTRADA: Nome de cidade, político, empresa ou CNPJ
  → GRAFO: Neo4j (317K nós)
  → EMENDAS + TRANSFERÊNCIAS: TransfereGov
  → CEAP + VOTAÇÕES: Câmara dos Deputados
  → SERVIDORES + SALÁRIOS: Portal da Transparência
  → CNPJ + SÓCIOS: Querido Diário / ETL Receita Federal
  → CONTRATOS + SANÇÕES: Portal da Transparência (CEIS+CNEP)
  → CPGF + VIAGENS: Portal da Transparência
  → DIÁRIO OFICIAL: Querido Diário (510+ cidades)
  → PROCESSOS JUDICIAIS: DataJud (CNJ) — todos tribunais
  → WEB SEARCH: Notícias, denúncias
= RELATÓRIO com evidências cruzadas de múltiplas fontes
```

### 18 Ferramentas Disponíveis

| # | Ferramenta | Fonte | API Key |
|---|-----------|-------|---------|
| 1-3 | search_entities, graph_stats, connections | Neo4j | — |
| 4 | web_search | DuckDuckGo | Não |
| 5-6 | emendas, transferencias | TransfereGov | Não |
| 7-8 | ceap, pep_city | Câmara | Não |
| 9-10 | gazettes, cnpj_info | Querido Diário | Não |
| 11 | votacoes | Câmara | Não |
| 12-16 | servidores, licitacoes, cpgf, viagens, contratos | Portal Transparência | **Sim** |
| 17 | sancoes (CEIS+CNEP) | Portal Transparência | **Sim** |
| 18 | processos judiciais | DataJud (CNJ) | **Sim** |

---

*"Siga o dinheiro público. Dados abertos, código aberto."*
*EGOS Inteligência — inteligencia.egos.ia.br*
