# Avaliação Honesta: O Que Realmente Funciona (e o que não funciona)

> **Data:** 2026-03-02 | **Versão:** 1.0 | **Autor:** Equipe EGOS
> **Propósito:** Ser brutalmente honesto sobre nossas capacidades atuais

---

## O Que Realmente Fazemos Hoje

### O que funciona de verdade

| Capacidade | Exemplo Real | Qualquer pessoa faria com ChatGPT? |
|-----------|-------------|-----------------------------------|
| **Consulta BNDES** | R$ 217M para Patense em 591 operações | ❌ Não — API obscura, poucas pessoas sabem que existe |
| **CEIS/CNEP unificado** | 15 empresas em ambas as listas | ⚠️ Sim, mas levaria horas no Portal da Transparência |
| **PEP × OpenSanctions** | 7.044 brasileiros em listas internacionais | ❌ Não — requer ter ambos datasets e fazer matching |
| **Busca em Diários Oficiais** | Querido Diário com 5.570+ municípios | ⚠️ Sim via site, mas sem cruzamento automático |
| **Bot 24/7** | Discord + Telegram com 14 ferramentas | ❌ Não existe equivalente gratuito com estas fontes |

### O que NÃO funciona (ainda)

| Promessa | Realidade | O que falta |
|----------|-----------|-------------|
| **"Grafo de vínculos"** | Sem CNPJ/QSA, o grafo não conecta sócios a empresas | Baixar 60GB CNPJ da Receita Federal |
| **"Investigação automática"** | O bot faz consultas individuais, não encadeia raciocínio | Modelo de IA mais potente (Gemini 3.1 Pro ou Claude Opus 4.6) |
| **"Cross-referencing inteligente"** | Na prática são JOINs SQL entre tabelas | Algoritmos de grafo (PageRank, Community Detection) |
| **"Detectar fraude"** | Mostramos dados, não detectamos padrões automaticamente | ML/Anomaly Detection, Benford's Law, HHI |
| **"Relatórios de investigação"** | São markdown estáticos, não interativos | Frontend com visualização de grafo clicável |

### Comparação honesta: nós vs alternativas

| | BR/ACC (nós) | ChatGPT + busca web | Portal da Transparência | Aleph/OCCRP |
|---|---|---|---|---|
| **BNDES por empresa** | ✅ API integrada | ❌ Não sabe que existe | ✅ Manual no site | ❌ Foco global |
| **CEIS+CNEP cruzado** | ✅ Automático | ⚠️ Se souber perguntar | ✅ Manual | ❌ |
| **PEP × sanções globais** | ✅ 7k matches | ❌ | ❌ | ✅ Melhor que nós |
| **Rede societária** | ❌ Sem CNPJ | ⚠️ Busca caso a caso | ⚠️ Manual | ✅ 270M entidades |
| **Acessibilidade** | ✅ Bot gratuito | ✅ Todos têm | ⚠️ Interface ruim | ❌ Pago/restrito |
| **Open source** | ✅ 100% | ❌ | ❌ | ✅ MIT |

---

## O Que Torna Nosso Projeto Único (de verdade)

### 1. Infraestrutura aberta que ninguém mais oferece no Brasil

Não existe outro projeto open-source brasileiro que unifique CEIS + CNEP + PEP + OpenSanctions + BNDES + TSE + Diários Oficiais em um único grafo consultável por bot.

**Serenata de Amor:** Focou só em CEAP (gastos parlamentares). Abandonado desde 2022.
**Querido Diário:** Só diários oficiais. Não cruza com sanções/PEPs.
**Portal da Transparência:** Interface web péssima, sem API para cruzamentos.

### 2. O bot é GRATUITO e acessível a qualquer cidadão

Um jornalista ou cidadão pode perguntar "quanto a empresa X recebeu do BNDES?" no Telegram e ter resposta em 10 segundos. Sem precisar saber programar, sem conta paga, sem intermediário.

### 3. O potencial do grafo (quando CNPJ carregar)

Com 53.6M empresas + QSA, os cruzamentos se tornam impossíveis de fazer manualmente:
- "Político X é sócio de empresa Y que ganhou contrato Z do órgão onde ele trabalha"
- "Empresa sancionada mudou de CNPJ mas manteve os mesmos sócios"
- "47 empresas compartilham o mesmo endereço fiscal"

**Isso ninguém faz no Brasil hoje. Nem o Aleph.**

---

## O Que os Relatórios do Showcase Realmente Mostram

### Investigação 1-4, 6 (SQL JOINs)

**Honestidade:** São agregações simples (GROUP BY, COUNT, FILTER) sobre dados públicos. Qualquer analista de dados faria o mesmo com um CSV e Excel em 30 minutos.

**Valor real:** Automatizar essas consultas e disponibilizá-las via bot para quem NÃO sabe SQL.

### Investigação 5 (PEP × OpenSanctions)

**Honestidade:** O matching é por nome, com fuzzy matching simples. Pode ter falsos positivos.

**Valor real:** Ninguém mais no Brasil está fazendo esse cruzamento de forma aberta.

### Investigação Patense (a melhor)

**Honestidade:** Usamos a API do BNDES (que é pública), web search, e Neo4j. O relatório foi gerado por uma IA avançada (Claude Sonnet), não pelo bot.

**Valor real:** A síntese (R$ 217M → 13 empresas → 5 SPEs → perguntas investigativas) requer raciocínio em cadeia que modelos baratos não fazem. O pipeline (BNDES API → Neo4j → relatório) é genuinamente útil.

---

## Plano de Ação: Do Honesto ao Incrível

### Curto prazo (esta semana)

1. ✅ Carregar CNPJ (quando download completar) — transforma tudo
2. ✅ Melhorar bot: respostas curtas, recomendar CPF/CNPJ, explicar limitações
3. ✅ Atualizar modelos de IA para março 2026

### Médio prazo (mês 1)

4. Frontend interativo com grafo clicável (não mais markdown estático)
5. Algoritmos de grafo reais (PageRank, Betweenness)
6. Sistema de investigações compartilhadas (anônimas, crowd-sourced)

### Longo prazo (mês 2-3)

7. Anomaly detection automático (Benford, temporal patterns)
8. Entity resolution cross-dataset (fuzzy matching avançado)
9. MCP Server para IDEs (investigação profunda com memória persistente)

---

*"A honestidade sobre limitações gera mais confiança do que promessas vazias."*
