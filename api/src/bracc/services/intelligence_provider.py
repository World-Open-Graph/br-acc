from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable, Mapping
from importlib import import_module
from importlib.util import find_spec
from typing import TYPE_CHECKING, Any, Protocol, cast

from fastapi import HTTPException

from bracc.config import settings
from bracc.models.entity import ExposureFactor, ExposureResponse, SourceAttribution
from bracc.models.pattern import PATTERN_METADATA, PatternResult
from bracc.services.neo4j_service import execute_query, execute_query_single

if TYPE_CHECKING:
    from neo4j import AsyncDriver, AsyncSession

COMMUNITY_PATTERN_IDS = (
    "sanctioned_still_receiving",
    "amendment_beneficiary_contracts",
    "split_contracts_below_threshold",
    "contract_concentration",
    "embargoed_receiving",
    "debtor_contracts",
    "srp_multi_org_hitchhiking",
    "inexigibility_recurrence",
)

COMMUNITY_PATTERN_QUERIES: dict[str, str] = {
    "sanctioned_still_receiving": "public_pattern_sanctioned_still_receiving",
    "amendment_beneficiary_contracts": "public_pattern_amendment_beneficiary_contracts",
    "split_contracts_below_threshold": "public_pattern_split_contracts_below_threshold",
    "contract_concentration": "public_pattern_contract_concentration",
    "embargoed_receiving": "public_pattern_embargoed_receiving",
    "debtor_contracts": "public_pattern_debtor_contracts",
    "srp_multi_org_hitchhiking": "public_pattern_srp_multi_org_hitchhiking",
    "inexigibility_recurrence": "public_pattern_inexigibility_recurrence",
}

_CNPJ_PATTERN = re.compile(r"^\d{14}$")
_PUBLIC_PATTERN_BLOCKLIST = (
    "cpf",
    "doc_",
    "person",
    "partner",
    "politician",
    "family",
    "deputy",
    "legislator",
)
logger = logging.getLogger(__name__)

_PatternRunner = Callable[..., Awaitable[list[PatternResult]]]
_ComputeExposure = Callable[[Any, str], Awaitable[ExposureResponse]]


def _load_pattern_queries() -> Mapping[str, str]:
    module = import_module("bracc.services.pattern_service")
    module_any = cast("Any", module)
    return cast("Mapping[str, str]", module_any.PATTERN_QUERIES)


def _load_pattern_runner(name: str) -> _PatternRunner:
    module = import_module("bracc.services.pattern_service")
    module_any = cast("Any", module)
    return cast("_PatternRunner", getattr(module_any, name))


def _load_compute_exposure() -> _ComputeExposure:
    module = import_module("bracc.services.score_service")
    module_any = cast("Any", module)
    return cast("_ComputeExposure", module_any.compute_exposure)


class IntelligenceProvider(Protocol):
    tier: str

    async def run_all_patterns(
        self,
        driver: AsyncDriver,
        entity_id: str | None = None,
        lang: str = "pt",
        include_probable: bool = False,
    ) -> list[PatternResult]:
        ...

    async def run_pattern(
        self,
        session: AsyncSession,
        pattern_id: str,
        entity_id: str | None = None,
        lang: str = "pt",
        include_probable: bool = False,
    ) -> list[PatternResult]:
        ...

    def list_patterns(self) -> list[dict[str, str]]:
        ...

    async def get_entity_exposure(
        self,
        session: AsyncSession,
        entity_id: str,
    ) -> ExposureResponse:
        ...

    async def get_timeline_enrichment(
        self,
        session: AsyncSession,
        entity_id: str,
    ) -> dict[str, Any]:
        ...


def _format_cnpj(digits: str) -> str:
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def _build_pattern_meta(pattern_ids: tuple[str, ...]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for pid in pattern_ids:
        meta = PATTERN_METADATA.get(pid, {})
        rows.append({
            "id": pid,
            "name_pt": meta.get("name_pt", pid),
            "name_en": meta.get("name_en", pid),
            "description_pt": meta.get("desc_pt", ""),
            "description_en": meta.get("desc_en", ""),
        })
    return rows


def _community_pattern_params(
    company_id: str,
    company_identifier: str,
    company_identifier_formatted: str,
) -> dict[str, str | int | float]:
    return {
        "company_id": company_id,
        "company_identifier": company_identifier,
        "company_identifier_formatted": company_identifier_formatted,
        "pattern_split_threshold_value": settings.pattern_split_threshold_value,
        "pattern_split_min_count": settings.pattern_split_min_count,
        "pattern_share_threshold": settings.pattern_share_threshold,
        "pattern_srp_min_orgs": settings.pattern_srp_min_orgs,
        "pattern_inexig_min_recurrence": settings.pattern_inexig_min_recurrence,
        "pattern_max_evidence_refs": settings.pattern_max_evidence_refs,
    }


def _sanitize_public_pattern_data(record: Any) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key in record:
        if key in {"pattern_id", "summary_pt", "summary_en"}:
            continue
        lower_key = str(key).lower()
        if any(token in lower_key for token in _PUBLIC_PATTERN_BLOCKLIST):
            continue
        value = record[key]
        if isinstance(value, list):
            data[key] = [str(item) for item in value if item is not None and str(item).strip()]
        else:
            data[key] = value
    return data


class CommunityIntelligenceProvider:
    tier = "community"

    def list_patterns(self) -> list[dict[str, str]]:
        return _build_pattern_meta(COMMUNITY_PATTERN_IDS)

    async def run_all_patterns(
        self,
        driver: AsyncDriver,
        entity_id: str | None = None,
        lang: str = "pt",
        include_probable: bool = False,
    ) -> list[PatternResult]:
        if not entity_id:
            return []
        async with driver.session(database=settings.neo4j_database) as session:
            return await self.run_pattern(
                session,
                pattern_id="__all__",
                entity_id=entity_id,
                lang=lang,
                include_probable=include_probable,
            )

    async def run_pattern(
        self,
        session: AsyncSession,
        pattern_id: str,
        entity_id: str | None = None,
        lang: str = "pt",
        include_probable: bool = False,
    ) -> list[PatternResult]:
        del include_probable  # community tier does not expose probable identity paths
        if not entity_id:
            return []

        company = await self._resolve_company(session, entity_id)
        if company is None:
            return []

        company_id, company_identifier, company_identifier_formatted = company
        params = _community_pattern_params(
            company_id,
            company_identifier,
            company_identifier_formatted,
        )

        pattern_ids: tuple[str, ...]
        if pattern_id == "__all__":
            pattern_ids = COMMUNITY_PATTERN_IDS
        elif pattern_id in COMMUNITY_PATTERN_QUERIES:
            pattern_ids = (pattern_id,)
        else:
            return []

        results: list[PatternResult] = []
        for pid in pattern_ids:
            try:
                records = await execute_query(
                    session,
                    COMMUNITY_PATTERN_QUERIES[pid],
                    params,
                    timeout=5,
                )
            except TimeoutError:
                logger.warning("Community pattern '%s' timed out; returning empty set", pid)
                continue
            except Exception:
                logger.exception("Community pattern '%s' failed; returning empty set", pid)
                continue
            meta = PATTERN_METADATA.get(pid, {})
            name_key = f"name_{lang}" if f"name_{lang}" in meta else "name_en"
            desc_key = f"desc_{lang}" if f"desc_{lang}" in meta else "desc_en"
            for record in records:
                data = _sanitize_public_pattern_data(record)
                raw_refs = data.get("evidence_refs", [])
                evidence_refs: list[str]
                if isinstance(raw_refs, list):
                    evidence_refs = [str(item) for item in raw_refs if str(item).strip()]
                elif raw_refs is None:
                    evidence_refs = []
                else:
                    evidence_refs = [str(raw_refs)]
                if not evidence_refs:
                    continue
                data["evidence_refs"] = evidence_refs[: settings.pattern_max_evidence_refs]
                raw_risk = data.get("risk_signal")
                try:
                    data["risk_signal"] = (
                        float(raw_risk)
                        if raw_risk is not None
                        else float(len(evidence_refs))
                    )
                except (TypeError, ValueError):
                    data["risk_signal"] = float(len(evidence_refs))
                raw_count = data.get("evidence_count")
                try:
                    data["evidence_count"] = (
                        int(raw_count)
                        if raw_count is not None
                        else len(evidence_refs)
                    )
                except (TypeError, ValueError):
                    data["evidence_count"] = len(evidence_refs)

                results.append(PatternResult(
                    pattern_id=pid,
                    pattern_name=meta.get(name_key, pid),
                    description=meta.get(desc_key, ""),
                    data=data,
                    entity_ids=[company_id],
                    sources=[SourceAttribution(database="neo4j_public")],
                    exposure_tier="public_safe",
                    intelligence_tier=self.tier,
                ))
        return results

    async def _resolve_company(
        self,
        session: AsyncSession,
        entity_id: str,
    ) -> tuple[str, str, str] | None:
        by_element = await execute_query_single(
            session,
            "entity_by_element_id",
            {"element_id": entity_id},
        )
        if by_element is not None and "Company" in by_element["entity_labels"]:
            node = by_element["e"]
            cnpj = str(node.get("cnpj", "")).strip()
            digits = re.sub(r"[.\-/]", "", cnpj)
            if _CNPJ_PATTERN.match(digits):
                return entity_id, digits, _format_cnpj(digits)

        identifier = re.sub(r"[.\-/]", "", entity_id)
        if not _CNPJ_PATTERN.match(identifier):
            return None
        return entity_id, identifier, _format_cnpj(identifier)

    async def get_entity_exposure(
        self,
        session: AsyncSession,
        entity_id: str,
    ) -> ExposureResponse:
        degree_records = await execute_query(
            session,
            "node_degree",
            {"entity_id": entity_id},
            timeout=5,
        )
        if not degree_records:
            raise HTTPException(status_code=404, detail="Entity not found")
        degree = int(degree_records[0]["degree"])
        percentile = 0.0
        if degree > 0:
            percentile = 25.0
        if degree > 5:
            percentile = 50.0
        if degree > 15:
            percentile = 75.0
        if degree > 50:
            percentile = 90.0

        factor = ExposureFactor(
            name="connections",
            value=float(degree),
            percentile=percentile,
            weight=1.0,
            sources=["neo4j_graph"],
        )
        return ExposureResponse(
            entity_id=entity_id,
            exposure_index=round(percentile, 2),
            factors=[factor],
            peer_group="community_baseline",
            peer_count=0,
            sources=[SourceAttribution(database="neo4j_public")],
            intelligence_tier=self.tier,
        )

    async def get_timeline_enrichment(
        self,
        session: AsyncSession,
        entity_id: str,
    ) -> dict[str, Any]:
        del session, entity_id
        return {}


class FullIntelligenceProvider:
    tier = "full"

    def list_patterns(self) -> list[dict[str, str]]:
        return _build_pattern_meta(tuple(_load_pattern_queries().keys()))

    async def run_all_patterns(
        self,
        driver: AsyncDriver,
        entity_id: str | None = None,
        lang: str = "pt",
        include_probable: bool = False,
    ) -> list[PatternResult]:
        run_all_patterns = _load_pattern_runner("run_all_patterns")
        results = await run_all_patterns(
            driver,
            entity_id=entity_id,
            lang=lang,
            include_probable=include_probable,
        )
        for row in results:
            row.intelligence_tier = self.tier
        return results

    async def run_pattern(
        self,
        session: AsyncSession,
        pattern_id: str,
        entity_id: str | None = None,
        lang: str = "pt",
        include_probable: bool = False,
    ) -> list[PatternResult]:
        run_pattern = _load_pattern_runner("run_pattern")
        results = await run_pattern(
            session,
            pattern_id=pattern_id,
            entity_id=entity_id,
            lang=lang,
            include_probable=include_probable,
        )
        for row in results:
            row.intelligence_tier = self.tier
        return results

    async def get_entity_exposure(
        self,
        session: AsyncSession,
        entity_id: str,
    ) -> ExposureResponse:
        compute_exposure = _load_compute_exposure()
        result = await compute_exposure(session, entity_id)
        result.intelligence_tier = self.tier
        return result

    async def get_timeline_enrichment(
        self,
        session: AsyncSession,
        entity_id: str,
    ) -> dict[str, Any]:
        del session, entity_id
        return {}


_PROVIDER_CACHE: dict[str, IntelligenceProvider] = {}


def _full_modules_available() -> bool:
    return (
        find_spec("bracc.services.pattern_service") is not None
        and find_spec("bracc.services.score_service") is not None
    )


def get_default_provider() -> IntelligenceProvider:
    tier = settings.product_tier.strip().lower()
    if tier not in {"community", "full"}:
        tier = "full"
    if tier == "full" and not _full_modules_available():
        tier = "community"
    cached = _PROVIDER_CACHE.get(tier)
    if cached is not None:
        return cached
    provider: IntelligenceProvider
    if tier == "community":
        provider = CommunityIntelligenceProvider()
    else:
        provider = FullIntelligenceProvider()
    _PROVIDER_CACHE[tier] = provider
    return provider
