from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bracc_etl.entity_resolution.config import get_person_settings

if TYPE_CHECKING:
    import pandas as pd


class PersonLinker:
    """Wraps splink to deduplicate Person records across data sources."""

    def __init__(self, db_api: Any) -> None:
        try:
            from splink import Linker
        except ImportError as exc:
            raise ImportError(
                "splink is required for entity resolution. "
                "Install it with: pip install 'bracc-etl[resolution]'"
            ) from exc

        self._linker_cls = Linker
        self._db_api = db_api
        self._linker: Any | None = None

    def train(self, df: pd.DataFrame) -> None:
        """Train the splink model on a Person DataFrame.

        Uses random sampling for u-values, then EM blocking on cpf
        (TSE-seeded) for m-values.
        """
        settings = get_person_settings()
        self._linker = self._linker_cls(
            df,
            settings,
            db_api=self._db_api,
        )
        self._linker.training.estimate_u_using_random_sampling(max_pairs=1e6)
        self._linker.training.estimate_parameters_using_expectation_maximisation(
            "l.cpf = r.cpf"
        )

    def predict(self, df: pd.DataFrame, threshold: float = 0.8) -> pd.DataFrame:
        """Return predicted duplicate links above the probability threshold."""
        if self._linker is None:
            self.train(df)
            assert self._linker is not None  # noqa: S101

        results = self._linker.inference.predict(threshold_match_probability=threshold)
        df_out: pd.DataFrame = results.as_pandas_dataframe()
        return df_out
