from __future__ import annotations

from typing import Any


def get_person_settings() -> dict[str, Any]:
    """Return splink 4 settings dict for Person entity matching.

    Fields compared:
    - name: jaro-winkler similarity at multiple thresholds
    - cpf: exact match
    - birth_date: exact match
    """
    try:
        import splink.comparison_library as cl  # type: ignore[import-not-found]
        from splink import SettingsCreator  # type: ignore[import-not-found,unused-ignore]
    except ImportError as exc:
        raise ImportError(
            "splink is required for entity resolution. "
            "Install it with: pip install 'bracc-etl[resolution]'"
        ) from exc

    creator = SettingsCreator(
        link_type="dedupe_only",
        comparisons=[
            cl.JaroWinklerAtThresholds("name", score_threshold_or_thresholds=[0.9, 0.8]),
            cl.ExactMatch("cpf"),
            cl.ExactMatch("birth_date"),
        ],
        blocking_rules_to_generate_predictions=[
            "l.cpf = r.cpf",
            "l.name = r.name",
        ],
        retain_matching_columns=True,
        retain_intermediate_calculation_columns=False,
    )
    result: dict[str, Any] = creator.get_settings("duckdb").as_dict()
    return result
