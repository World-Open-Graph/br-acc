from unittest.mock import MagicMock

from bracc_etl.base import Pipeline


class DummyPipeline(Pipeline):
    name = "dummy"
    source_id = "test"

    def __init__(self) -> None:
        super().__init__(driver=MagicMock(), data_dir="./data")
        self.extracted = False
        self.transformed = False
        self.loaded = False

    def extract(self) -> None:
        self.extracted = True

    def transform(self) -> None:
        self.transformed = True

    def load(self) -> None:
        self.loaded = True


def test_pipeline_run_executes_all_stages() -> None:
    pipeline = DummyPipeline()
    pipeline.run()
    assert pipeline.extracted
    assert pipeline.transformed
    assert pipeline.loaded
