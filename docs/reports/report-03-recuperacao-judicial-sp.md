# Relatório de Investigação #03: Recuperação Judicial em São Paulo

> **Gerado por:** EGOS Inteligência (inteligencia.egos.ia.br)
> **Data:** 02/03/2026 | **Modelo LLM:** Google Gemini 2.0 Flash (via OpenRouter)
> **Stack:** Neo4j + FastAPI + React + DataJud (CNJ) + Portal da Transparência
> **Custo estimado desta análise:** ~R$ 0,05 (tokens LLM) + R$ 0,00 (APIs gratuitas)

---

## Panorama: Recuperações Judiciais no TJSP

| Métrica | Valor | Fonte |
|---------|-------|-------|
| **Total de processos** | 3.704 | DataJud (CNJ) — TJSP |
| **Classe processual** | Recuperação Judicial | CNJ — Tabela Unificada |
| **Período** | Todos os anos disponíveis | DataJud |
| **Tribunal** | TJSP (Tribunal de Justiça de São Paulo) | CNJ |

---

## Processos Mais Recentes

| Número | Órgão Julgador | Data | Assuntos |
|--------|---------------|------|----------|
| 4000081662026826... | 1ª Vara Reg. Comp. Empresarial — Foro Especial 1ª, 7ª e 9ª RAJs | 22/01/2026 | Recuperação Judicial e Falência |
| 4084118552025826... | 2ª Vara Reg. Comp. Empresarial — Foro Especial 1ª, 7ª e 9ª RAJs | 20/12/2025 | Recuperação Judicial e Falência |
| 4082689532025826... | 1ª Vara de Falências e Recuperações Judiciais — Foro Central Cível | 18/12/2025 | Recuperação Judicial e Falência, Falência |
| 4023735692025826... | Vara Reg. Comp. Empresarial — Foro Especial 4ª e 10ª RAJs | 18/12/2025 | Recuperação Judicial e Falência, Liminar |
| 4081489112025826... | 3ª Vara de Falências e Recuperações Judiciais — Foro Central Cível | 17/12/2025 | Recuperação Judicial e Falência |

---

## Por Que Isso Importa?

### Para o Cidadão
Empresas em recuperação judicial **continuam operando**, mas podem:
- ❌ Não pagar fornecedores pequenos
- ❌ Ganhar licitações públicas mesmo endividadas (irregularidade)
- ❌ Demitir funcionários sem pagar rescisão
- ❌ Transferir ativos para empresas "limpas" dos mesmos sócios

### Para Investigadores
O cruzamento de dados revela padrões:
- **Empresa em RJ + contrato público ativo** = irregularidade grave
- **Mesmo sócio em empresa em RJ e empresa nova** = possível fraude patrimonial
- **Fornecedor do governo entra em RJ logo após receber pagamento** = suspeita de desvio

---

## Passo a Passo: Reproduzindo Esta Análise

### 1. Buscar recuperações judiciais (qualquer tribunal)

```
Acesse inteligencia.egos.ia.br → Chatbot
Pergunte: "Buscar processos de recuperação judicial no TJSP"
```

### 2. Identificar a empresa

```
Pergunte: "Quem são os sócios da empresa [NOME]?"
O sistema consulta: Receita Federal (CNPJ/QSA) + BrasilAPI
```

### 3. Verificar se tem contratos com o governo

```
Pergunte: "A empresa [NOME] tem contratos com o governo federal?"
O sistema consulta: Portal da Transparência (API com chave)
```

### 4. Verificar se está sancionada

```
Pergunte: "A empresa [NOME] está no CEIS ou CNEP?"
O sistema consulta: Portal da Transparência — cadastros de sanções
```

### 5. Buscar no diário oficial

```
Pergunte: "O que saiu no diário oficial sobre [NOME DA EMPRESA]?"
O sistema consulta: Querido Diário (510+ cidades)
```

---

## Execuções Fiscais — Complemento

Além das recuperações judiciais, o TJSP tem **10.000+ execuções fiscais** recentes, indicando empresas que devem impostos ao governo.

| Número | Órgão | Data |
|--------|-------|------|
| 1003624292025826... | SAF de Itapira | 31/12/2025 |
| 1003623442025826... | SAF de Itapira | 31/12/2025 |
| 1003622592025826... | SAF de Itapira | 31/12/2025 |

> **Cross-reference:** Empresa com execução fiscal + contrato público = recebendo dinheiro público enquanto deve ao governo.

---

## O Que Falta Para Completar

| Dado | Status | Quando |
|------|--------|--------|
| **Nome das empresas nos processos** | DataJud não expõe partes por padrão (sigilo) | Necessário consulta individual |
| **CNPJ das empresas em RJ** | Precisa cruzar com ETL Receita Federal | ETL 15% → 100% (~3-5 dias) |
| **Contratos ativos dessas empresas** | Portal Transparência requer código do órgão | Disponível por consulta |
| **Sócios em comum entre empresas** | Grafo Neo4j com QSA completo | Após ETL completo |
| **Doações de campanha dos sócios** | TSE bulk data | Próximo ETL planejado |

---

## Stack Técnica Completa

| Camada | Tecnologia | Função |
|--------|-----------|--------|
| **Grafo** | Neo4j 5.x (317K nós, 34K rels) | Entidades + conexões |
| **API** | FastAPI (Python 3.12) | 18 ferramentas investigativas |
| **LLM** | Gemini 2.0 Flash (OpenRouter) | Análise inteligente |
| **Frontend** | React 18 + Vite + D3.js | Visualização interativa |
| **Cache** | Redis 7 | Performance + analytics |
| **Proxy** | Caddy (auto-SSL) | HTTPS automático |
| **Servidor** | Contabo VPS (8vCPU, 30GB) | ~€15/mês |
| **Busca Web** | Brave Search API | #1 benchmark, 669ms |
| **APIs Públicas** | Portal Transparência, DataJud, TransfereGov, Câmara, Querido Diário | Gratuitas |

### Custo Total de Operação

| Item | Custo/Mês (USD) |
|------|-----------|
| Servidor Contabo (8vCPU, 30GB) | $35 |
| Supabase Pro (PostgreSQL) | $20 |
| Windsurf IDE (AI-assisted dev) | $45 |
| OpenRouter (LLM — Gemini 2.0 Flash) | ~$5 |
| Brave Search API | $0-5 |
| APIs públicas (Portal, DataJud, etc.) | $0 |
| **TOTAL** | **~US$ 105/mês (~R$ 630)** |

---

*"Justiça e transparência não deveriam ser acessíveis apenas para quem pode pagar milhões por ferramentas como Palantir."*
*EGOS Inteligência — inteligencia.egos.ia.br — Open source. Dados abertos. Para todos.*
