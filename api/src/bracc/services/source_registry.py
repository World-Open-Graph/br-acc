import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceRegistryEntry:
    id: str
    name: str
    category: str
    tier: str
    status: str
    implementation_state: str
    load_state: str
    frequency: str
    in_universe_v1: bool
    primary_url: str
    pipeline_id: str
    owner_agent: str
    access_mode: str
    public_access_mode: str
    discovery_status: str
    last_seen_url: str
    cadence_expected: str
    cadence_observed: str
    quality_status: str
    notes: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "tier": self.tier,
            "status": self.status,
            "implementation_state": self.implementation_state,
            "load_state": self.load_state,
            "frequency": self.frequency,
            "in_universe_v1": self.in_universe_v1,
            "primary_url": self.primary_url,
            "pipeline_id": self.pipeline_id,
            "owner_agent": self.owner_agent,
            "access_mode": self.access_mode,
            "public_access_mode": self.public_access_mode,
            "discovery_status": self.discovery_status,
            "last_seen_url": self.last_seen_url,
            "cadence_expected": self.cadence_expected,
            "cadence_observed": self.cadence_observed,
            "quality_status": self.quality_status,
            "notes": self.notes,
        }


def _str_to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _default_registry_path() -> Path:
    # .../api/src/bracc/services/source_registry.py -> repo root is parents[4]
    return Path(__file__).resolve().parents[4] / "docs" / "source_registry_br_v1.csv"


def get_registry_path() -> Path:
    """Return the source registry CSV path from env or default.

    BRACC_SOURCE_REGISTRY_PATH must be set only by administrators in a trusted
    environment; do not allow untrusted users or processes to set it.
    """
    configured = os.getenv("BRACC_SOURCE_REGISTRY_PATH", "").strip()
    return Path(configured) if configured else _default_registry_path()


def load_source_registry() -> list[SourceRegistryEntry]:
    registry_path = get_registry_path()
    if not registry_path.exists():
        return []

    entries: list[SourceRegistryEntry] = []
    with registry_path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            entries.append(
                SourceRegistryEntry(
                    id=(row.get("source_id") or "").strip(),
                    name=(row.get("name") or "").strip(),
                    category=(row.get("category") or "").strip(),
                    tier=(row.get("tier") or "").strip(),
                    status=(row.get("status") or "").strip(),
                    implementation_state=(row.get("implementation_state") or "").strip(),
                    load_state=(row.get("load_state") or "").strip(),
                    frequency=(row.get("frequency") or "").strip(),
                    in_universe_v1=_str_to_bool(row.get("in_universe_v1") or ""),
                    primary_url=(row.get("primary_url") or "").strip(),
                    pipeline_id=(row.get("pipeline_id") or "").strip(),
                    owner_agent=(row.get("owner_agent") or "").strip(),
                    access_mode=(row.get("access_mode") or "").strip(),
                    public_access_mode=(
                        (row.get("public_access_mode") or row.get("access_mode") or "").strip()
                    ),
                    discovery_status=(
                        (row.get("discovery_status") or "discovered").strip()
                    ),
                    last_seen_url=(
                        (row.get("last_seen_url") or row.get("primary_url") or "").strip()
                    ),
                    cadence_expected=(
                        (row.get("cadence_expected") or row.get("frequency") or "").strip()
                    ),
                    cadence_observed=(row.get("cadence_observed") or "").strip(),
                    quality_status=((row.get("quality_status") or row.get("status") or "").strip()),
                    notes=(row.get("notes") or "").strip(),
                )
            )

    entries.sort(key=lambda entry: entry.id)
    return entries


def source_registry_summary(entries: list[SourceRegistryEntry]) -> dict[str, int]:
    universe_v1 = [entry for entry in entries if entry.in_universe_v1]
    implemented = [
        entry for entry in universe_v1 if entry.implementation_state == "implemented"
    ]
    loaded = [entry for entry in universe_v1 if entry.load_state == "loaded"]
    stale = [entry for entry in universe_v1 if entry.status == "stale"]
    blocked = [entry for entry in universe_v1 if entry.status == "blocked_external"]
    quality_fail = [entry for entry in universe_v1 if entry.status == "quality_fail"]
    healthy = [entry for entry in universe_v1 if entry.status == "loaded"]
    discovered_uningested = [
        entry
        for entry in universe_v1
        if entry.discovery_status == "discovered_uningested"
        or entry.implementation_state == "not_implemented"
    ]

    return {
        "universe_v1_sources": len(universe_v1),
        "implemented_sources": len(implemented),
        "loaded_sources": len(loaded),
        "healthy_sources": len(healthy),
        "stale_sources": len(stale),
        "blocked_external_sources": len(blocked),
        "quality_fail_sources": len(quality_fail),
        "discovered_uningested_sources": len(discovered_uningested),
    }
