"""Transparency & web search tools for the EGOS Inteligência chatbot.

Tools:
- web_search: DuckDuckGo HTML search (no API key needed)
- search_emendas: Portal da Transparência emendas by city/state
- search_transferencias: Federal transfers to municipalities
- search_ceap: CEAP parliamentary expenses
- search_pep_city: Politically exposed persons by city
"""

import asyncio
import logging
import os
import re
from typing import Any
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/json",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# Portal da Transparência base (public, no key needed for HTML scraping)
_PT_BASE = "https://api.portaldatransparencia.gov.br/api-de-dados"
# TransfereGov API
_TG_BASE = "https://api.transferegov.gestao.gov.br"


async def tool_web_search(query: str, max_results: int = 8) -> list[dict[str, str]]:
    """Web search: Brave Search API primary, DuckDuckGo fallback."""
    results: list[dict[str, str]] = []
    brave_key = os.environ.get("BRAVE_API_KEY", "")

    # Try Brave Search first
    if brave_key:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": max_results, "search_lang": "pt-br"},
                    headers={"Accept": "application/json", "X-Subscription-Token": brave_key},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("web", {}).get("results", [])[:max_results]:
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "snippet": r.get("description", "")[:300],
                        })
                    if results:
                        return results
        except Exception as e:
            logger.warning("Brave search failed, falling back to DDG: %s", e)

    # Fallback: DuckDuckGo HTML
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=_HEADERS)
            html = resp.text

        snippets = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.+?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(.+?)</a>',
            html, re.DOTALL
        )
        for href, title, snippet in snippets[:max_results]:
            actual_url = href
            if "uddg=" in href:
                m = re.search(r"uddg=([^&]+)", href)
                if m:
                    from urllib.parse import unquote
                    actual_url = unquote(m.group(1))
            results.append({
                "title": re.sub(r"<[^>]+>", "", title).strip(),
                "url": actual_url,
                "snippet": re.sub(r"<[^>]+>", "", snippet).strip()[:300],
            })
    except Exception as e:
        logger.warning("DDG search also failed: %s", e)
        results.append({"title": "Erro na busca", "url": "", "snippet": str(e)[:200]})

    return results


async def tool_search_emendas(municipio: str, uf: str = "", ano: int = 2024) -> dict[str, Any]:
    """Search parliamentary amendments (emendas) for a municipality.
    Uses Portal da Transparência web scraping."""
    query = f"emendas parlamentares {municipio} {uf} {ano} site:portaldatransparencia.gov.br"
    web_results = await tool_web_search(query, max_results=3)

    # Also search for actual data via TransfereGov if possible
    tg_results: list[dict[str, Any]] = []
    try:
        search_url = f"https://api.transferegov.gestao.gov.br/transferenciasespeciais/transferencia?nome_municipio=ilike.*{quote_plus(municipio)}*&limit=10"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(search_url, headers={"Accept": "application/json"})
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for item in data[:10]:
                        tg_results.append({
                            "parlamentar": item.get("nome_parlamentar", ""),
                            "valor": item.get("valor_transferencia", 0),
                            "municipio": item.get("nome_municipio", ""),
                            "uf": item.get("sigla_uf", ""),
                            "objeto": item.get("objeto", "")[:200],
                            "ano": item.get("ano_emenda", ""),
                        })
    except Exception as e:
        logger.warning("TransfereGov API failed: %s", e)

    return {
        "municipio": municipio,
        "uf": uf,
        "ano": ano,
        "transferegov_results": tg_results,
        "web_references": web_results,
        "fonte": "TransfereGov API + Portal da Transparência",
    }


async def tool_search_transferencias(municipio: str, uf: str = "", ano: int = 2024) -> dict[str, Any]:
    """Search federal transfers to a municipality."""
    query = f"transferencias federais {municipio} {uf} {ano} site:portaldatransparencia.gov.br OR site:tesourotransparente.gov.br"
    web_results = await tool_web_search(query, max_results=3)

    # Try TransfereGov convenios API
    convenios: list[dict[str, Any]] = []
    try:
        conv_url = f"https://api.transferegov.gestao.gov.br/convenio?nome_municipio=ilike.*{quote_plus(municipio)}*&limit=10&order=valor_global.desc"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(conv_url, headers={"Accept": "application/json"})
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for item in data[:10]:
                        convenios.append({
                            "proponente": item.get("nome_proponente", ""),
                            "valor_global": item.get("valor_global", 0),
                            "objeto": item.get("objeto_proposta", "")[:200],
                            "situacao": item.get("situacao_proposta", ""),
                            "orgao": item.get("nome_orgao_concedente", ""),
                        })
    except Exception as e:
        logger.warning("TransfereGov convenios failed: %s", e)

    return {
        "municipio": municipio,
        "convenios": convenios,
        "web_references": web_results,
        "fonte": "TransfereGov API + Tesouro Transparente",
    }


async def tool_search_ceap(parlamentar: str = "", uf: str = "", ano: int = 2024) -> dict[str, Any]:
    """Search CEAP (Cota para Exercício da Atividade Parlamentar) expenses.
    Uses Dados Abertos da Câmara API."""
    results: list[dict[str, Any]] = []
    try:
        # Câmara dos Deputados API - public, no key needed
        params = {"ano": ano, "itens": 10, "ordem": "DESC", "ordenarPor": "dataDocumento"}
        if uf:
            params["siglaUf"] = uf.upper()

        # First find the deputado by name
        if parlamentar:
            dep_url = f"https://dadosabertos.camara.leg.br/api/v2/deputados?nome={quote_plus(parlamentar)}&ordem=ASC&ordenarPor=nome"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(dep_url, headers={"Accept": "application/json"})
                if resp.status_code == 200:
                    deps = resp.json().get("dados", [])
                    for dep in deps[:3]:
                        dep_id = dep.get("id")
                        dep_name = dep.get("nome", "")
                        dep_party = dep.get("siglaPartido", "")
                        dep_uf = dep.get("siglaUf", "")

                        # Get expenses for this deputado
                        exp_url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{dep_id}/despesas?ano={ano}&itens=15&ordem=DESC&ordenarPor=dataDocumento"
                        exp_resp = await client.get(exp_url, headers={"Accept": "application/json"})
                        if exp_resp.status_code == 200:
                            expenses = exp_resp.json().get("dados", [])
                            total = sum(float(e.get("valorDocumento", 0)) for e in expenses)
                            top_categories: dict[str, float] = {}
                            for e in expenses:
                                cat = e.get("tipoDespesa", "Outros")
                                top_categories[cat] = top_categories.get(cat, 0) + float(e.get("valorDocumento", 0))

                            results.append({
                                "deputado": dep_name,
                                "partido": dep_party,
                                "uf": dep_uf,
                                "total_amostra": round(total, 2),
                                "num_despesas": len(expenses),
                                "top_categorias": dict(sorted(top_categories.items(), key=lambda x: -x[1])[:5]),
                                "despesas_recentes": [
                                    {
                                        "tipo": e.get("tipoDespesa", ""),
                                        "fornecedor": e.get("nomeFornecedor", ""),
                                        "cnpj_fornecedor": e.get("cnpjCpfFornecedor", ""),
                                        "valor": float(e.get("valorDocumento", 0)),
                                        "data": e.get("dataDocumento", ""),
                                    }
                                    for e in expenses[:5]
                                ],
                            })
        else:
            # No specific parlamentar - list top spenders from UF
            if uf:
                try:
                    dep_url = f"https://dadosabertos.camara.leg.br/api/v2/deputados?siglaUf={uf.upper()}&ordem=ASC&ordenarPor=nome&itens=15"
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.get(dep_url, headers={"Accept": "application/json"})
                        if resp.status_code == 200:
                            deps = resp.json().get("dados", [])
                            for dep in deps[:8]:
                                dep_id = dep.get("id")
                                dep_name = dep.get("nome", "")
                                dep_party = dep.get("siglaPartido", "")
                                exp_url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{dep_id}/despesas?ano={ano}&itens=10&ordem=DESC&ordenarPor=dataDocumento"
                                exp_resp = await client.get(exp_url, headers={"Accept": "application/json"})
                                if exp_resp.status_code == 200:
                                    expenses = exp_resp.json().get("dados", [])
                                    total = sum(float(e.get("valorDocumento", 0)) for e in expenses)
                                    if total > 0:
                                        results.append({
                                            "deputado": dep_name,
                                            "partido": dep_party,
                                            "uf": uf.upper(),
                                            "total_amostra": round(total, 2),
                                            "num_despesas": len(expenses),
                                        })
                except Exception as e:
                    logger.warning("CEAP UF search failed: %s", e)
            if not results:
                query = f"CEAP despesas parlamentares {uf} {ano}"
                web_results = await tool_web_search(query, max_results=3)
                return {"uf": uf, "ano": ano, "web_references": web_results, "fonte": "Dados Abertos da Câmara"}

    except Exception as e:
        logger.warning("CEAP search failed: %s", e)

    return {
        "parlamentar": parlamentar,
        "uf": uf,
        "ano": ano,
        "resultados": results,
        "fonte": "Dados Abertos da Câmara dos Deputados (dadosabertos.camara.leg.br)",
    }


async def tool_search_pep_city(cidade: str, uf: str = "") -> dict[str, Any]:
    """Search politically exposed persons (PEPs) and public figures for a city.
    Combines Neo4j graph data with web search."""
    # Search for politicians, judges, prosecutors in this city
    queries = [
        f"prefeito vereador {cidade} {uf} 2024",
        f"politicos investigados {cidade} {uf}",
        f"deputado federal {uf} emendas {cidade}",
    ]

    all_results: list[dict[str, str]] = []
    for q in queries:
        results = await tool_web_search(q, max_results=2)
        all_results.extend(results)

    # Search Câmara API for deputies from this state (with mandate info)
    deputados: list[dict[str, str]] = []
    if uf:
        try:
            dep_url = f"https://dadosabertos.camara.leg.br/api/v2/deputados?siglaUf={uf.upper()}&ordem=ASC&ordenarPor=nome&itens=50"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(dep_url, headers={"Accept": "application/json"})
                if resp.status_code == 200:
                    deps = resp.json().get("dados", [])

                    async def _enrich_deputy(dep: dict) -> dict[str, str]:
                        dep_id = dep.get("id")
                        dep_info: dict[str, str] = {
                            "nome": dep.get("nome", ""),
                            "partido": dep.get("siglaPartido", ""),
                            "uf": dep.get("siglaUf", ""),
                            "email": dep.get("email", ""),
                            "id_camara": str(dep_id or ""),
                        }
                        if not dep_id:
                            return dep_info
                        try:
                            # Fetch detail + legislatures in parallel
                            detail_resp, hist_resp = await asyncio.gather(
                                client.get(f"https://dadosabertos.camara.leg.br/api/v2/deputados/{dep_id}", headers={"Accept": "application/json"}),
                                client.get(f"https://dadosabertos.camara.leg.br/api/v2/deputados/{dep_id}/legislaturas", headers={"Accept": "application/json"}),
                            )
                            if detail_resp.status_code == 200:
                                detail = detail_resp.json().get("dados", {})
                                status = detail.get("ultimoStatus", {})
                                dep_info["legislatura_atual"] = str(status.get("idLegislatura", ""))
                                dep_info["data_inicio_mandato"] = status.get("data", "")
                                dep_info["condicao_eleitoral"] = status.get("condicaoEleitoral", "")
                                dep_info["situacao"] = status.get("situacao", "")
                            if hist_resp.status_code == 200:
                                legislaturas = hist_resp.json().get("dados", [])
                                dep_info["total_mandatos"] = str(len(legislaturas))
                                if legislaturas:
                                    mandatos_periodos = []
                                    for leg in legislaturas:
                                        inicio = leg.get("dataInicio", "")
                                        fim = leg.get("dataFim", "")
                                        mandatos_periodos.append(f"{inicio} a {fim}")
                                    dep_info["mandatos_periodos"] = "; ".join(mandatos_periodos)
                        except Exception:
                            pass  # mandate info is best-effort
                        return dep_info

                    # Enrich up to 15 deputies in parallel, rest get basic info
                    enriched = await asyncio.gather(*[_enrich_deputy(d) for d in deps[:15]])
                    deputados.extend(enriched)
                    for dep in deps[15:]:
                        deputados.append({
                            "nome": dep.get("nome", ""),
                            "partido": dep.get("siglaPartido", ""),
                            "uf": dep.get("siglaUf", ""),
                            "email": dep.get("email", ""),
                            "id_camara": str(dep.get("id", "")),
                        })
        except Exception as e:
            logger.warning("Deputados API failed: %s", e)

    return {
        "cidade": cidade,
        "uf": uf,
        "deputados_federais": deputados,
        "web_references": all_results,
        "dica": f"Use search_ceap com o nome do deputado para ver gastos. Use search_emendas com '{cidade}' para ver emendas direcionadas.",
        "fonte": "Dados Abertos da Câmara + Web Search",
    }


# Querido Diário API (Open Knowledge Brasil) — free, no API key
_QD_BASE = "https://api.queridodiario.ok.org.br"

# IBGE codes for major cities (expand as needed)
_IBGE_CODES: dict[str, str] = {
    "uberlandia": "3170206", "sao paulo": "3550308", "rio de janeiro": "3304557",
    "belo horizonte": "3106200", "brasilia": "5300108", "curitiba": "4106902",
    "salvador": "2927408", "fortaleza": "2304400", "recife": "2611606",
    "porto alegre": "4314902", "goiania": "5208707", "manaus": "1302603",
    "campinas": "3509502", "patos de minas": "3148004", "uberaba": "3170107",
    "juiz de fora": "3136702", "florianopolis": "4205407", "vitoria": "3205309",
    "natal": "2408102", "joao pessoa": "2507507", "maceio": "2704302",
    "campo grande": "5002704", "teresina": "2211001", "sao luis": "2111300",
    "aracaju": "2800308", "cuiaba": "5103403", "belem": "1501402",
    "macapa": "1600303", "palmas": "1721000", "boa vista": "1400100",
    "porto velho": "1100205", "rio branco": "1200401",
}


async def tool_search_gazettes(municipio: str, query: str = "", max_results: int = 5) -> dict[str, Any]:
    """Search municipal official gazettes via Querido Diário API."""
    municipio_lower = municipio.lower().strip()

    # Try to find IBGE code
    territory_id = _IBGE_CODES.get(municipio_lower, "")

    results: list[dict[str, Any]] = []
    try:
        # If we don't have the IBGE code, search for the city first
        if not territory_id:
            async with httpx.AsyncClient(timeout=15.0) as client:
                city_resp = await client.get(f"{_QD_BASE}/cities?city_name={quote_plus(municipio)}")
                if city_resp.status_code == 200:
                    cities = city_resp.json().get("cities", [])
                    if cities:
                        territory_id = cities[0].get("territory_id", "")

        if not territory_id:
            return {"municipio": municipio, "error": "Cidade nao encontrada no Querido Diario", "dica": "Tente o nome completo da cidade"}

        # Search gazettes
        search_query = query if query else municipio
        params = {
            "territory_ids": territory_id,
            "querystring": search_query,
            "excerpt_size": 300,
            "number_of_excerpts": 2,
            "size": min(max_results, 10),
            "sort_by": "descending_date",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{_QD_BASE}/gazettes", params=params)
            if resp.status_code == 200:
                data = resp.json()
                total = data.get("total_gazettes", 0)
                for gz in data.get("gazettes", [])[:max_results]:
                    excerpts = gz.get("excerpts", [])
                    results.append({
                        "data": gz.get("date", ""),
                        "municipio": gz.get("territory_name", municipio),
                        "uf": gz.get("state_code", ""),
                        "url": gz.get("url", ""),
                        "trechos": [e[:300] for e in excerpts[:2]],
                        "edicao": gz.get("edition", ""),
                    })

                return {
                    "municipio": municipio,
                    "territory_id": territory_id,
                    "query": search_query,
                    "total_resultados": total,
                    "resultados": results,
                    "fonte": "Querido Diário (queridodiario.ok.org.br) — Open Knowledge Brasil",
                }

    except Exception as e:
        logger.warning("Querido Diario search failed: %s", e)

    return {"municipio": municipio, "query": query, "resultados": results, "fonte": "Querido Diário"}


async def tool_cnpj_info(cnpj: str) -> dict[str, Any]:
    """Get company info and partners by CNPJ via Querido Diário API."""
    # Clean CNPJ
    cnpj_clean = re.sub(r"[^0-9]", "", cnpj)
    if len(cnpj_clean) != 14:
        return {"error": f"CNPJ invalido: {cnpj}. Deve ter 14 digitos."}

    info: dict[str, Any] = {}
    partners: list[dict[str, str]] = []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Company info
            resp = await client.get(f"{_QD_BASE}/company/info/{cnpj_clean}")
            if resp.status_code == 200:
                data = resp.json()
                info = {
                    "cnpj": data.get("cnpj_basico", cnpj_clean),
                    "razao_social": data.get("razao_social", ""),
                    "nome_fantasia": data.get("nome_fantasia", ""),
                    "situacao": data.get("situacao_cadastral", ""),
                    "natureza_juridica": data.get("natureza_juridica", ""),
                    "porte": data.get("porte_empresa", ""),
                    "capital_social": data.get("capital_social", 0),
                    "cnae_principal": data.get("cnae_fiscal_principal", ""),
                    "municipio": data.get("municipio", ""),
                    "uf": data.get("uf", ""),
                    "data_inicio": data.get("data_inicio_atividade", ""),
                }

            # Partners
            resp2 = await client.get(f"{_QD_BASE}/company/partners/{cnpj_clean}")
            if resp2.status_code == 200:
                data2 = resp2.json()
                for p in data2.get("socios", data2 if isinstance(data2, list) else []):
                    if isinstance(p, dict):
                        partners.append({
                            "nome": p.get("nome_socio", p.get("nome", "")),
                            "qualificacao": p.get("qualificacao_socio", ""),
                            "data_entrada": p.get("data_entrada_sociedade", ""),
                        })

    except Exception as e:
        logger.warning("CNPJ lookup failed: %s", e)

    return {
        "cnpj": cnpj_clean,
        "empresa": info,
        "socios": partners,
        "dica": "Use search_entities com o nome dos sócios para encontrar conexões no grafo. Use search_gazettes com o CNPJ para ver menções em diários oficiais.",
        "fonte": "Querido Diário (CNPJ) + Receita Federal",
    }



async def tool_search_votacoes(parlamentar: str = "", proposicao: str = "", ano: int = 2024) -> dict[str, Any]:
    """Search roll call votes (votações nominais) from Câmara dos Deputados API."""
    results: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            if parlamentar:
                # Find deputy first
                dep_url = f"https://dadosabertos.camara.leg.br/api/v2/deputados?nome={quote_plus(parlamentar)}&ordem=ASC&ordenarPor=nome"
                resp = await client.get(dep_url, headers={"Accept": "application/json"})
                if resp.status_code == 200:
                    deps = resp.json().get("dados", [])
                    for dep in deps[:2]:
                        dep_id = dep.get("id")
                        dep_name = dep.get("nome", "")
                        # Get recent votes
                        # First get recent votações
                        vot_url = f"https://dadosabertos.camara.leg.br/api/v2/votacoes?ordem=DESC&ordenarPor=dataHoraRegistro&itens=5"
                        vot_resp = await client.get(vot_url, headers={"Accept": "application/json"})
                        if vot_resp.status_code == 200:
                            votacoes = vot_resp.json().get("dados", [])
                            for vot in votacoes[:5]:
                                vot_id = vot.get("id", "")
                                # Check how this deputy voted
                                votos_url = f"https://dadosabertos.camara.leg.br/api/v2/votacoes/{vot_id}/votos"
                                votos_resp = await client.get(votos_url, headers={"Accept": "application/json"})
                                if votos_resp.status_code == 200:
                                    votos = votos_resp.json().get("dados", [])
                                    dep_voto = next((v for v in votos if v.get("deputado_", {}).get("id") == dep_id), None)
                                    if dep_voto:
                                        results.append({
                                            "deputado": dep_name,
                                            "votacao": vot.get("descricao", "")[:150],
                                            "data": vot.get("dataHoraRegistro", "")[:10],
                                            "voto": dep_voto.get("tipoVoto", ""),
                                            "proposicao": vot.get("proposicao_", {}).get("ementa", "")[:200] if vot.get("proposicao_") else "",
                                        })
            else:
                # List recent votações
                vot_url = f"https://dadosabertos.camara.leg.br/api/v2/votacoes?ordem=DESC&ordenarPor=dataHoraRegistro&itens=10"
                resp = await client.get(vot_url, headers={"Accept": "application/json"})
                if resp.status_code == 200:
                    votacoes = resp.json().get("dados", [])
                    for vot in votacoes[:10]:
                        # Count votes
                        vot_id = vot.get("id", "")
                        sim = nao = abst = 0
                        votos_url = f"https://dadosabertos.camara.leg.br/api/v2/votacoes/{vot_id}/votos"
                        votos_resp = await client.get(votos_url, headers={"Accept": "application/json"})
                        if votos_resp.status_code == 200:
                            votos = votos_resp.json().get("dados", [])
                            for v in votos:
                                tipo = v.get("tipoVoto", "")
                                if tipo == "Sim":
                                    sim += 1
                                elif tipo in ("Não", "Nao"):
                                    nao += 1
                                else:
                                    abst += 1

                        results.append({
                            "descricao": vot.get("descricao", "")[:200],
                            "data": vot.get("dataHoraRegistro", "")[:10],
                            "aprovada": vot.get("aprovacao", None),
                            "sim": sim,
                            "nao": nao,
                            "abstencoes": abst,
                        })

    except Exception as e:
        logger.warning("Votacoes search failed: %s", e)

    return {
        "parlamentar": parlamentar,
        "ano": ano,
        "votacoes": results,
        "fonte": "Dados Abertos da Câmara dos Deputados (votações nominais)",
        "dica": "Use com o nome de um deputado para ver como ele votou em cada proposição.",
    }



# ─── Portal da Transparência (with API key) ───────────────────────────

PORTAL_API_KEY = os.environ.get("PORTAL_TRANSPARENCIA_API_KEY", "")
PORTAL_BASE = "https://api.portaldatransparencia.gov.br/api-de-dados"
PORTAL_HEADERS = {
    "Accept": "application/json",
    "chave-api-dados": PORTAL_API_KEY,
}


async def tool_search_servidores(nome: str = "", cpf: str = "", orgao: str = "") -> dict[str, Any]:
    """Search federal public servants — name, salary, position, org."""
    results: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            params: dict[str, str] = {"pagina": "1"}
            if cpf:
                params["cpfServidor"] = cpf.replace(".", "").replace("-", "")
            elif orgao:
                params["codigoOrgaoServidorExercicio"] = orgao
            else:
                # API requires CPF or orgao code — try by-name endpoint
                resp = await client.get(
                    f"{PORTAL_BASE}/servidores/remuneracao",
                    params={"nome": nome, "pagina": "1"} if nome else {"pagina": "1"},
                    headers=PORTAL_HEADERS,
                )
                if resp.status_code == 200:
                    for s in resp.json()[:10]:
                        results.append({
                            "nome": s.get("nome", ""),
                            "cpf": s.get("cpf", ""),
                            "cargo": s.get("descricaoCargo", ""),
                            "orgao": s.get("orgaoExercicio", ""),
                            "remuneracao_bruta": s.get("remuneracaoBruta", ""),
                            "remuneracao_liquida": s.get("remuneracaoLiquida", ""),
                        })
                return {
                    "query": nome or cpf,
                    "servidores": results,
                    "fonte": "Portal da Transparência — Servidores",
                    "nota": "Busca por nome pode ser limitada. Use CPF para resultado exato." if not cpf else "",
                }

            resp = await client.get(
                f"{PORTAL_BASE}/servidores",
                params=params,
                headers=PORTAL_HEADERS,
            )
            if resp.status_code == 200:
                for s in resp.json()[:10]:
                    results.append({
                        "nome": s.get("nome", ""),
                        "cpf": s.get("cpf", ""),
                        "cargo": s.get("cargo", {}).get("descricao", "") if isinstance(s.get("cargo"), dict) else s.get("descricaoCargo", ""),
                        "orgao_exercicio": s.get("orgaoServidorExercicio", {}).get("nome", "") if isinstance(s.get("orgaoServidorExercicio"), dict) else "",
                        "orgao_lotacao": s.get("orgaoServidorLotacao", {}).get("nome", "") if isinstance(s.get("orgaoServidorLotacao"), dict) else "",
                        "situacao": s.get("situacaoServidor", {}).get("descricao", "") if isinstance(s.get("situacaoServidor"), dict) else "",
                        "remuneracao_bruta": s.get("remuneracaoBruta", ""),
                        "remuneracao_liquida": s.get("remuneracaoAposDeducoes", ""),
                    })
            else:
                logger.warning("Portal servidores HTTP %s", resp.status_code)
    except Exception as e:
        logger.warning("Portal servidores failed: %s", e)

    return {
        "query": nome or cpf,
        "servidores": results,
        "fonte": "Portal da Transparência — Servidores do Poder Executivo Federal",
        "dica": "Use o CPF para busca exata. Combine com CNPJ para investigar servidores donos de empresas.",
    }


async def tool_search_licitacoes(orgao: str = "", uf: str = "", modalidade: str = "", ano: int = 2024) -> dict[str, Any]:
    """Search federal government procurement/bids."""
    results: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            params: dict[str, str] = {"pagina": "1", "dataInicial": f"01/01/{ano}", "dataFinal": f"31/12/{ano}"}
            # Licitacoes requires codigoOrgao — use contratos endpoint which is more flexible
            if orgao:
                params["codigoOrgao"] = orgao
            # Try contratos endpoint instead (more flexible filters)
            resp = await client.get(
                f"{PORTAL_BASE}/contratos",
                params=params,
                headers=PORTAL_HEADERS,
            )
            if resp.status_code == 200:
                for l in resp.json()[:10]:
                    results.append({
                        "numero": l.get("numero", ""),
                        "objeto": l.get("objeto", "")[:200],
                        "orgao": l.get("orgao", {}).get("nome", "") if isinstance(l.get("orgao"), dict) else "",
                        "modalidade": l.get("modalidadeLicitacao", {}).get("descricao", "") if isinstance(l.get("modalidadeLicitacao"), dict) else "",
                        "valor_estimado": l.get("valorEstimado", ""),
                        "situacao": l.get("situacao", {}).get("descricao", "") if isinstance(l.get("situacao"), dict) else "",
                        "data_abertura": l.get("dataAbertura", ""),
                    })
            else:
                logger.warning("Portal licitacoes HTTP %s", resp.status_code)
    except Exception as e:
        logger.warning("Portal licitacoes failed: %s", e)

    return {
        "uf": uf,
        "ano": ano,
        "licitacoes": results,
        "fonte": "Portal da Transparência — Licitações do Poder Executivo Federal",
    }


async def tool_search_cpgf(nome: str = "", orgao: str = "", mes: int = 0, ano: int = 2024) -> dict[str, Any]:
    """Search government credit card (CPGF) expenses."""
    results: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            params: dict[str, str] = {"pagina": "1"}
            if nome:
                params["nomePortadorCartao"] = nome
            if orgao:
                params["codigoOrgao"] = orgao
            if mes:
                params["mesExtrato"] = str(mes)
            params["anoExtrato"] = str(ano)

            resp = await client.get(
                f"{PORTAL_BASE}/cartoes",
                params=params,
                headers=PORTAL_HEADERS,
            )
            if resp.status_code == 200:
                for c in resp.json()[:10]:
                    results.append({
                        "portador": c.get("nomePortadorCartao", ""),
                        "cpf_portador": c.get("cpfPortadorCartao", ""),
                        "orgao": c.get("orgao", {}).get("nome", "") if isinstance(c.get("orgao"), dict) else "",
                        "valor_transacao": c.get("valorTransacao", ""),
                        "nome_favorecido": c.get("nomeFavorecido", ""),
                        "data_transacao": c.get("dataTransacao", ""),
                        "tipo_transacao": c.get("tipoTransacao", ""),
                    })
            else:
                logger.warning("Portal CPGF HTTP %s", resp.status_code)
    except Exception as e:
        logger.warning("Portal CPGF failed: %s", e)

    return {
        "query": nome or orgao,
        "ano": ano,
        "gastos_cartao": results,
        "fonte": "Portal da Transparência — Gastos por Cartão de Pagamento (CPGF)",
        "dica": "CPGF = cartão corporativo do governo. Investigue gastos suspeitos: restaurantes caros, viagens, compras pessoais.",
    }


async def tool_search_viagens(nome: str = "", orgao: str = "", ano: int = 2024) -> dict[str, Any]:
    """Search government travel expenses."""
    results: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            params: dict[str, str] = {"pagina": "1"}
            if nome:
                params["nomeProposto"] = nome
            if orgao:
                params["codigoOrgao"] = orgao
            params["anoViagem"] = str(ano)

            resp = await client.get(
                f"{PORTAL_BASE}/viagens",
                params=params,
                headers=PORTAL_HEADERS,
            )
            if resp.status_code == 200:
                for v in resp.json()[:10]:
                    results.append({
                        "nome": v.get("nomeProposto", ""),
                        "cargo": v.get("cargo", ""),
                        "orgao": v.get("orgao", {}).get("nome", "") if isinstance(v.get("orgao"), dict) else "",
                        "destino": v.get("destino", ""),
                        "data_ida": v.get("dataIdaViagem", ""),
                        "data_volta": v.get("dataVoltaViagem", ""),
                        "valor_diarias": v.get("valorDiarias", ""),
                        "valor_passagens": v.get("valorPassagens", ""),
                        "motivo": v.get("motivo", "")[:150],
                    })
            else:
                logger.warning("Portal viagens HTTP %s", resp.status_code)
    except Exception as e:
        logger.warning("Portal viagens failed: %s", e)

    return {
        "query": nome or orgao,
        "ano": ano,
        "viagens": results,
        "fonte": "Portal da Transparência — Viagens a Serviço do Governo Federal",
        "dica": "Compare viagens com votações: servidor viajou mas não estava no órgão? Viagens repetidas ao mesmo destino?",
    }


async def tool_search_contratos(orgao: str = "", fornecedor: str = "", ano: int = 2024) -> dict[str, Any]:
    """Search federal government contracts."""
    results: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            params: dict[str, str] = {"pagina": "1"}
            if fornecedor:
                params["nomeFornecedor"] = fornecedor
            if orgao:
                params["codigoOrgao"] = orgao
            params["dataInicial"] = f"01/01/{ano}"
            params["dataFinal"] = f"31/12/{ano}"

            resp = await client.get(
                f"{PORTAL_BASE}/contratos",
                params=params,
                headers=PORTAL_HEADERS,
            )
            if resp.status_code == 200:
                for c in resp.json()[:10]:
                    results.append({
                        "numero": c.get("numero", ""),
                        "objeto": c.get("objeto", "")[:200],
                        "orgao": c.get("orgao", {}).get("nome", "") if isinstance(c.get("orgao"), dict) else "",
                        "fornecedor": c.get("fornecedor", {}).get("nome", "") if isinstance(c.get("fornecedor"), dict) else "",
                        "cnpj_fornecedor": c.get("fornecedor", {}).get("cnpjCpf", "") if isinstance(c.get("fornecedor"), dict) else "",
                        "valor_inicial": c.get("valorInicial", ""),
                        "valor_final": c.get("valorFinal", ""),
                        "data_inicio": c.get("dataInicioVigencia", ""),
                        "data_fim": c.get("dataFimVigencia", ""),
                    })
            else:
                logger.warning("Portal contratos HTTP %s", resp.status_code)
    except Exception as e:
        logger.warning("Portal contratos failed: %s", e)

    return {
        "query": fornecedor or orgao,
        "ano": ano,
        "contratos": results,
        "fonte": "Portal da Transparência — Contratos do Poder Executivo Federal",
        "dica": "Investigue: mesmo fornecedor com múltiplos contratos? Valor final >> valor inicial (aditivos)?",
    }


async def tool_search_sancoes(cnpj: str = "", nome: str = "") -> dict[str, Any]:
    """Search CEIS (inidôneas) + CNEP (punidas) sanctions."""
    results: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for endpoint, label in [("ceis", "CEIS - Empresa Inidônea"), ("cnep", "CNEP - Empresa Punida")]:
                params: dict[str, str] = {"pagina": "1"}
                if cnpj:
                    params["cnpjSancionado"] = cnpj.replace(".", "").replace("/", "").replace("-", "")
                if nome:
                    params["nomeSancionado"] = nome

                resp = await client.get(
                    f"{PORTAL_BASE}/{endpoint}",
                    params=params,
                    headers=PORTAL_HEADERS,
                )
                if resp.status_code == 200:
                    for s in resp.json()[:5]:
                        results.append({
                            "cadastro": label,
                            "nome": s.get("nomeSancionado", "") or s.get("sancionado", {}).get("nome", ""),
                            "cnpj_cpf": s.get("cnpjSancionado", "") or s.get("cpfSancionado", ""),
                            "orgao_sancionador": s.get("orgaoSancionador", {}).get("nome", "") if isinstance(s.get("orgaoSancionador"), dict) else "",
                            "tipo_sancao": s.get("tipoSancao", {}).get("descricaoResumida", "") if isinstance(s.get("tipoSancao"), dict) else "",
                            "data_inicio": s.get("dataInicioSancao", ""),
                            "data_fim": s.get("dataFimSancao", ""),
                        })
    except Exception as e:
        logger.warning("Portal sancoes failed: %s", e)

    # Filter by CNPJ/name if provided (API sometimes ignores filters)
    if cnpj:
        clean_cnpj = cnpj.replace(".", "").replace("/", "").replace("-", "")
        results = [s for s in results if clean_cnpj in str(s.get("cnpj_cpf", "")).replace(".", "").replace("/", "").replace("-", "")]
    if nome and not cnpj:
        nome_upper = nome.upper()
        results = [s for s in results if nome_upper in str(s.get("nome", "")).upper()]

    return {
        "query": cnpj or nome,
        "sancoes": results,
        "fonte": "Portal da Transparência — CEIS + CNEP (Empresas Inidôneas e Punidas)",
        "dica": "Empresa sancionada ainda ganha contratos? Isso é irregularidade grave.",
    }


# ─── DataJud (Processos Judiciais - CNJ) ──────────────────────────────

DATAJUD_API_KEY = os.environ.get("DATAJUD_API_KEY", "")
DATAJUD_BASE = "https://api-publica.datajud.cnj.jus.br"
DATAJUD_HEADERS = {
    "Authorization": f"APIKey {DATAJUD_API_KEY}",
    "Content-Type": "application/json",
}

# Map of tribunals for common searches
DATAJUD_TRIBUNAIS = {
    "STJ": "api_publica_stj",
    "TST": "api_publica_tst",
    "TSE": "api_publica_tse",
    "TRF1": "api_publica_trf1",  # DF, GO, MT, BA, MA, PI, PA, AM, RR, AP, TO, AC, RO
    "TRF2": "api_publica_trf2",  # RJ, ES
    "TRF3": "api_publica_trf3",  # SP, MS
    "TRF4": "api_publica_trf4",  # PR, SC, RS
    "TRF5": "api_publica_trf5",  # PE, CE, RN, PB, AL, SE
    "TRF6": "api_publica_trf6",  # MG
    "TJSP": "api_publica_tjsp",
    "TJRJ": "api_publica_tjrj",
    "TJMG": "api_publica_tjmg",
    "TJRS": "api_publica_tjrs",
    "TJPR": "api_publica_tjpr",
    "TJSC": "api_publica_tjsc",
    "TJBA": "api_publica_tjba",
    "TJGO": "api_publica_tjgo",
    "TJPE": "api_publica_tjpe",
    "TJCE": "api_publica_tjce",
    "TJDF": "api_publica_tjdft",
    "TJMA": "api_publica_tjma",
    "TJPA": "api_publica_tjpa",
    "TJAM": "api_publica_tjam",
    "TJMT": "api_publica_tjmt",
    "TJMS": "api_publica_tjms",
    "TJES": "api_publica_tjes",
    "TJPI": "api_publica_tjpi",
}

# UF -> TRF mapping
UF_TO_TRF = {
    "DF": "TRF1", "GO": "TRF1", "MT": "TRF1", "BA": "TRF1", "MA": "TRF1",
    "PI": "TRF1", "PA": "TRF1", "AM": "TRF1", "RR": "TRF1", "AP": "TRF1",
    "TO": "TRF1", "AC": "TRF1", "RO": "TRF1",
    "RJ": "TRF2", "ES": "TRF2",
    "SP": "TRF3", "MS": "TRF3",
    "PR": "TRF4", "SC": "TRF4", "RS": "TRF4",
    "PE": "TRF5", "CE": "TRF5", "RN": "TRF5", "PB": "TRF5", "AL": "TRF5", "SE": "TRF5",
    "MG": "TRF6",
}


async def tool_search_processos(numero_processo: str = "", nome_parte: str = "", tribunal: str = "TJSP", classe: str = "") -> dict[str, Any]:
    """Search judicial processes via DataJud (CNJ)."""
    results: list[dict[str, Any]] = []
    try:
        alias = DATAJUD_TRIBUNAIS.get(tribunal.upper(), f"api_publica_{tribunal.lower()}")
        url = f"{DATAJUD_BASE}/{alias}/_search"

        if numero_processo:
            query = {
                "query": {
                    "match": {"numeroProcesso": numero_processo.replace(".", "").replace("-", "")}
                },
                "size": 5,
            }
        elif nome_parte:
            query = {
                "query": {
                    "match": {"movimentos.complementosTabelados.descricao": nome_parte}
                },
                "size": 5,
            }
        elif classe:
            query = {
                "query": {
                    "match_phrase": {"classe.nome": classe}
                },
                "size": 5,
                "sort": [{"dataAjuizamento": {"order": "desc"}}],
            }
        else:
            query = {
                "query": {"match_all": {}},
                "size": 5,
                "sort": [{"dataAjuizamento": {"order": "desc"}}],
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=query, headers=DATAJUD_HEADERS)
            if resp.status_code == 200:
                hits = resp.json().get("hits", {}).get("hits", [])
                for hit in hits[:5]:
                    src = hit.get("_source", {})
                    movs = src.get("movimentos", [])
                    last_mov = movs[0] if movs else {}
                    results.append({
                        "numero": src.get("numeroProcesso", ""),
                        "classe": src.get("classe", {}).get("nome", ""),
                        "assuntos": [a.get("nome", "") for a in src.get("assuntos", [])[:3]],
                        "orgao_julgador": src.get("orgaoJulgador", {}).get("nome", ""),
                        "data_ajuizamento": src.get("dataAjuizamento", ""),
                        "grau": src.get("grau", ""),
                        "nivel_sigilo": src.get("nivelSigilo", 0),
                        "ultimo_movimento": last_mov.get("nome", ""),
                        "data_ultimo_movimento": last_mov.get("dataHora", ""),
                    })
            else:
                logger.warning("DataJud HTTP %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.warning("DataJud search failed: %s", e)

    return {
        "query": numero_processo or nome_parte or classe or "recentes",
        "tribunal": tribunal,
        "processos": results,
        "fonte": f"DataJud (CNJ) — {tribunal}",
        "tribunais_disponiveis": list(DATAJUD_TRIBUNAIS.keys())[:10],
        "dica": "Use número do processo para busca exata. Busque por classe: 'Recuperação Judicial', 'Ação de Improbidade', 'Execução Fiscal'.",
    }
