# Plataforma de Investigacoes Compartilhadas

> **Data:** 2026-03-02 | **Status:** Planejamento
> **Principio:** Conectar pontos, nunca acusar. Inteligencia coletiva com governanca.

---

## Conceito

Cada cidadao brasileiro conhece melhor sua cidade, seus politicos, suas empresas locais. Um morador de Patos de Minas sabe coisas sobre a Patense que nenhum jornalista de SP vai descobrir. Nosso papel e dar a **infraestrutura** pra essas pessoas encontrarem e conectarem dados publicos.

### O que NAO somos

- Nao somos um tribunal. Nunca afirmamos culpa.
- Nao somos jornalistas. Nao publicamos materias.
- Nao somos delatores. Nao incentivamos denuncia anonima.

### O que SOMOS

- Uma ferramenta de **transparencia** que cruza dados publicos.
- Uma comunidade que **corrige e melhora** informacoes.
- Um sistema que **conecta pontos** de forma visual e auditavel.

---

## Arquitetura

### 1. Relatorios Gerados pelo Bot/Sistema

Quando o bot consulta dados, ele gera um **permalink** do resultado:

```
https://bracc.egos.ia.br/r/abc123
```

O relatorio contem:
- Dados consultados (BNDES, CEIS, CNEP, PEP, etc)
- Ferramentas usadas e timestamp
- Modelo de IA usado
- Fontes com links clicaveis
- Status de cada base (temos / nao temos)
- Hash de integridade (SHA-256 do conteudo)

### 2. Compartilhamento Anonimo

- Qualquer pessoa pode compartilhar um link de relatorio
- Nao exige cadastro pra VER
- Exige cadastro (email ou OAuth) pra CONTRIBUIR
- Contribuicoes sao pseudonimas (user-hash, nunca nome real)

### 3. Sistema de Correcoes (Crowd Intelligence)

Cada dado no relatorio pode receber:
- **Confirmacao** ("Eu confirmo, trabalho na regiao e sei que...")
- **Correcao** ("O CNPJ correto e X, nao Y")
- **Adendo** ("Essa empresa tambem opera como Z na cidade W")
- **Contexto** ("Esse contrato foi cancelado em 2024, nao esta vigente")

Regras de governanca:
- Cada contribuicao e versionada (git-like)
- Contribuicoes precisam citar fonte (link, documento, lei)
- 3+ confirmacoes independentes = dado ganha badge "verificado pela comunidade"
- Moderacao: nada e publicado sem revisao automatica (PII filter, hate speech detection)

### 4. Conexao Automatica entre Investigacoes

O sistema analisa TODAS as pesquisas feitas por todos os usuarios e detecta:
- **Entidades em comum:** "5 pessoas diferentes pesquisaram a empresa X"
- **Grafos emergentes:** "Empresa A → Socio B → Empresa C apareceu em 3 pesquisas distintas"
- **Alertas temporais:** "3 pesquisas sobre o municipio Y no mesmo mes"

Isso e feito de forma **agregada e anonima** — ninguem sabe quem pesquisou o que, mas o sistema detecta padroes.

### 5. Governanca

| Regra | Implementacao |
|-------|---------------|
| Nunca acusar | IA filtra linguagem acusatoria antes de publicar |
| Fonte obrigatoria | Contribuicao sem fonte = nao publicada |
| PII Protection | CPFs, enderecos pessoais sao mascarados automaticamente |
| Direito de resposta | Qualquer pessoa/empresa mencionada pode solicitar correcao |
| Auditoria | Log de todas as acoes, imutavel |
| Transparencia | Codigo 100% open source, dados publicos |

---

## Tabela Supabase (schema inicial)

```sql
-- Relatorios gerados
CREATE TABLE osint_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL, -- permalink: /r/abc123
    title TEXT NOT NULL,
    query TEXT NOT NULL, -- o que foi pesquisado
    tools_used TEXT[] NOT NULL, -- ferramentas usadas
    ai_model TEXT NOT NULL, -- modelo de IA
    content JSONB NOT NULL, -- dados estruturados
    content_hash TEXT NOT NULL, -- SHA-256
    sources JSONB NOT NULL, -- fontes com URLs
    data_gaps TEXT[], -- bases que faltaram
    platform TEXT, -- discord/telegram/web
    created_by TEXT, -- user-hash anonimo
    views INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Contribuicoes da comunidade
CREATE TABLE osint_contributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID REFERENCES osint_reports(id),
    type TEXT CHECK (type IN ('confirmation', 'correction', 'addition', 'context')),
    content TEXT NOT NULL,
    source_url TEXT, -- fonte obrigatoria
    contributor_hash TEXT NOT NULL, -- pseudonimo
    verified_count INTEGER DEFAULT 0, -- quantas confirmacoes
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'published', 'rejected')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Deteccao de padroes (conexoes entre pesquisas)
CREATE TABLE osint_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type TEXT NOT NULL, -- 'shared_entity', 'emerging_graph', 'temporal_cluster'
    entities TEXT[] NOT NULL, -- entidades envolvidas
    report_ids UUID[] NOT NULL, -- relatorios conectados
    confidence FLOAT, -- 0-1
    description TEXT,
    detected_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Padronizacao de Relatorios

### Formato obrigatorio (todo relatorio gerado)

```json
{
  "version": "1.0",
  "title": "Consulta: Grupo Patense",
  "generated_at": "2026-03-02T04:00:00Z",
  "ai_model": "Gemini 2.0 Flash",
  "tools_used": ["bndes_search", "bracc_company_graph", "web_search"],
  "query": "patense racoes bndes",
  "sections": [
    {
      "source": "BNDES Dados Abertos",
      "source_url": "https://dadosabertos.bndes.gov.br",
      "status": "found",
      "data": { ... },
      "confidence": "high"
    },
    {
      "source": "CEIS/CGU",
      "source_url": "https://portaldatransparencia.gov.br/sancoes/ceis",
      "status": "not_found",
      "note": "Nenhuma sancao encontrada para as empresas consultadas"
    },
    {
      "source": "CNPJ/QSA (Receita Federal)",
      "status": "unavailable",
      "note": "Base em download. Quando disponivel, poderemos mapear socios."
    }
  ],
  "data_gaps": [
    "CNPJ/QSA nao carregado — nao foi possivel verificar socios",
    "DataJud nao integrado — nao foi possivel verificar processos judiciais"
  ],
  "disclaimer": "Dados publicos sao sinais, nao prova juridica."
}
```

### Visual (frontend)

Cada secao do relatorio:
- **Verde** = dado encontrado e verificado
- **Cinza** = dado buscado, nao encontrado
- **Amarelo** = base indisponivel (explica por que)
- **Azul** = link clicavel pra fonte original
- CNPJs e CPFs publicos sao clicaveis (abre nova consulta)
- Nomes de empresas sao clicaveis (busca no grafo)
- Botao "Compartilhar" gera link anonimo
- Botao "Contribuir" abre formulario de correcao

---

## Implementacao (fases)

### Fase 1 (esta semana)
- [ ] Criar tabela `osint_reports` no Supabase
- [ ] Bot salva resultado de cada consulta como relatorio
- [ ] Gerar permalink `/r/{slug}` para cada relatorio
- [ ] Pagina web simples que renderiza o JSON como HTML bonito

### Fase 2 (semana 2)
- [ ] Sistema de contribuicoes (correcoes, adendos)
- [ ] Pseudonimizacao de contribuidores
- [ ] Filtro automatico de PII

### Fase 3 (semana 3-4)
- [ ] Deteccao de padroes entre pesquisas
- [ ] Alertas de entidades recorrentes
- [ ] Dashboard de tendencias

---

*"Cada brasileiro conhece sua cidade melhor que qualquer algoritmo. Nosso papel e dar a ferramenta."*
