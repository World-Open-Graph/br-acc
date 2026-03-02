# Relatório de Investigação #02: Transparência Municipal — Manaus (AM)

> **Gerado por:** EGOS Inteligência (inteligencia.egos.ia.br)
> **Data:** 02/03/2026 | **Modelo LLM:** Google Gemini 2.0 Flash (via OpenRouter)
> **Stack:** Neo4j + FastAPI + React + DataJud + Portal da Transparência + Querido Diário
> **Custo estimado desta análise:** ~R$ 0,05 (tokens LLM) + R$ 0,00 (APIs gratuitas)

---

## Panorama do Município

| Campo | Valor |
|-------|-------|
| **Município** | Manaus |
| **UF** | Amazonas |
| **Código IBGE** | 1302603 |
| **População** | ~2.2 milhões |
| **Região** | Norte |

---

## 1. Emendas Parlamentares Direcionadas

Consultando o Portal da Transparência (API oficial, chave gratuita):

| Autor | Ano | Tipo de Emenda |
|-------|-----|----------------|
| VINICIUS GURGEL | 2018 | Emenda Individual - Transferências com Finalidade Definida |
| COMISSÃO DE FINANÇAS E TRIBUTAÇÃO - CFT | 2020 | Emenda de Comissão |
| RAUL HENRY | 2015 | Emenda Individual - Transferências com Finalidade Definida |
| RELATOR GERAL | 2020 | Emenda de Relator |
| CABUCU BORGES | 2019 | Emenda Individual - Transferências com Finalidade Definida |

> **15 emendas federais** direcionadas a Manaus encontradas.
> **Investigação sugerida:** Verificar se os deputados que destinam emendas têm relação com fornecedores locais.

---

## 2. Processos Judiciais (DataJud — TJAM)

### Ações Civis Públicas: 4.664 processos

| Número | Órgão Julgador | Data | Assuntos |
|--------|---------------|------|----------|
| 0018859782026804... | Vara Especializada do Meio Ambiente | 28/01/2026 | Indenização por Dano Ambiental |
| 0000078312026804... | Vara da Comarca de Beruri | 27/01/2026 | Liminar |
| 0017254972026804... | Vara Especializada do Meio Ambiente | 27/01/2026 | Dano Ambiental |
| 0600077682026804... | 2ª Vara da Comarca de Tefé | 23/01/2026 | Obrigação de Fazer/Não Fazer |
| 0000042162026804... | Vara da Comarca de Barcelos | 22/01/2026 | Abuso de Poder |

> **Destaque:** Alta concentração de ações ambientais (Vara Especializada do Meio Ambiente).
> Amazônia é foco de fiscalização — cruzar com empresas com contratos de desmatamento/mineração.

---

## 3. Passo a Passo: Como Reproduzir Esta Análise

### Para Cidadãos (sem conhecimento técnico)

1. **Acesse** inteligencia.egos.ia.br
2. **Clique no chatbot** (ícone de conversa no canto)
3. **Pergunte:**
   - "Quais emendas parlamentares vão para Manaus?"
   - "Buscar processos judiciais recentes no Amazonas"
   - "Quais empresas sancionadas em Manaus?"
   - "O que saiu no diário oficial de Manaus sobre licitações?"
4. **O sistema faz o cruzamento automaticamente:**
   - Emendas (TransfereGov) → quem mandou dinheiro
   - Processos (DataJud) → quem está sendo processado
   - Sanções (CEIS/CNEP) → quem está impedido de contratar
   - Diários oficiais (Querido Diário) → o que foi publicado oficialmente
5. **Exporte o resultado** como PDF ou compartilhe o link

### Para Desenvolvedores

```python
# 1. Emendas para Manaus
GET https://api.portaldatransparencia.gov.br/api-de-dados/emendas?codigoIBGE=1302603
Headers: chave-api-dados: [SUA_CHAVE_GRATUITA]

# 2. Processos judiciais TJAM
POST https://api-publica.datajud.cnj.jus.br/api_publica_tjam/_search
Headers: Authorization: APIKey [SUA_CHAVE]
Body: {"query":{"match_phrase":{"classe.nome":"Ação Civil Pública"}},"size":5}

# 3. Diários oficiais Manaus
GET https://queridodiario.ok.org.br/api/gazettes?territory_id=1302603&querystring=licitacao

# 4. Sanções (CEIS)
GET https://api.portaldatransparencia.gov.br/api-de-dados/ceis?pagina=1
```

---

## 4. O Que Falta Para Completar

| Dado Faltante | Impacto | Prioridade |
|---------------|---------|-----------|
| **Dados municipais de licitações** | Manaus não tem API de licitações aberta | Crawler necessário |
| **Folha de pagamento municipal** | Supersalários escondidos | Portal municipal não tem API |
| **Relação deputados ↔ fornecedores** | Conflito de interesses | ETL 53M empresas (15% concluído) |
| **Doações de campanha** | Financiamento eleitoral | TSE bulk data (próximo ETL) |
| **Imagens de satélite** | Desmatamento ilegal | Integração INPE futura |

---

## 5. Infraestrutura e Custos

| Componente | Tecnologia | Custo Mensal (USD) |
|-----------|-----------|-------------|
| **Servidor** | Contabo VPS (8 vCPU, 30GB RAM) | $35/mês |
| **Banco de dados** | Supabase Pro (PostgreSQL) | $20/mês |
| **IDE/Dev** | Windsurf IDE (AI-assisted) | $45/mês |
| **Banco de grafos** | Neo4j Community (317K nós) | Grátis |
| **LLM** | Gemini 2.0 Flash via OpenRouter | ~$5/mês |
| **Web Search** | Brave Search API (2K grátis/mês) | $0-5/mês |
| **APIs públicas** | Portal Transparência, DataJud, Querido Diário | Grátis |
| **Frontend** | React + Vite (Caddy) | Grátis |
| **Total mensal** | | **~US$ 105/mês (~R$ 630)** |

> **Comparação:** Palantir Gotham custa ~US$10 milhões/ano. Nós fazemos o mesmo tipo de análise por ~US$105/mês (~R$630).

---

*"A transparência pública não deveria custar milhões. Deveria ser gratuita."*
*EGOS Inteligência — inteligencia.egos.ia.br*
