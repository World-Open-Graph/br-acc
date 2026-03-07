"""Format API responses into human-readable Telegram messages."""

from __future__ import annotations

import contextlib
import re
from typing import Any

# Telegram message length limit
_MAX_MESSAGE_LENGTH = 4096


def format_cnpj(digits: str) -> str:
    """Format a 14-digit string as ``XX.XXX.XXX/XXXX-XX``."""
    clean = re.sub(r"[.\-/]", "", digits)
    if len(clean) != 14:
        return digits
    return f"{clean[:2]}.{clean[2:5]}.{clean[5:8]}/{clean[8:12]}-{clean[12:]}"


def format_company_graph(data: dict[str, Any]) -> str:
    """Turn a ``GraphResponse`` into a readable Telegram message."""
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    if not nodes:
        return "ℹ️ Nenhum resultado encontrado para esse CNPJ."

    # Find center node
    center_id = data.get("center_id")
    center_node = None
    for node in nodes:
        if node.get("id") == center_id:
            center_node = node
            break
    if center_node is None:
        center_node = nodes[0]

    props = center_node.get("properties", {})
    company_name = center_node.get("label", "Desconhecido")
    cnpj_raw = props.get("cnpj", "")
    cnpj_display = format_cnpj(cnpj_raw) if cnpj_raw else "N/A"

    sections: list[str] = []

    # Header
    sections.append(f"🏢 *{_escape_md(company_name)}*")
    sections.append(f"📋 CNPJ: `{cnpj_display}`")

    # Extra properties
    situacao = props.get("situacao_cadastral", props.get("situacao"))
    if situacao:
        sections.append(f"📌 Situação: {_escape_md(str(situacao))}")

    natureza = props.get("natureza_juridica")
    if natureza:
        sections.append(f"⚖️ Natureza: {_escape_md(str(natureza))}")

    capital = props.get("capital_social")
    if capital:
        with contextlib.suppress(ValueError, TypeError):
            sections.append(f"💰 Capital Social: R$ {float(capital):,.2f}")

    # Connection summary
    other_nodes = [n for n in nodes if n.get("id") != center_id]
    if other_nodes:
        sections.append(f"\n🔗 *Conexões encontradas:* {len(other_nodes)}")
        type_counts: dict[str, int] = {}
        for node in other_nodes:
            node_type = node.get("type", "unknown")
            type_counts[node_type] = type_counts.get(node_type, 0) + 1
        for node_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            emoji = _type_emoji(node_type)
            sections.append(f"  {emoji} {_escape_md(node_type)}: {count}")

    if edges:
        sections.append(f"↔️ Relações: {len(edges)}")

    # Sources
    sources = center_node.get("sources", [])
    if sources:
        source_names = [s.get("database", "?") for s in sources]
        sections.append(f"\n📚 Fontes: {', '.join(source_names)}")

    sections.append("\n_Dados públicos — fonte: BR/ACC Open Graph_")

    return _truncate("\n".join(sections))


def format_search_results(data: dict[str, Any]) -> str:
    """Turn a ``SearchResponse`` into a readable Telegram message."""
    results = data.get("results", [])
    total = data.get("total", 0)

    if not results:
        return "🔍 Nenhum resultado encontrado para essa busca."

    plural = "s" if total != 1 else ""
    sections: list[str] = [
        f"🔍 *Resultados* \\({total} encontrado{plural}\\):\n",
    ]

    for i, result in enumerate(results[:5], 1):
        name = result.get("name", "Sem nome")
        entity_type = result.get("type", "unknown")
        doc = result.get("document")
        emoji = _type_emoji(entity_type)

        line = f"{i}\\. {emoji} *{_escape_md(name)}*"
        if doc:
            digits = re.sub(r"[^0-9]", "", doc)
            display = format_cnpj(doc) if len(digits) == 14 else doc
            line += f"\n   📋 `{display}`"
        line += f"\n   Tipo: {_escape_md(entity_type)}"
        sections.append(line)

    sections.append("\n_Use /consulta <CNPJ> para detalhes_")
    return _truncate("\n".join(sections))


def format_meta(data: dict[str, Any]) -> str:
    """Turn a public meta response into a readable Telegram message."""
    sections: list[str] = ["📊 *BR/ACC Open Graph — Estatísticas*\n"]

    total_nodes = data.get("total_nodes", 0)
    total_rels = data.get("total_relationships", 0)
    sections.append(f"🌐 Total de nós: *{total_nodes:,}*")
    sections.append(f"↔️ Total de relações: *{total_rels:,}*")

    company_count = data.get("company_count", 0)
    contract_count = data.get("contract_count", 0)
    sanction_count = data.get("sanction_count", 0)

    sections.append(f"\n🏢 Empresas: {company_count:,}")
    sections.append(f"📄 Contratos: {contract_count:,}")
    sections.append(f"⚠️ Sanções: {sanction_count:,}")

    health = data.get("source_health", {})
    if health:
        implemented = health.get("implemented_sources", 0)
        loaded = health.get("loaded_sources", 0)
        sections.append(f"\n📡 Fontes implementadas: {implemented}")
        sections.append(f"✅ Fontes carregadas: {loaded}")

    sections.append("\n_Dados públicos — fonte: BR/ACC Open Graph_")
    return _truncate("\n".join(sections))


def format_rate_limit_exceeded(remaining_days: int) -> str:
    """Message shown when the user exceeds their monthly quota."""
    return (
        "⏳ *Limite mensal atingido*\n\n"
        "Você atingiu o limite de consultas deste mês\\.\n"
        f"Seu limite será renovado em *{remaining_days}* "
        f"dia{'s' if remaining_days != 1 else ''}\\.\n\n"
        "_Isso ajuda a manter o serviço gratuito para todos\\._"
    )


def format_error(detail: str | None = None) -> str:
    """Generic error message."""
    msg = "❌ *Erro ao processar sua consulta*\n\n"
    if detail:
        msg += f"{_escape_md(detail)}\n\n"
    msg += "_Tente novamente em alguns instantes\\._"
    return msg


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _type_emoji(entity_type: str) -> str:
    mapping: dict[str, str] = {
        "company": "🏢",
        "person": "👤",
        "contract": "📄",
        "sanction": "⚠️",
        "embargo": "🚫",
        "partner": "🤝",
        "amendment": "📝",
        "convenio": "🤝",
        "publicoffice": "🏛️",
        "fund": "💰",
        "politician": "🗳️",
    }
    return mapping.get(entity_type.lower(), "📌")


def _escape_md(text: str) -> str:
    """Escape MarkdownV2 special characters for Telegram."""
    specials = r"_*[]()~`>#+-=|{}.!"
    escaped = ""
    for char in text:
        if char in specials:
            escaped += f"\\{char}"
        else:
            escaped += char
    return escaped


def _truncate(text: str) -> str:
    """Truncate to Telegram's 4096-char limit."""
    if len(text) <= _MAX_MESSAGE_LENGTH:
        return text
    return text[: _MAX_MESSAGE_LENGTH - 30] + "\n\n_\\.\\.\\. \\(truncado\\)_"
