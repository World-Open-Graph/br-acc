from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import CliRunner

if TYPE_CHECKING:
    from types import ModuleType


def _load_script_module(filename: str, module_name: str) -> ModuleType:
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    script_path = scripts_dir / filename
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_download_cnpj_bq_writes_manifest_on_success(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_script_module("download_cnpj_bq.py", "download_cnpj_bq_ok")

    def _fake_download(*args, **kwargs):  # type: ignore[no-untyped-def]
        table = args[3]
        out = args[5]
        dest = out / f"{table}_history.csv"
        dest.write_text("data,cnpj_basico\n2024-01-01,00000000\n", encoding="utf-8")
        return {
            "table": table,
            "output_file": dest.name,
            "status": "ok",
            "rows": 1,
            "snapshot_min": "2024-01-01",
            "snapshot_max": "2024-01-01",
            "checksum": "abc",
            "started_at": "2026-02-28T00:00:00+00:00",
            "finished_at": "2026-02-28T00:00:01+00:00",
            "error": "",
        }

    monkeypatch.setattr(module, "_download_table", _fake_download)
    monkeypatch.setattr(module, "_run_bigquery_precheck", lambda **kw: None)
    runner = CliRunner()
    result = runner.invoke(
        module.main,
        [
            "--billing-project",
            "icarus-corruptos",
            "--output-dir",
            str(tmp_path),
            "--dataset",
            "basedosdados.br_me_cnpj",
        ],
    )

    assert result.exit_code == 0
    manifest = json.loads((tmp_path / "download_manifest.json").read_text(encoding="utf-8"))
    assert manifest["summary"]["ok"] == 3
    assert manifest["summary"]["failed"] == 0
    assert manifest["summary"]["snapshot_max"] == "2024-01-01"


def test_download_cnpj_bq_fails_closed_when_table_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_script_module("download_cnpj_bq.py", "download_cnpj_bq_fail")

    def _fail_on_socios(*args, **kwargs):  # type: ignore[no-untyped-def]
        table = args[3]
        if table == "socios":
            raise RuntimeError("missing snapshot metadata")
        out = args[5]
        dest = out / f"{table}_history.csv"
        dest.write_text("data,cnpj_basico\n2024-01-01,00000000\n", encoding="utf-8")
        return {
            "table": table,
            "output_file": dest.name,
            "status": "ok",
            "rows": 1,
            "snapshot_min": "2024-01-01",
            "snapshot_max": "2024-01-01",
            "checksum": "abc",
            "started_at": "2026-02-28T00:00:00+00:00",
            "finished_at": "2026-02-28T00:00:01+00:00",
            "error": "",
        }

    monkeypatch.setattr(module, "_download_table", _fail_on_socios)
    monkeypatch.setattr(module, "_run_bigquery_precheck", lambda **kw: None)
    runner = CliRunner()
    result = runner.invoke(
        module.main,
        [
            "--billing-project",
            "icarus-corruptos",
            "--output-dir",
            str(tmp_path),
            "--dataset",
            "basedosdados.br_me_cnpj",
        ],
    )

    assert result.exit_code != 0
    manifest = json.loads((tmp_path / "download_manifest.json").read_text(encoding="utf-8"))
    assert manifest["summary"]["failed"] == 1
    assert any(t["status"] == "failed" for t in manifest["tables"])
