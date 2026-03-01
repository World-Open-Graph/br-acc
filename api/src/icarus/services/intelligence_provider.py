from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Mapping
from importlib import import_module
from importlib.util import find_spec
from typing import TYPE_CHECKING, Any, Protocol, cast

from fastapi import HTTPException

from icarus.config import settings
from icarus.models.entity import ExposureFactor, ExposureResponse, SourceAttribution
from icarus.models.pattern import PATTERN_METADATA, PatternResult
from icarus.services.neo4j_service import execute_query, execute_query_single

if TYPE_CHECKING:
    from neo4j import AsyncDriver, AsyncSession

COMMUNITY_PATTERN_IDS = (
    "sanctioned_still_receiving",
    "debtor_contracts",
    "loan_debtor",
    "amendment_beneficiary_contracts",
)

_CNPJ_PATTERN = re.compile(r"^\d{14}$")

_PatternRunner = Callable[..., Awaitable[list[PatternResult]]]
_ComputeExposure = Callable[[Any, str], Awaitable[ExposureResponse]]


def _load_pattern_queries() -> Mapping[str, str]:
    module = import_module("icarus.services.pattern_service")
    module_any = cast("Any", module)
    return cast("Mapping[str, str]", module_any.PATTERN_QUERIES)


def _load_pattern_runner(name: str) -> _PatternRunner:
    module = import_module("icarus.services.pattern_service")
    module_any = cast("Any", module)
    return cast("_PatternRunner", getattr(module_any, name))


def _load_compute_exposure() -> _ComputeExposure:
    module = import_module("icarus.services.score_service")
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
        records = await execute_query(
            session,
            "public_patterns_company",
            {
                "company_id": company_id,
                "company_identifier": company_identifier,
                "company_identifier_formatted": company_identifier_formatted,
            },
        )

        results: list[PatternResult] = []
        for record in records:
            pid = record["pattern_id"]
            if pid not in COMMUNITY_PATTERN_IDS:
                continue
            if pattern_id != "__all__" and pid != pattern_id:
                continue
            summary = record["summary_pt"] if lang == "pt" else record["summary_en"]
            results.append(PatternResult(
                pattern_id=pid,
                pattern_name=summary,
                description=summary,
                data={
                    "company_cnpj": record["cnpj"],
                    "company_name": record["company_name"],
                    "contract_count": record["contract_count"],
                    "sanction_count": record["sanction_count"],
                    "debt_count": record["debt_count"],
                    "loan_count": record["loan_count"],
                    "amendment_count": record["amendment_count"],
                    "risk_signal": record["risk_signal"],
                    "identity_path_quality": "community_baseline",
                },
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
        find_spec("icarus.services.pattern_service") is not None
        and find_spec("icarus.services.score_service") is not None
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
