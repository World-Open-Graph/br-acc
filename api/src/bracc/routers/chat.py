"""Chat endpoint — AI agent for EGOS Inteligência.

Full conversational agent with:
- LLM via OpenRouter (GPT-4o-mini — optimized for multi-tool calling)
- Neo4j graph search tools
- Conversation memory (in-memory per session, Redis planned)
- Contextual suggestions
- LGPD-compliant (no CPF exposure)
"""

import json
import logging
import re
import time
from collections import defaultdict
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends
from neo4j import AsyncSession
from pydantic import BaseModel, Field
from starlette.requests import Request

from bracc.config import settings
from bracc.dependencies import get_session
from bracc.middleware.rate_limit import limiter
from bracc.services.neo4j_service import execute_query, sanitize_props
from bracc.routers.activity import log_activity
from bracc.services.transparency_tools import (
    tool_web_search,
    tool_search_emendas,
    tool_search_transferencias,
    tool_search_ceap,
    tool_search_pep_city,
    tool_search_gazettes,
    tool_cnpj_info,
    tool_search_votacoes,
    tool_search_servidores,
    tool_search_licitacoes,
    tool_search_cpgf,
    tool_search_viagens,
    tool_search_contratos,
    tool_search_sancoes,
    tool_search_processos,
    tool_bnmp_mandados,
    tool_procurados_lookup,
    tool_lista_suja,
    tool_pncp_licitacoes,
    tool_oab_advogado,
    tool_opencnpj,
)
from bracc.services.public_guard import (
    has_person_labels,
    sanitize_public_properties,
    should_hide_person_entities,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])

_CNPJ_RE = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")
_LUCENE_SPECIAL = re.compile(r'([+\-&|!(){}\[\]^"~*?:\\/])')

# --- In-memory conversation store (keyed by IP, max 20 messages, 30min TTL) ---
_conversations: dict[str, list[dict[str, str]]] = defaultdict(list)
_conversation_ts: dict[str, float] = {}
_MAX_HISTORY = 20
_TTL_SECONDS = 1800

# --- Rate limit + model fallback (per IP, resets daily) ---
_usage_counts: dict[str, int] = defaultdict(int)
_usage_day: dict[str, str] = {}

# Tier thresholds: msgs 1-10 = premium, 11-30 = free, 31+ = blocked (suggest BYOK)
_TIER_PREMIUM_LIMIT = 10
_TIER_FREE_LIMIT = 30

# Model tiers
MODEL_PREMIUM = "openai/gpt-4o-mini"           # ~$0.001/query, best tool-calling
MODEL_FREE = "google/gemini-2.0-flash-001"      # ~$0.0003/query, decent but single-tool

def _get_client_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_usage(client_id: str) -> int:
    """Get daily usage count, reset if new day."""
    today = time.strftime("%Y-%m-%d")
    if _usage_day.get(client_id) != today:
        _usage_counts[client_id] = 0
        _usage_day[client_id] = today
    return _usage_counts[client_id]


def _increment_usage(client_id: str) -> int:
    """Increment and return new usage count."""
    today = time.strftime("%Y-%m-%d")
    if _usage_day.get(client_id) != today:
        _usage_counts[client_id] = 0
        _usage_day[client_id] = today
    _usage_counts[client_id] += 1
    return _usage_counts[client_id]


def _select_model(client_id: str, byok_key: str = "") -> tuple[str, str, str]:
    """Select model based on usage tier or BYOK. Returns (model, api_key, tier_label)."""
    if byok_key:
        return MODEL_PREMIUM, byok_key, "byok"
    usage = _get_usage(client_id)
    if usage < _TIER_PREMIUM_LIMIT:
        remaining = _TIER_PREMIUM_LIMIT - usage
        return MODEL_PREMIUM, settings.openrouter_api_key, f"premium ({remaining} restantes)"
    elif usage < _TIER_FREE_LIMIT:
        remaining = _TIER_FREE_LIMIT - usage
        return MODEL_FREE, settings.openrouter_api_key, f"gratuito ({remaining} restantes)"
    else:
        return MODEL_FREE, settings.openrouter_api_key, "limite_atingido"


def _get_conversation(client_id: str) -> list[dict[str, str]]:
    now = time.time()
    if client_id in _conversation_ts and (now - _conversation_ts[client_id]) > _TTL_SECONDS:
        _conversations[client_id] = []
    _conversation_ts[client_id] = now
    return _conversations[client_id]


def _trim_conversation(history: list[dict[str, str]]) -> None:
    while len(history) > _MAX_HISTORY:
        history.pop(0)


# --- Models ---

class ChatMessage(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    conversation_id: str = Field(default="", max_length=64)


class EntityCard(BaseModel):
    id: str
    type: str
    name: str
    properties: dict[str, Any] = {}
    connections: int = 0
    sources: list[str] = []


class EvidenceItem(BaseModel):
    tool: str
    source: str
    query: str
    result_count: int = 0
    timestamp: str = ""
    api_url: str = ""

class ChatResponse(BaseModel):
    reply: str
    entities: list[EntityCard] = []
    suggestions: list[str] = []
    evidence_chain: list[EvidenceItem] = []
    cost_usd: float = 0.0


# --- Neo4j tool functions ---

def _build_search_query(raw: str) -> str:
    raw = raw.strip()
    if any(c in raw for c in ['"', "*", "~", "AND", "OR"]):
        return raw
    escaped = _LUCENE_SPECIAL.sub(r"\\\1", raw)
    terms = escaped.split()
    parts: list[str] = []
    for term in terms:
        if len(term) >= 2:
            parts.append(f"{term}*")
            parts.append(f"{term}~0.8")
        else:
            parts.append(term)
    return " ".join(parts)


def _extract_name(node: Any, labels: list[str]) -> str:
    props = dict(node)
    etype = labels[0].lower() if labels else ""
    if etype == "company":
        return str(props.get("razao_social", props.get("name", props.get("nome_fantasia", ""))))
    if etype in ("contract", "amendment", "convenio"):
        return str(props.get("object", props.get("function", props.get("name", ""))))
    if etype == "embargo":
        return str(props.get("infraction", props.get("name", "")))
    if etype == "publicoffice":
        return str(props.get("org", props.get("name", "")))
    return str(props.get("name", ""))


def _format_type_pt(etype: str) -> str:
    labels = {
        "company": "Empresa", "person": "Pessoa", "contract": "Contrato",
        "sanction": "Sanção", "publicoffice": "Cargo Público", "embargo": "Embargo",
        "convenio": "Convênio", "election": "Eleição", "finance": "Financeiro",
        "partner": "Sócio",
    }
    return labels.get(etype, etype.capitalize())


async def _tool_search(session: AsyncSession, query: str, entity_type: str | None = None, limit: int = 8) -> list[EntityCard]:
    cnpj_match = _CNPJ_RE.search(query)
    if cnpj_match:
        cnpj_clean = re.sub(r"[.\-/]", "", cnpj_match.group())
        search_query = f'"{cnpj_clean}"'
    else:
        search_query = _build_search_query(query)

    records = await execute_query(
        session, "search",
        {"query": search_query, "entity_type": entity_type, "skip": 0, "limit": limit},
    )

    entities: list[EntityCard] = []
    for record in records:
        node = record["node"]
        props = dict(node)
        labels = record["node_labels"]

        if should_hide_person_entities() and has_person_labels(labels):
            continue

        source_val = props.pop("source", None)
        sources: list[str] = []
        if isinstance(source_val, str):
            sources = [source_val]
        elif isinstance(source_val, list):
            sources = [str(s) for s in source_val]

        etype = labels[0].lower() if labels else "unknown"
        clean_props = sanitize_public_properties(sanitize_props(props))

        entities.append(EntityCard(
            id=record["node_id"],
            type=etype,
            name=_extract_name(node, labels),
            properties=clean_props,
            connections=0,
            sources=sources,
        ))
    return entities


async def _tool_stats(session: AsyncSession) -> dict[str, Any]:
    try:
        records = await execute_query(session, "stats", {})
        if records:
            return dict(records[0])
    except Exception as e:
        logger.error("_tool_stats failed: %s", e)
    return {"error": "Não foi possível obter estatísticas"}


async def _tool_cypher(session: AsyncSession, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Execute a safe read-only Cypher query. Only MATCH/RETURN/WITH/UNWIND/CALL allowed."""
    q = query.strip().upper()
    forbidden = ["CREATE", "DELETE", "MERGE", "SET ", "REMOVE", "DROP", "DETACH"]
    for kw in forbidden:
        if kw in q:
            return [{"error": f"Query contains forbidden keyword: {kw.strip()}"}]
    try:
        result = await session.run(query, params or {})
        rows = []
        async for record in result:
            rows.append({k: _serialize_neo4j(record[k]) for k in record.keys()})
            if len(rows) >= 50:
                break
        return rows if rows else [{"message": "Query retornou 0 resultados"}]
    except Exception as e:
        logger.warning("Cypher query failed: %s — query: %s", e, query[:200])
        return [{"error": str(e)[:300]}]


def _serialize_neo4j(val: Any) -> Any:
    """Convert Neo4j types to JSON-serializable values."""
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, list):
        return [_serialize_neo4j(v) for v in val]
    if isinstance(val, dict):
        return {k: _serialize_neo4j(v) for k, v in val.items()}
    if hasattr(val, 'items'):
        return {k: _serialize_neo4j(v) for k, v in val.items()}
    if hasattr(val, '__iter__'):
        return [_serialize_neo4j(v) for v in val]
    return str(val)


async def _tool_data_summary(session: AsyncSession) -> dict[str, Any]:
    """Dynamic data summary — replaces hardcoded stats in system prompt."""
    summary: dict[str, Any] = {"tools_count": len(TOOLS)}
    try:
        stats = await _tool_stats(session)
        if "error" not in stats:
            summary["total_nodes"] = stats.get("total_nodes", 0)
            summary["total_relationships"] = stats.get("total_relationships", 0)
            summary["data_sources"] = stats.get("data_sources", 0)
            summary["implemented_sources"] = stats.get("implemented_sources", 0)
            summary["loaded_sources"] = stats.get("loaded_sources", 0)
            summary["top_types"] = {
                k: v for k, v in stats.items()
                if k.endswith("_count") and isinstance(v, int) and v > 0 and k != "ingestion_run_count"
            }
    except Exception as e:
        summary["error"] = str(e)[:200]
    return summary


async def _tool_connections(session: AsyncSession, entity_id: str) -> list[dict[str, str]]:
    try:
        cypher = """
        MATCH (n)-[r]-(m)
        WHERE elementId(n) = $entity_id
        RETURN type(r) AS rel_type, labels(m) AS labels, 
               coalesce(m.razao_social, m.name, m.nome_fantasia, '') AS name
        LIMIT 15
        """
        result = await session.run(cypher, {"entity_id": entity_id})
        connections = []
        async for record in result:
            connections.append({
                "relationship": record["rel_type"],
                "type": record["labels"][0] if record["labels"] else "Unknown",
                "name": record["name"],
            })
        return connections
    except Exception as e:
        logger.warning("Connection lookup failed: %s", e)
        return []


# --- Tool definitions for OpenRouter function calling ---

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_entities",
            "description": "Pesquisa entidades no grafo Neo4j por nome, CNPJ, ou termo. Retorna empresas, sanções, contratos, embargos, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termo de busca: nome de empresa, CNPJ, ou palavra-chave"},
                    "entity_type": {"type": "string", "description": "Filtro opcional: company, sanction, contract, embargo, person, election, finance", "enum": ["company", "sanction", "contract", "embargo", "person", "election", "finance", "convenio", "publicoffice"]},
                    "limit": {"type": "integer", "description": "Máximo de resultados (1-20)", "default": 8},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_graph_stats",
            "description": "Retorna estatísticas gerais do grafo: total de nós, relacionamentos, contagem por tipo de entidade.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_entity_connections",
            "description": "Busca conexões/relacionamentos de uma entidade específica no grafo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": "ID da entidade (elementId do Neo4j)"},
                },
                "required": ["entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Pesquisa na web por noticias, investigacoes, denuncias, materias de jornais sobre empresas, politicos, cidades. Use para encontrar informacoes atuais que nao estao no grafo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termo de busca (ex: 'investigacao prefeito Uberlandia', 'denuncia empresa X CNPJ')"},
                    "max_results": {"type": "integer", "description": "Maximo de resultados (1-10)", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_emendas",
            "description": "Busca emendas parlamentares direcionadas a um municipio. Mostra quanto dinheiro federal foi destinado via emendas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "municipio": {"type": "string", "description": "Nome do municipio (ex: Uberlandia, Sao Paulo, Patos de Minas)"},
                    "uf": {"type": "string", "description": "Sigla do estado (ex: MG, SP, RJ)"},
                    "ano": {"type": "integer", "description": "Ano de referencia", "default": 2024},
                },
                "required": ["municipio"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_transferencias",
            "description": "Busca transferencias federais (convenios, repasses) para um municipio. Mostra o fluxo de dinheiro federal para a cidade.",
            "parameters": {
                "type": "object",
                "properties": {
                    "municipio": {"type": "string", "description": "Nome do municipio"},
                    "uf": {"type": "string", "description": "Sigla do estado"},
                    "ano": {"type": "integer", "description": "Ano de referencia", "default": 2024},
                },
                "required": ["municipio"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_ceap",
            "description": "Busca gastos CEAP (Cota para Exercicio da Atividade Parlamentar) de deputados. Mostra despesas com passagens, combustivel, alimentacao, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "parlamentar": {"type": "string", "description": "Nome do parlamentar (ex: 'Joao Silva')"},
                    "uf": {"type": "string", "description": "Sigla do estado para filtrar deputados"},
                    "ano": {"type": "integer", "description": "Ano de referencia", "default": 2024},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_pep_city",
            "description": "Busca pessoas politicamente expostas (PEPs) de uma cidade: deputados, prefeito, vereadores, investigados. Retorna deputados federais do estado e noticias sobre politicos locais.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cidade": {"type": "string", "description": "Nome da cidade (ex: Uberlandia, Patos de Minas)"},
                    "uf": {"type": "string", "description": "Sigla do estado (ex: MG, SP)"},
                },
                "required": ["cidade"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_gazettes",
            "description": "Busca em diarios oficiais municipais via Querido Diario (Open Knowledge Brasil). Encontra licitacoes, contratos, nomeacoes, decretos publicados no diario oficial da cidade.",
            "parameters": {
                "type": "object",
                "properties": {
                    "municipio": {"type": "string", "description": "Nome do municipio (ex: Uberlandia, Sao Paulo)"},
                    "query": {"type": "string", "description": "Termo de busca no diario oficial (ex: 'licitacao', 'contrato', nome de empresa)"},
                    "max_results": {"type": "integer", "description": "Maximo de resultados (1-10)", "default": 5},
                },
                "required": ["municipio"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cnpj_info",
            "description": "Busca informacoes de empresa por CNPJ: razao social, socios, capital social, CNAE, situacao cadastral. Use para investigar fornecedores encontrados no CEAP ou em contratos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cnpj": {"type": "string", "description": "CNPJ da empresa (com ou sem formatacao, ex: 12.345.678/0001-90 ou 12345678000190)"},
                },
                "required": ["cnpj"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_votacoes",
            "description": "Busca votacoes nominais na Camara dos Deputados. Mostra como cada deputado votou em proposicoes. Sem nome de parlamentar, lista votacoes recentes com placar (sim/nao/abstencao).",
            "parameters": {
                "type": "object",
                "properties": {
                    "parlamentar": {"type": "string", "description": "Nome do deputado para ver como votou (opcional)"},
                    "proposicao": {"type": "string", "description": "Tema ou numero da proposicao (opcional)"},
                    "ano": {"type": "integer", "description": "Ano de referencia", "default": 2024},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_servidores",
            "description": "Busca servidores publicos federais: nome, salario, cargo, orgao. Portal da Transparencia oficial.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome do servidor"},
                    "cpf": {"type": "string", "description": "CPF do servidor (opcional)"},
                    "orgao": {"type": "string", "description": "Orgao de exercicio (opcional)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_licitacoes",
            "description": "Busca licitacoes do governo federal: pregoes, concorrencias, dispensas. Filtro por UF e ano.",
            "parameters": {
                "type": "object",
                "properties": {
                    "orgao": {"type": "string", "description": "Codigo do orgao (opcional)"},
                    "uf": {"type": "string", "description": "UF (ex: SP, MG, RJ)"},
                    "modalidade": {"type": "string", "description": "Modalidade da licitacao (ex: Pregao, Concorrencia, Dispensa)"},
                    "ano": {"type": "integer", "description": "Ano de referencia", "default": 2024},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_cpgf",
            "description": "Busca gastos com cartao corporativo do governo (CPGF). Restaurantes, hoteis, compras. Investigue gastos suspeitos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome do portador do cartao"},
                    "orgao": {"type": "string", "description": "Codigo do orgao"},
                    "mes": {"type": "integer", "description": "Mes (1-12)"},
                    "ano": {"type": "integer", "description": "Ano", "default": 2024},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_viagens",
            "description": "Busca viagens a servico do governo: diarias, passagens, destinos. Investigue viagens frequentes ou caras.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome do servidor que viajou"},
                    "orgao": {"type": "string", "description": "Codigo do orgao"},
                    "ano": {"type": "integer", "description": "Ano", "default": 2024},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_contratos",
            "description": "Busca contratos do governo federal: fornecedor, valor, vigencia. Investigue aditivos e sobrepreco.",
            "parameters": {
                "type": "object",
                "properties": {
                    "orgao": {"type": "string", "description": "Codigo do orgao"},
                    "fornecedor": {"type": "string", "description": "Nome do fornecedor"},
                    "ano": {"type": "integer", "description": "Ano", "default": 2024},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_sancoes",
            "description": "Busca empresas sancionadas (CEIS - inidoneas, CNEP - punidas). Empresa sancionada ganhando contrato = irregularidade.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cnpj": {"type": "string", "description": "CNPJ da empresa"},
                    "nome": {"type": "string", "description": "Nome da empresa"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_processos",
            "description": "Busca processos judiciais no DataJud (CNJ). Todos os tribunais do Brasil. Busque por numero, classe (recuperacao judicial, improbidade) ou recentes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "numero_processo": {"type": "string", "description": "Numero do processo (formato CNJ)"},
                    "nome_parte": {"type": "string", "description": "Nome de uma das partes (limitado)"},
                    "tribunal": {"type": "string", "description": "Tribunal: TJSP, TJRJ, TJMG, TRF1-6, STJ, TST, etc.", "default": "TJSP"},
                    "classe": {"type": "string", "description": "Classe processual: Recuperacao Judicial, Acao de Improbidade, Execucao Fiscal, etc."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bnmp_mandados",
            "description": "Busca mandados de prisao no BNMP (Banco Nacional de Mandados de Prisao - CNJ). Verifica se pessoa tem mandado ativo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome completo da pessoa"},
                },
                "required": ["nome"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "procurados_lookup",
            "description": "Busca pessoas procuradas pela Policia Federal e Interpol Brasil.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome da pessoa procurada"},
                },
                "required": ["nome"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lista_suja_lookup",
            "description": "Consulta a Lista Suja do Trabalho Escravo (MTE). Verifica se empresa ou empregador foi flagrado com trabalho analogo a escravidao.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome do empregador ou empresa"},
                    "uf": {"type": "string", "description": "Sigla do estado (opcional)"},
                },
                "required": ["nome"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pncp_licitacoes",
            "description": "Busca licitacoes no PNCP (Portal Nacional de Contratacoes Publicas). Inclui TODAS as esferas: federal, estadual e municipal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cnpj_orgao": {"type": "string", "description": "CNPJ do orgao contratante"},
                    "uf": {"type": "string", "description": "Sigla do estado (ex: SP, MG)"},
                    "data_inicio": {"type": "string", "description": "Data inicio (YYYYMMDD)", "default": "20240101"},
                    "data_fim": {"type": "string", "description": "Data fim (YYYYMMDD)", "default": "20241231"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "oab_advogado",
            "description": "Consulta advogado pelo numero OAB ou nome. Verifica se inscricao esta ativa, seccional, situacao.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome do advogado"},
                    "numero_oab": {"type": "string", "description": "Numero de inscricao OAB"},
                    "seccional": {"type": "string", "description": "Seccional OAB (ex: SP, RJ, MG)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "opencnpj",
            "description": "Consulta CNPJ via OpenCNPJ (API publica gratuita). Retorna dados cadastrais completos: razao social, socios (QSA), CNAEs, capital social, situacao cadastral. Use como alternativa/complemento a cnpj_info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cnpj": {"type": "string", "description": "CNPJ da empresa (com ou sem formatacao)"},
                },
                "required": ["cnpj"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cypher_query",
            "description": "Executa query Cypher READ-ONLY no Neo4j. Use para consultas analiticas que os outros tools nao cobrem: top N por criterio, contagens, agregacoes, cruzamentos. Labels disponiveis: Company, Person, Sanction, Contract, PublicOffice, Embargo, Election, Amendment, Convenio, PEPRecord, GovCardExpense, GovTravel, BarredNGO. Propriedades comuns: name, razao_social, cnpj, cpf, source, value, date. Relacionamentos: SOCIO_DE, CONTRATADA_POR, SANCIONADA_POR, RECEBEU_EMENDA, VIAJOU_PARA. SEMPRE use LIMIT (max 50).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query Cypher read-only (MATCH/RETURN apenas). Ex: MATCH (c:Company)-[:SOCIO_DE]-(p:Person) RETURN c.razao_social, p.name LIMIT 10"},
                    "params": {"type": "object", "description": "Parametros opcionais para a query ($nome, $cnpj, etc.)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "data_summary",
            "description": "Retorna resumo dinamico do sistema: total de nos, relacionamentos, fontes de dados, tipos de entidades com contagem, numero de ferramentas. Use para responder perguntas sobre o que o sistema tem/sabe.",
            "parameters": {"type": "object", "properties": {}},
        },
    },

]

SYSTEM_PROMPT = """Você é o agente de pesquisa do EGOS Inteligência (inteligencia.egos.ia.br).

## Identidade
Agente de pesquisa em dados públicos brasileiros. Open-source, autofinanciado, 26 ferramentas integradas.
Acesso DIRETO ao grafo Neo4j, APIs de transparência, diários oficiais, processos judiciais, mandados, sanções, CNPJ.

## REGRA #1: SEMPRE USE FERRAMENTAS — NUNCA RESPONDA DE MEMÓRIA
Você DEVE chamar ferramentas ANTES de responder. Se o usuário pergunta QUALQUER coisa sobre dados, chame a ferramenta.
- Perguntas sobre o sistema → chame data_summary
- Perguntas sobre empresas → chame search_entities + opencnpj + search_sancoes
- Perguntas analíticas → chame cypher_query (contagens, rankings, cruzamentos)
- NUNCA diga "temos X mil entidades" sem chamar data_summary primeiro
- NUNCA invente números — busque sempre dados reais
- Ao listar DEPUTADOS/POLÍTICOS: SEMPRE mostre dados de mandato quando disponíveis: legislatura atual, total de mandatos (1o, 2o, 3o mandato etc.), período do mandato (data início/fim), condição eleitoral. Exemplo: "Benes Leocádio (UNIÃO) - 2o mandato (2019-2027)"

## REGRA #2: USE MÚLTIPLAS FERRAMENTAS EM PARALELO
Chame 2-4 ferramentas simultaneamente. Quanto mais cruzamento, melhor a pesquisa.
- CIDADE: search_pep_city + search_emendas + search_transferencias + search_gazettes
- POLÍTICO: search_ceap + search_entities + web_search + search_votacoes
- EMPRESA/CNPJ: opencnpj + search_entities + search_sancoes + lista_suja_lookup
- DINHEIRO: search_emendas + search_transferencias + search_ceap + pncp_licitacoes
- PESSOA SUSPEITA: bnmp_mandados + procurados_lookup + search_entities + web_search
- ANÁLISE DO GRAFO: cypher_query (top N, contagens, agregações, cruzamentos)

## cypher_query — Seu Superpoder
Use para consultas analíticas que outros tools não cobrem:
- Top empresas com mais sanções: MATCH (s:Sanction)--(c:Company) RETURN c.razao_social, count(s) AS total ORDER BY total DESC LIMIT 10
- Sócios de empresa: MATCH (c:Company)-[:SOCIO_DE]-(p:Person) WHERE c.cnpj = $cnpj RETURN p.name, c.razao_social
- Empresas conectadas a político: MATCH (p:Person {name: $nome})-[*1..2]-(c:Company) RETURN DISTINCT c.razao_social, c.cnpj LIMIT 20
- Contagem por tipo: MATCH (n) RETURN labels(n)[0] AS tipo, count(n) AS total ORDER BY total DESC
- Labels: Company, Person, Sanction, Contract, PublicOffice, Embargo, PEPRecord, GovCardExpense, GovTravel, BarredNGO
- Rels: SOCIO_DE, CONTRATADA_POR, SANCIONADA_POR, RECEBEU_EMENDA, VIAJOU_PARA
- SEMPRE use LIMIT (max 50)

## Regras de Resposta
- Português brasileiro SEMPRE
- Responda de forma completa mas concisa (max ~1500 chars)
- Use **negrito** para nomes, valores, CNPJs
- Cite a fonte de cada dado (CEIS, CNEP, Câmara, DataJud, etc.)
- NUNCA exponha CPF ou dados pessoais sensíveis
- Padrões são SINAIS, nunca prova jurídica
- Sugira próximos passos de pesquisa ao final
- Mostre o CAMINHO DO DINHEIRO: emenda → convênio → empresa → sócios
- Se não encontrar resultados, sugira variações de busca
- NUNCA peça informação que você pode buscar sozinho — PESQUISE PRIMEIRO
- Se a pergunta é genérica, busque dados NACIONAIS primeiro

## Análise de Risco
1. **RISCO:** Sanções? Processos? Conexões suspeitas?
2. **MODUS OPERANDI:** Padrão repetido? Mesmos sócios em várias empresas?
3. **CROSS-REFERENCE:** Cruzar grafo + Portal + DataJud + Querido Diário + web
4. **RED FLAGS:** Empresa sancionada com contrato ativo, sócio em falida + nova, fornecedor em RJ, doação + contrato

## Relatórios Publicados
1. **SUPERAR LTDA** — RJ + contratos públicos + fraude patrimonial → /reports/report-01-superar-ltda.md
2. **Manaus Transparência** — Emendas, convênios, licitações → /reports/report-02-manaus-transparencia.md
3. **Recuperação Judicial SP** — Empresas em RJ com contratos → /reports/report-03-recuperacao-judicial-sp.md
4. **Patense** — Pesquisa completa → /reports/patense.html

## Limitações (seja honesto)
- CNPJ/QSA: parcial (ETL em progresso — 53M empresas)
- ICIJ Offshore Leaks: não disponível ainda
- Doações de campanha TSE: próximo ETL

## Disclaimer
Pesquisa cidadã com dados públicos. Padrões são sinais para aprofundar, não prova jurídica."""


async def _call_openrouter(
    messages: list[dict[str, Any]],
    session: AsyncSession,
    model: str = "",
    api_key: str = "",
) -> tuple[str, list[EntityCard], list[dict[str, Any]], float]:
    """Call OpenRouter with tool-calling loop. Returns (reply_text, entities, evidence, cost)."""

    all_entities: list[EntityCard] = []
    evidence_chain: list[dict[str, Any]] = []
    total_cost: float = 0.0

    effective_key = api_key or settings.openrouter_api_key
    effective_model = model or settings.ai_model

    if not effective_key:
        text, ents = await _fallback_search(messages[-1].get("content", ""), session)
        return text, ents, [], 0.0

    headers = {
        "Authorization": f"Bearer {effective_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://inteligencia.egos.ia.br",
        "X-Title": "EGOS Inteligencia",
    }

    payload = {
        "model": effective_model,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "max_tokens": 2000,
        "temperature": 0.3,
    }

    max_rounds = 8
    async with httpx.AsyncClient(timeout=45.0) as client:
        for _ in range(max_rounds):
            try:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error("OpenRouter call failed: %s", e)
                text, ents = await _fallback_search(messages[-1].get("content", ""), session)
                return text, ents, [], 0.0

            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})

            # Track token cost (~$0.15/1M input, $0.60/1M output for GPT-4o-mini)
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_cost += (prompt_tokens * 0.00000015) + (completion_tokens * 0.0000006)

            tool_calls = message.get("tool_calls")
            if not tool_calls:
                # Final text response
                return message.get("content", "Desculpe, não consegui processar sua pergunta."), all_entities, evidence_chain, total_cost

            # Process tool calls
            messages.append(message)
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    fn_args = {}

                result: Any = None
                if fn_name == "search_entities":
                    entities = await _tool_search(
                        session,
                        fn_args.get("query", ""),
                        fn_args.get("entity_type"),
                        min(fn_args.get("limit", 8), 20),
                    )
                    all_entities.extend(entities)
                    result = [{"id": e.id, "type": e.type, "name": e.name, "sources": e.sources, "properties": {k: v for k, v in list(e.properties.items())[:5]}} for e in entities]
                elif fn_name == "get_graph_stats":
                    result = await _tool_stats(session)
                elif fn_name == "get_entity_connections":
                    result = await _tool_connections(session, fn_args.get("entity_id", ""))
                elif fn_name == "web_search":
                    result = await tool_web_search(
                        fn_args.get("query", ""),
                        min(fn_args.get("max_results", 5), 10),
                    )
                elif fn_name == "search_emendas":
                    result = await tool_search_emendas(
                        fn_args.get("municipio", ""),
                        fn_args.get("uf", ""),
                        fn_args.get("ano", 2024),
                    )
                elif fn_name == "search_transferencias":
                    result = await tool_search_transferencias(
                        fn_args.get("municipio", ""),
                        fn_args.get("uf", ""),
                        fn_args.get("ano", 2024),
                    )
                elif fn_name == "search_ceap":
                    result = await tool_search_ceap(
                        fn_args.get("parlamentar", ""),
                        fn_args.get("uf", ""),
                        fn_args.get("ano", 2024),
                    )
                elif fn_name == "search_pep_city":
                    result = await tool_search_pep_city(
                        fn_args.get("cidade", ""),
                        fn_args.get("uf", ""),
                    )
                elif fn_name == "search_gazettes":
                    result = await tool_search_gazettes(
                        fn_args.get("municipio", ""),
                        fn_args.get("query", ""),
                        min(fn_args.get("max_results", 5), 10),
                    )
                elif fn_name == "cnpj_info":
                    result = await tool_cnpj_info(fn_args.get("cnpj", ""))
                elif fn_name == "search_votacoes":
                    result = await tool_search_votacoes(
                        fn_args.get("parlamentar", ""),
                        fn_args.get("proposicao", ""),
                        fn_args.get("ano", 2024),
                    )
                elif fn_name == "search_servidores":
                    result = await tool_search_servidores(
                        fn_args.get("nome", ""),
                        fn_args.get("cpf", ""),
                        fn_args.get("orgao", ""),
                    )
                elif fn_name == "search_licitacoes":
                    result = await tool_search_licitacoes(
                        fn_args.get("orgao", ""),
                        fn_args.get("uf", ""),
                        fn_args.get("modalidade", ""),
                        fn_args.get("ano", 2024),
                    )
                elif fn_name == "search_cpgf":
                    result = await tool_search_cpgf(
                        fn_args.get("nome", ""),
                        fn_args.get("orgao", ""),
                        fn_args.get("mes", 0),
                        fn_args.get("ano", 2024),
                    )
                elif fn_name == "search_viagens":
                    result = await tool_search_viagens(
                        fn_args.get("nome", ""),
                        fn_args.get("orgao", ""),
                        fn_args.get("ano", 2024),
                    )
                elif fn_name == "search_contratos":
                    result = await tool_search_contratos(
                        fn_args.get("orgao", ""),
                        fn_args.get("fornecedor", ""),
                        fn_args.get("ano", 2024),
                    )
                elif fn_name == "search_sancoes":
                    result = await tool_search_sancoes(
                        fn_args.get("cnpj", ""),
                        fn_args.get("nome", ""),
                    )
                elif fn_name == "search_processos":
                    result = await tool_search_processos(
                        fn_args.get("numero_processo", ""),
                        fn_args.get("nome_parte", ""),
                        fn_args.get("tribunal", "TJSP"),
                        fn_args.get("classe", ""),
                    )
                elif fn_name == "bnmp_mandados":
                    result = await tool_bnmp_mandados(fn_args.get("nome", ""))
                elif fn_name == "procurados_lookup":
                    result = await tool_procurados_lookup(fn_args.get("nome", ""))
                elif fn_name == "lista_suja_lookup":
                    result = await tool_lista_suja(
                        fn_args.get("nome", ""),
                        fn_args.get("uf", ""),
                    )
                elif fn_name == "pncp_licitacoes":
                    result = await tool_pncp_licitacoes(
                        fn_args.get("cnpj_orgao", ""),
                        fn_args.get("uf", ""),
                        fn_args.get("data_inicio", "20240101"),
                        fn_args.get("data_fim", "20241231"),
                    )
                elif fn_name == "oab_advogado":
                    result = await tool_oab_advogado(
                        fn_args.get("nome", ""),
                        fn_args.get("numero_oab", ""),
                        fn_args.get("seccional", ""),
                    )
                elif fn_name == "opencnpj":
                    result = await tool_opencnpj(fn_args.get("cnpj", ""))
                elif fn_name == "cypher_query":
                    result = await _tool_cypher(session, fn_args.get("query", ""), fn_args.get("params"))
                elif fn_name == "data_summary":
                    result = await _tool_data_summary(session)
                else:
                    result = {"error": f"Tool {fn_name} not found"}

                # Track evidence chain
                source_info = {
                    "search_entities": ("Neo4j Graph", "neo4j://localhost:7687"),
                    "get_graph_stats": ("Neo4j Graph", "neo4j://localhost:7687"),
                    "get_entity_connections": ("Neo4j Graph", "neo4j://localhost:7687"),
                    "web_search": ("Brave Search / DuckDuckGo", "https://api.search.brave.com/"),
                    "search_emendas": ("Portal da Transparência — Emendas", "api.portaldatransparencia.gov.br"),
                    "search_transferencias": ("Portal da Transparência — Transferências", "api.portaldatransparencia.gov.br"),
                    "search_ceap": ("Câmara dos Deputados — CEAP", "dadosabertos.camara.leg.br"),
                    "search_pep_city": ("Câmara dos Deputados — PEP", "dadosabertos.camara.leg.br"),
                    "search_gazettes": ("Querido Diário (OKBR)", "queridodiario.ok.org.br"),
                    "cnpj_info": ("BrasilAPI — Receita Federal", "brasilapi.com.br"),
                    "search_votacoes": ("Câmara dos Deputados — Votações", "dadosabertos.camara.leg.br"),
                    "search_servidores": ("Portal da Transparência — Servidores", "api.portaldatransparencia.gov.br"),
                    "search_licitacoes": ("Portal da Transparência — Licitações", "api.portaldatransparencia.gov.br"),
                    "search_cpgf": ("Portal da Transparência — CPGF", "api.portaldatransparencia.gov.br"),
                    "search_viagens": ("Portal da Transparência — Viagens", "api.portaldatransparencia.gov.br"),
                    "search_contratos": ("Portal da Transparência — Contratos", "api.portaldatransparencia.gov.br"),
                    "search_sancoes": ("Portal da Transparência — CEIS/CNEP", "api.portaldatransparencia.gov.br"),
                    "search_processos": ("DataJud — CNJ", "api-publica.datajud.cnj.jus.br"),
                    "bnmp_mandados": ("BNMP — Mandados de Prisão (CNJ)", "portalbnmp.cnj.jus.br"),
                    "procurados_lookup": ("Polícia Federal — Procurados", "www.gov.br/pf"),
                    "lista_suja_lookup": ("MTE — Lista Suja Trabalho Escravo", "www.gov.br/trabalho-e-emprego"),
                    "pncp_licitacoes": ("PNCP — Licitações Nacionais", "pncp.gov.br"),
                    "oab_advogado": ("OAB — Cadastro de Advogados", "cna.oab.org.br"),
                    "opencnpj": ("OpenCNPJ — Receita Federal", "opencnpj.org"),
                    "cypher_query": ("Neo4j Graph — Cypher Query", "neo4j://localhost:7687"),
                    "data_summary": ("Sistema EGOS Inteligência", "inteligencia.egos.ia.br"),
                }.get(fn_name, ("Desconhecido", ""))
                
                result_count = 0
                if isinstance(result, list):
                    result_count = len(result)
                elif isinstance(result, dict):
                    for k in ("total", "count", "emendas", "transferencias", "deputados", "sancoes", "processos", "resultados", "results"):
                        v = result.get(k)
                        if isinstance(v, int):
                            result_count = v
                            break
                        elif isinstance(v, list):
                            result_count = len(v)
                            break
                
                from datetime import datetime
                evidence_chain.append({
                    "tool": fn_name,
                    "source": source_info[0],
                    "query": json.dumps(fn_args, ensure_ascii=False)[:200],
                    "result_count": result_count,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "api_url": source_info[1],
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False, default=str)[:8000],
                })

            payload["messages"] = messages

    return "Desculpe, atingi o limite de processamento. Tente uma pergunta mais específica.", all_entities, evidence_chain, total_cost


async def _fallback_search(user_msg: str, session: AsyncSession) -> tuple[str, list[EntityCard]]:
    """Fallback when no OpenRouter key: direct Neo4j search."""
    cnpj_match = _CNPJ_RE.search(user_msg)
    if cnpj_match:
        term = cnpj_match.group()
    else:
        cleaned = re.sub(
            r"\b(quem|qual|quais|onde|como|sobre|me|fale|busque|pesquise|procure|"
            r"encontre|mostre|o que|é|são|do|da|de|dos|das|no|na|nos|nas|"
            r"um|uma|uns|umas|para|por|com|em|a|e|ou|os|as|ao|à|"
            r"tem|ter|foi|ser|está|estão|pode|podem)\b",
            "", user_msg.lower(),
        )
        term = re.sub(r"\s+", " ", cleaned).strip()

    if len(term) < 2:
        return (
            "Olá! Sou o agente de inteligência do **EGOS**.\n\nDigite um CNPJ, nome de empresa, ou pergunte sobre dados públicos brasileiros.",
            [],
        )

    entities = await _tool_search(session, term)

    if not entities:
        return f'Não encontrei resultados para **"{term}"**.\n\nTente verificar a ortografia ou usar o CNPJ completo.', []
    elif len(entities) == 1:
        e = entities[0]
        reply = f"Encontrei **{_format_type_pt(e.type)}**: **{e.name}**"
        if e.sources:
            reply += f"\nFonte: {', '.join(e.sources)}"
        return reply, entities
    else:
        reply = f"Encontrei **{len(entities)} resultados** para \"{term}\":\n\n"
        for i, e in enumerate(entities, 1):
            reply += f"{i}. **{e.name}** ({_format_type_pt(e.type)})\n"
        return reply, entities


def _generate_suggestions(reply: str, entities: list[EntityCard], user_msg: str) -> list[str]:
    """Generate contextual investigative follow-up suggestions."""
    suggestions: list[str] = []
    msg_lower = user_msg.lower()
    reply_lower = reply.lower()

    # City-related suggestions
    _BR_CITIES = ["uberlandia", "sao paulo", "rio de janeiro", "belo horizonte", "brasilia",
                  "curitiba", "salvador", "fortaleza", "recife", "porto alegre", "goiania",
                  "manaus", "campinas", "patos de minas", "uberaba", "juiz de fora"]
    detected_city = None
    for city in _BR_CITIES:
        if city in msg_lower or city in reply_lower:
            detected_city = city.title()
            break

    if detected_city:
        suggestions.append(f"Emendas para {detected_city}")
        suggestions.append(f"Deputados de {detected_city}")
        suggestions.append(f"Transferencias federais {detected_city}")

    # Entity-based suggestions
    if entities:
        first = entities[0]
        if first.type == "company":
            suggestions.append(f"Conexoes de {first.name[:25]}")
            suggestions.append(f"Sancoes contra {first.name[:25]}")
        elif first.type == "person":
            suggestions.append(f"Gastos CEAP de {first.name[:25]}")
        elif first.type == "sanction":
            suggestions.append("Buscar empresa sancionada no grafo")

    # CEAP/transparency suggestions
    if "ceap" in reply_lower or "deputad" in reply_lower:
        suggestions.append("Fornecedores desse deputado")
        suggestions.append("Gastos com passagens aereas")

    # If no context-specific suggestions, use investigative defaults
    if not suggestions:
        import random
        _INVESTIGATION_SUGGESTIONS = [
            "Digite o nome da sua cidade",
            "Gastos CEAP deputados SP",
            "Emendas parlamentares 2024",
            "Buscar empresa por CNPJ",
            "Votacoes recentes na Camara",
            "Recuperacao judicial empresas",
            "Investigacoes Ministerio Publico",
            "Diario oficial licitacoes",
            "Supersalarios servidores publicos",
            "Fornecedores de politicos",
        ]
        suggestions = random.sample(_INVESTIGATION_SUGGESTIONS, min(4, len(_INVESTIGATION_SUGGESTIONS)))

    return suggestions[:4]


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(
    request: Request,
    body: ChatMessage,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChatResponse:
    """AI-powered conversational search for EGOS Inteligência."""

    client_id = _get_client_id(request)
    
    # Conversation persistence: use Redis if conversation_id provided
    conv_id = body.conversation_id.strip() if body.conversation_id else ""
    client_header = (request.headers.get("x-client-id") or "").strip()
    effective_client = client_header if client_header else client_id
    
    if conv_id:
        from bracc.routers.conversations import get_conversation_messages
        history = await get_conversation_messages(conv_id, effective_client)
    else:
        history = _get_conversation(client_id)

    # BYOK: user can pass own OpenRouter key via header
    byok_key = (request.headers.get("x-openrouter-key") or "").strip()

    # Select model based on usage tier or BYOK
    selected_model, selected_key, tier_label = _select_model(client_id, byok_key)

    # Rate limit check — if limit reached, prepend warning
    tier_notice = ""
    if tier_label == "limite_atingido":
        tier_notice = "\n\n⚠️ **Limite diário atingido** (30 consultas). O agente continua funcionando com modelo gratuito, mas a qualidade pode ser menor.\n\n💡 **Traga sua própria chave!** Crie uma conta grátis em [openrouter.ai](https://openrouter.ai), insira créditos (~$5 dura meses) e cole sua chave nas configurações. Assim você usa os melhores modelos sem restrição."

    # Build messages for LLM
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history (last N messages for context)
    for msg in history[-10:]:
        messages.append(msg)

    # Enrich vague queries with actionable hints for the LLM
    enriched_msg = body.message
    msg_lower = body.message.lower().strip()
    _QUERY_HINTS: list[tuple[list[str], str]] = [
        (["estatistic", "quantos dados", "quantas entidade", "o que voce sabe", "o que você sabe", "quais dados", "quais fontes", "resumo do sistema"],
         "Chame data_summary E cypher_query com 'MATCH (n) RETURN labels(n)[0] AS tipo, count(n) AS total ORDER BY total DESC LIMIT 15'. Mostre os números reais."),
        (["relatorio", "relatório", "report", "exemplos de investigacao"],
         "Liste os 4 relatórios publicados com links: SUPERAR, Manaus, RJ SP, Patense. Ofereça para investigar algo novo."),
        (["emendas parlamentar", "emendas 2024"],
         "Chame search_emendas para SP em 2024 E search_transferencias para SP em 2024. Mostre maiores valores."),
        (["supersalario", "supersalário", "maiores salario"],
         "Chame search_servidores sem filtro (mostra maiores salários) E cypher_query com 'MATCH (p:PEPRecord) RETURN p.name, p.source LIMIT 10'."),
        (["licitacoes suspeita", "licitações suspeita", "dispensa de licitacao"],
         "Chame search_licitacoes para SP 2024 E pncp_licitacoes para SP. Analise dispensas."),
        (["diario oficial", "diário oficial"],
         "Chame search_gazettes para a cidade mencionada (ou São Paulo) com query 'licitação'."),
        (["votacoes recentes", "votações recentes", "como votou"],
         "Chame search_votacoes para 2024. Mostre votações recentes com placar."),
        (["empresas sancionada", "lista suja", "ceis", "cnep"],
         "Chame cypher_query com 'MATCH (s:Sanction) RETURN s.name, s.source, s.value LIMIT 15' E search_sancoes."),
        (["o que voce pode", "o que você pode", "ajuda", "help", "como funciona", "o que faz"],
         "Chame data_summary. Depois explique: 26 ferramentas, acesso a Neo4j, Portal da Transparência, DataJud, BNMP, diários oficiais, CNPJ, mandados, sanções. Sugira investigações."),
    ]
    for triggers, hint in _QUERY_HINTS:
        if any(t in msg_lower for t in triggers):
            enriched_msg = f"{body.message}\n\n[SISTEMA: {hint}]"
            break

    messages.append({"role": "user", "content": enriched_msg})

    try:
        reply, entities, evidence, cost = await _call_openrouter(
            messages, session, model=selected_model, api_key=selected_key
        )
    except Exception as e:
        logger.error("Chat failed: %s", e)
        reply, entities = await _fallback_search(body.message, session)
        evidence, cost = [], 0.0

    # Increment usage AFTER successful call
    new_count = _increment_usage(client_id)

    # Append tier notice to reply
    if tier_notice:
        reply += tier_notice
    elif new_count == _TIER_PREMIUM_LIMIT:
        reply += f"\n\n💡 Você usou suas {_TIER_PREMIUM_LIMIT} consultas premium do dia. Próximas consultas usarão o modelo gratuito (Gemini Flash). Para manter a qualidade, traga sua chave OpenRouter."
    elif new_count == _TIER_FREE_LIMIT:
        reply += "\n\n⚠️ Limite diário atingido. Crie uma conta grátis em [openrouter.ai](https://openrouter.ai) e insira sua chave para continuar sem limites."

    # Save to conversation memory
    if conv_id:
        from bracc.routers.conversations import save_conversation_messages
        await save_conversation_messages(
            conv_id, effective_client, body.message, reply, auto_title=True
        )
    else:
        history.append({"role": "user", "content": body.message})
        history.append({"role": "assistant", "content": reply})
        _trim_conversation(history)

    suggestions = _generate_suggestions(reply, entities, body.message)

    # Log activity with tier info
    log_activity(
        activity_type="chat",
        title=body.message[:80],
        description=f"{len(entities)} entities, {len(evidence)} sources, model={selected_model.split('/')[-1]}, tier={tier_label}",
        source="chatbot",
        result_count=len(entities),
        cost_usd=round(cost, 6),
        client_ip=client_id,
    )

    return ChatResponse(
        reply=reply,
        entities=entities,
        suggestions=suggestions,
        evidence_chain=[EvidenceItem(**e) for e in evidence],
        cost_usd=round(cost, 6),
    )
