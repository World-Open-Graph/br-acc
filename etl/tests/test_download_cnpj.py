"""Tests for etl/scripts/download_cnpj.py — release resolution and manifest."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from types import ModuleType

import httpx
import pytest


def _load_script_module() -> ModuleType:
    """Load download_cnpj.py as a module without running it."""
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    script_path = scripts_dir / "download_cnpj.py"
    spec = importlib.util.spec_from_file_location("download_cnpj", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def mod() -> ModuleType:
    return _load_script_module()


# ---- resolve_rf_release tests ----


def test_resolve_rf_release_nextcloud_success(mod: ModuleType) -> None:
    """When Nextcloud token probe returns 200, use Nextcloud URL."""
    def _fake_head(url: str, **kwargs) -> MagicMock:  # type: ignore[no-untyped-def]
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with (
        patch.object(httpx, "head", side_effect=_fake_head),
        patch.dict("os.environ", {}, clear=False),
    ):
        result = mod.resolve_rf_release()

    assert "arquivos.receitafederal.gov.br" in result
    assert "download?path=" in result


def test_resolve_rf_release_nextcloud_env_token_priority(mod: ModuleType) -> None:
    """CNPJ_SHARE_TOKEN env var is tried before known tokens."""
    probed_urls: list[str] = []

    def _fake_head(url: str, **kwargs) -> MagicMock:  # type: ignore[no-untyped-def]
        probed_urls.append(url)
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with (
        patch.object(httpx, "head", side_effect=_fake_head),
        patch.dict("os.environ", {"CNPJ_SHARE_TOKEN": "customToken123"}, clear=False),
    ):
        result = mod.resolve_rf_release()

    # First probe should use the env token
    assert "customToken123" in probed_urls[0]
    assert "customToken123" in result


def test_resolve_rf_release_fallback_to_legacy_when_nextcloud_down(mod: ModuleType) -> None:
    """When all Nextcloud tokens fail, fall back to legacy paths."""
    def _fake_head(url: str, **kwargs) -> MagicMock:  # type: ignore[no-untyped-def]
        resp = MagicMock()
        if "arquivos.receitafederal.gov.br" in url:
            resp.status_code = 404
        elif "dados_abertos_cnpj" in url:
            resp.status_code = 200
        else:
            resp.status_code = 404
        return resp

    with (
        patch.object(httpx, "head", side_effect=_fake_head),
        patch.dict("os.environ", {}, clear=False),
    ):
        result = mod.resolve_rf_release()

    assert "dados_abertos_cnpj" in result


def test_resolve_rf_release_explicit_override_legacy(mod: ModuleType) -> None:
    """When year_month is provided and Nextcloud down, use legacy with that month."""
    def _fake_head(url: str, **kwargs) -> MagicMock:  # type: ignore[no-untyped-def]
        resp = MagicMock()
        if "arquivos.receitafederal.gov.br" in url:
            resp.status_code = 404
        else:
            resp.status_code = 200
        return resp

    with (
        patch.object(httpx, "head", side_effect=_fake_head),
        patch.dict("os.environ", {}, clear=False),
    ):
        result = mod.resolve_rf_release("2026-01")

    assert "2026-01" in result
    assert result == "https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/2026-01/"


def test_resolve_rf_release_all_fail_raises(mod: ModuleType) -> None:
    """When all candidates (Nextcloud + legacy) return 404, raise RuntimeError."""
    def _fake_head(url: str, **kwargs) -> MagicMock:  # type: ignore[no-untyped-def]
        resp = MagicMock()
        resp.status_code = 404
        return resp

    with (
        patch.object(httpx, "head", side_effect=_fake_head),
        patch.dict("os.environ", {}, clear=False),
        pytest.raises(RuntimeError, match="Could not resolve CNPJ release"),
    ):
        mod.resolve_rf_release()


def test_resolve_rf_release_legacy_flat_fallback(mod: ModuleType) -> None:
    """When Nextcloud + legacy new paths fail, fall back to legacy flat URL."""
    call_urls: list[str] = []

    def _fake_head(url: str, **kwargs) -> MagicMock:  # type: ignore[no-untyped-def]
        call_urls.append(url)
        resp = MagicMock()
        # Everything fails except legacy flat URL
        if url == "https://dadosabertos.rfb.gov.br/CNPJ/":
            resp.status_code = 200
        else:
            resp.status_code = 404
        return resp

    with (
        patch.object(httpx, "head", side_effect=_fake_head),
        patch.dict("os.environ", {}, clear=False),
    ):
        result = mod.resolve_rf_release()

    assert result == "https://dadosabertos.rfb.gov.br/CNPJ/"
    # Should have tried Nextcloud tokens + legacy new paths + legacy flat
    assert len(call_urls) >= 5  # 2 Nextcloud + 2 monthly + 1 flat


# ---- manifest test ----


def test_manifest_written_after_download(mod: ModuleType, tmp_path: Path) -> None:
    """Verify download_manifest.json is created with expected structure."""
    from click.testing import CliRunner

    # Patch resolve_rf_release to avoid HTTP calls
    def _fake_resolve(year_month: str | None = None) -> str:
        return "https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/2026-03/"

    # Patch download_file to simulate successful downloads
    def _fake_download(url: str, dest: Path, **kwargs) -> bool:  # type: ignore[no-untyped-def]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"fake-zip-content")
        return True

    # Patch extract_zip to no-op
    def _fake_extract(zip_path: Path, output_dir: Path) -> list[Path]:
        return []

    with (
        patch.object(mod, "resolve_rf_release", side_effect=_fake_resolve),
        patch.object(mod, "download_file", side_effect=_fake_download),
        patch.object(mod, "extract_zip", side_effect=_fake_extract),
    ):
        runner = CliRunner()
        result = runner.invoke(
            mod.main,
            [
                "--output-dir", str(tmp_path),
                "--files", "1",
                "--skip-extract",
            ],
        )

    assert result.exit_code == 0, result.output

    manifest_path = tmp_path / "download_manifest.json"
    assert manifest_path.exists(), f"Manifest not found. Output:\n{result.output}"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["source"] == "receita_federal_cnpj"
    assert manifest["resolved_release"] == "2026-03"
    assert manifest["base_url"] == "https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/2026-03/"
    assert "checksum" in manifest
    assert manifest["checksum"].startswith("sha256:")
    assert "started_at" in manifest
    assert "finished_at" in manifest

    # Should have reference files + main files (1 per type = 3 main + 6 reference)
    assert len(manifest["files"]) == 9
    statuses = {f["status"] for f in manifest["files"]}
    assert statuses <= {"ok", "skipped", "failed"}
