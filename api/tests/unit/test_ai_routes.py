"""Tests for AI routes and services.

Covers:
- Entity analysis endpoint
- Web enrichment endpoint
- Investigative scores endpoint
- Timeline generation endpoint
- Source verification endpoint
- Suspicion score endpoint
- PDF dossier generation
- Alert subscription system
- TTS/STT endpoints
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from bracc.config import settings


def _mock_record(data: dict[str, object]) -> MagicMock:
    """Create a mock Neo4j record."""
    record = MagicMock()
    record.__getitem__ = lambda self, key: data[key]
    record.__contains__ = lambda self, key: key in data
    record.keys.return_value = list(data.keys())
    return record


def _fake_result(records: list[MagicMock]) -> AsyncMock:
    """Create a mock Neo4j result."""
    result = AsyncMock()

    async def _iter(self: object) -> object:  # noqa: ANN001
        for r in records:
            yield r

    result.__aiter__ = _iter
    result.single = AsyncMock(return_value=records[0] if records else None)
    return result


def _setup_mock_session(driver: MagicMock, records: list[MagicMock]) -> AsyncMock:
    """Setup mock Neo4j session."""
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=_fake_result(records))
    driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    return mock_session


class TestAIStatus:
    """Tests for AI status endpoint."""

    @pytest.mark.anyio
    async def test_ai_status_returns_enabled_flags(self, client: AsyncClient) -> None:
        """Test that status endpoint returns correct feature flags."""
        response = await client.get("/api/v1/ai/status")
        assert response.status_code == 200
        data = response.json()
        assert "ai_enabled" in data
        assert "journalist_tools_enabled" in data
        assert "voice_enabled" in data


class TestEntityAnalysis:
    """Tests for entity analysis endpoint."""

    @pytest.mark.anyio
    async def test_analyze_entity_success(self, client: AsyncClient) -> None:
        """Test successful entity analysis."""
        from bracc.main import app

        entity_record = _mock_record({
            "e": {"name": "Test Company", "cnpj": "12.345.678/0001-90"},
            "entity_labels": ["Company"],
        })
        _setup_mock_session(app.state.neo4j_driver, [entity_record])

        response = await client.post(
            "/api/v1/ai/analyze",
            json={
                "entity_id": "test-entity-1",
                "include_relationships": True,
                "include_timeline": True,
                "include_anomalies": True,
                "lang": "pt",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "test-entity-1"
        assert "summary" in data
        assert "insights" in data
        assert "risk_level" in data
        assert "risk_score" in data

    @pytest.mark.anyio
    async def test_analyze_entity_not_found(self, client: AsyncClient) -> None:
        """Test analysis of non-existent entity."""
        from bracc.main import app

        _setup_mock_session(app.state.neo4j_driver, [])

        response = await client.post(
            "/api/v1/ai/analyze",
            json={"entity_id": "nonexistent"},
        )

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_analyze_entity_with_pep(self, client: AsyncClient) -> None:
        """Test analysis detecting PEP status."""
        from bracc.main import app

        entity_record = _mock_record({
            "e": {"name": "John Doe", "cpf": "123.456.789-00", "role": "deputado"},
            "entity_labels": ["Person"],
        })
        _setup_mock_session(app.state.neo4j_driver, [entity_record])

        response = await client.post(
            "/api/v1/ai/analyze",
            json={"entity_id": "test-person-1", "lang": "pt"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should have PEP insight
        pep_insights = [i for i in data["insights"] if i["type"] == "risk" and "PEP" in i.get("title", "")]
        assert len(pep_insights) > 0


class TestWebEnrichment:
    """Tests for web enrichment endpoint."""

    @pytest.mark.anyio
    async def test_enrich_entity_success(self, client: AsyncClient) -> None:
        """Test successful web enrichment."""
        from bracc.main import app

        entity_record = _mock_record({
            "e": {"name": "Test Company", "cnpj": "12.345.678/0001-90"},
            "entity_labels": ["Company"],
        })
        _setup_mock_session(app.state.neo4j_driver, [entity_record])

        response = await client.post(
            "/api/v1/ai/enrich",
            json={
                "entity_id": "test-entity-1",
                "sources": ["news"],
                "max_pages": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "test-entity-1"
        assert "results" in data
        assert "total_results" in data


class TestSuspicionScore:
    """Tests for suspicion score endpoint."""

    @pytest.mark.anyio
    async def test_suspicion_score_success(self, client: AsyncClient) -> None:
        """Test successful suspicion score retrieval."""
        from bracc.main import app

        entity_record = _mock_record({
            "e": {"name": "Test Company", "cnpj": "12.345.678/0001-90"},
            "entity_labels": ["Company"],
            "connection_count": 10,
            "source_count": 3,
            "financial_volume": 50000.0,
        })
        _setup_mock_session(app.state.neo4j_driver, [entity_record])

        response = await client.get(
            "/api/v1/ai/entity/test-entity-1/score",
            params={"include_explanations": True, "lang": "pt"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "test-entity-1"
        assert "suspicion_score" in data
        assert "risk_level" in data
        assert "confidence" in data
        assert "factors" in data

    @pytest.mark.anyio
    async def test_suspicion_score_with_explanations(self, client: AsyncClient) -> None:
        """Test suspicion score with detailed explanations."""
        from bracc.main import app

        entity_record = _mock_record({
            "e": {
                "name": "Risky Company",
                "cnpj": "12.345.678/0001-90",
                "sanction_count": 2,
                "is_pep": True,
            },
            "entity_labels": ["Company"],
            "connection_count": 50,
            "source_count": 5,
            "financial_volume": 1000000.0,
        })
        _setup_mock_session(app.state.neo4j_driver, [entity_record])

        response = await client.get(
            "/api/v1/ai/entity/test-entity-1/score",
            params={"include_explanations": True, "lang": "pt"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "factors" in data
        factors = data["factors"]
        assert len(factors) > 0
        # Check for factor structure
        for factor in factors:
            assert "name" in factor
            assert "score" in factor
            assert "weight" in factor
            assert "explanation" in factor
            assert "formatted_explanation" in factor

    @pytest.mark.anyio
    async def test_suspicion_score_entity_not_found(self, client: AsyncClient) -> None:
        """Test suspicion score for non-existent entity."""
        from bracc.main import app

        _setup_mock_session(app.state.neo4j_driver, [])

        response = await client.get("/api/v1/ai/entity/nonexistent/score")

        assert response.status_code == 200  # Returns null score, not error
        data = response.json()
        assert data["suspicion_score"] is None
        assert "null_reason" in data


class TestInvestigativeScores:
    """Tests for investigative scores endpoint."""

    @pytest.mark.anyio
    async def test_investigative_scores_success(self, client: AsyncClient) -> None:
        """Test successful investigative score calculation."""
        from bracc.main import app

        investigation_record = _mock_record({
            "id": "inv-1",
            "title": "Test Investigation",
            "entity_ids": ["entity-1", "entity-2"],
        })
        entity1_record = _mock_record({
            "e": {"name": "Entity 1"},
            "entity_labels": ["Company"],
        })
        entity2_record = _mock_record({
            "e": {"name": "Entity 2", "is_pep": True},
            "entity_labels": ["Person"],
        })

        # Setup mock to return different results for different queries
        mock_session = AsyncMock()
        results = [
            _fake_result([investigation_record]),
            _fake_result([entity1_record]),
            _fake_result([]),  # node_degree for entity-1
            _fake_result([entity2_record]),
            _fake_result([]),  # node_degree for entity-2
        ]
        mock_session.run = AsyncMock(side_effect=results)
        app.state.neo4j_driver.session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )

        response = await client.get("/api/v1/ai/score/inv-1")

        assert response.status_code == 200
        data = response.json()
        assert data["investigation_id"] == "inv-1"
        assert "overall_risk_score" in data
        assert "entity_scores" in data
        assert "recommended_actions" in data


class TestTimelineGeneration:
    """Tests for timeline generation endpoint."""

    @pytest.mark.anyio
    async def test_generate_timeline_success(self, client: AsyncClient) -> None:
        """Test successful timeline generation."""
        from bracc.main import app

        timeline_record = _mock_record({
            "id": "event-1",
            "date": "2024-01-15",
            "label": "Contract Award",
            "type": "Contract",
            "source": "transparencia",
        })
        _setup_mock_session(app.state.neo4j_driver, [timeline_record])

        response = await client.post(
            "/api/v1/ai/timeline",
            json={
                "entity_id": "test-entity-1",
                "include_ai_insights": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "test-entity-1"
        assert "events" in data
        assert "total" in data

    @pytest.mark.anyio
    async def test_generate_timeline_with_date_range(self, client: AsyncClient) -> None:
        """Test timeline generation with date filters."""
        from bracc.main import app

        _setup_mock_session(app.state.neo4j_driver, [])

        response = await client.post(
            "/api/v1/ai/timeline",
            json={
                "entity_id": "test-entity-1",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )

        assert response.status_code == 200


class TestSourceVerification:
    """Tests for source verification endpoint."""

    @pytest.mark.anyio
    async def test_verify_sources_success(self, client: AsyncClient) -> None:
        """Test successful source verification."""
        from bracc.main import app

        entity_record = _mock_record({
            "e": {"name": "Test Entity"},
            "entity_labels": ["Company"],
        })
        _setup_mock_session(app.state.neo4j_driver, [entity_record])

        response = await client.get(
            "/api/v1/journalist/sources/test-entity-1",
            params={"urls": "https://example.com/news1,https://example.com/news2"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "test-entity-1"
        assert "verified_sources" in data
        assert "total_verified" in data

    @pytest.mark.anyio
    async def test_verify_sources_no_urls(self, client: AsyncClient) -> None:
        """Test source verification with no URLs."""
        response = await client.get(
            "/api/v1/journalist/sources/test-entity-1",
            params={"urls": ""},
        )

        assert response.status_code == 400


class TestPDFDossier:
    """Tests for PDF dossier generation endpoint."""

    @pytest.mark.anyio
    async def test_generate_dossier_success(self, client: AsyncClient) -> None:
        """Test successful PDF dossier generation."""
        from bracc.main import app

        entity_record = _mock_record({
            "e": {"name": "Test Company", "cnpj": "12.345.678/0001-90"},
            "entity_labels": ["Company"],
        })
        _setup_mock_session(app.state.neo4j_driver, [entity_record])

        response = await client.get("/api/v1/journalist/entity/test-entity-1/dossier")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "content-disposition" in response.headers

    @pytest.mark.anyio
    async def test_generate_dossier_entity_not_found(self, client: AsyncClient) -> None:
        """Test dossier generation for non-existent entity."""
        from bracc.main import app

        _setup_mock_session(app.state.neo4j_driver, [])

        response = await client.get("/api/v1/journalist/entity/nonexistent/dossier")

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_generate_dossier_with_lang(self, client: AsyncClient) -> None:
        """Test dossier generation in English."""
        from bracc.main import app

        entity_record = _mock_record({
            "e": {"name": "Test Company", "cnpj": "12.345.678/0001-90"},
            "entity_labels": ["Company"],
        })
        _setup_mock_session(app.state.neo4j_driver, [entity_record])

        response = await client.get(
            "/api/v1/journalist/entity/test-entity-1/dossier",
            params={"lang": "en"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"


class TestAlertSubscriptions:
    """Tests for alert subscription system."""

    @pytest.mark.anyio
    async def test_subscribe_to_alerts_success(self, client: AsyncClient) -> None:
        """Test successful alert subscription."""
        response = await client.post(
            "/api/v1/journalist/alerts/subscribe",
            params={
                "entity_id": "test-entity-1",
                "email": "test@example.com",
                "alert_types": "score_change,new_data",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert "subscription_id" in data
        assert data["entity_id"] == "test-entity-1"
        assert data["email"] == "test@example.com"

    @pytest.mark.anyio
    async def test_subscribe_idempotent(self, client: AsyncClient) -> None:
        """Test that duplicate subscriptions are handled idempotently."""
        # First subscription
        response1 = await client.post(
            "/api/v1/journalist/alerts/subscribe",
            params={
                "entity_id": "test-entity-1",
                "email": "test@example.com",
                "alert_types": "score_change",
            },
        )

        assert response1.status_code == 200
        data1 = response1.json()
        sub_id = data1["subscription_id"]

        # Second identical subscription
        response2 = await client.post(
            "/api/v1/journalist/alerts/subscribe",
            params={
                "entity_id": "test-entity-1",
                "email": "test@example.com",
                "alert_types": "score_change",
            },
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["status"] == "already_exists"
        assert data2["subscription_id"] == sub_id

    @pytest.mark.anyio
    async def test_unsubscribe_success(self, client: AsyncClient) -> None:
        """Test successful unsubscription."""
        # First subscribe
        subscribe_response = await client.post(
            "/api/v1/journalist/alerts/subscribe",
            params={
                "entity_id": "test-entity-1",
                "email": "test@example.com",
            },
        )

        sub_id = subscribe_response.json()["subscription_id"]

        # Then unsubscribe
        response = await client.delete(f"/api/v1/journalist/alerts/unsubscribe/{sub_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["subscription_id"] == sub_id

    @pytest.mark.anyio
    async def test_unsubscribe_not_found(self, client: AsyncClient) -> None:
        """Test unsubscription with invalid ID."""
        response = await client.delete(
            "/api/v1/journalist/alerts/unsubscribe/invalid-id"
        )

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_list_subscriptions(self, client: AsyncClient) -> None:
        """Test listing subscriptions."""
        # Create a subscription first
        await client.post(
            "/api/v1/journalist/alerts/subscribe",
            params={
                "entity_id": "test-entity-1",
                "email": "test@example.com",
            },
        )

        # List all subscriptions
        response = await client.get("/api/v1/journalist/alerts/subscriptions")

        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.anyio
    async def test_list_subscriptions_filtered(self, client: AsyncClient) -> None:
        """Test listing subscriptions with filters."""
        # Create subscriptions
        await client.post(
            "/api/v1/journalist/alerts/subscribe",
            params={
                "entity_id": "test-entity-1",
                "email": "user1@example.com",
            },
        )

        # Filter by email
        response = await client.get(
            "/api/v1/journalist/alerts/subscriptions",
            params={"email": "user1@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        for sub in data["subscriptions"]:
            assert sub["email"] == "user1@example.com"


class TestVoiceEndpoints:
    """Tests for voice TTS/STT endpoints."""

    @pytest.mark.anyio
    async def test_tts_disabled_by_default(self, client: AsyncClient) -> None:
        """Test that TTS returns 503 when voice is disabled."""
        # Ensure voice is disabled
        original_value = settings.voice_enabled
        settings.voice_enabled = False

        try:
            response = await client.post(
                "/api/v1/voice/tts",
                json={"text": "Hello world"},
            )

            assert response.status_code == 503
            assert "not enabled" in response.json()["detail"].lower()
        finally:
            settings.voice_enabled = original_value

    @pytest.mark.anyio
    async def test_stt_disabled_by_default(self, client: AsyncClient) -> None:
        """Test that STT returns 503 when voice is disabled."""
        original_value = settings.voice_enabled
        settings.voice_enabled = False

        try:
            response = await client.post(
                "/api/v1/voice/stt",
                json={"audio_base64": "dGVzdA=="},
            )

            assert response.status_code == 503
        finally:
            settings.voice_enabled = original_value

    @pytest.mark.anyio
    async def test_tts_validation(self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test TTS input validation."""
        monkeypatch.setattr(settings, "voice_enabled", True)
        monkeypatch.setattr(settings, "ai_provider_api_key", "")

        response = await client.post(
            "/api/v1/voice/tts",
            json={"text": "Test", "speed": 5.0},  # Invalid speed
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.anyio
    async def test_stt_validation(self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test STT input validation."""
        monkeypatch.setattr(settings, "voice_enabled", True)

        response = await client.post(
            "/api/v1/voice/stt",
            json={"audio_base64": "not-valid-base64!!!"},
        )

        # Should fail on base64 decode or API call
        assert response.status_code in [400, 422, 500, 503]


class TestScoringService:
    """Tests for scoring service functions."""

    @pytest.mark.anyio
    async def test_suspicion_score_factors(self) -> None:
        """Test that suspicion score factors are calculated correctly."""
        from bracc.services.scoring_service import ScoreFactor

        factor = ScoreFactor(
            name="test_factor",
            score=50.0,
            weight=0.5,
            explanation="Test explanation",
            evidence=["evidence1"],
            sources=["source1"],
        )

        assert factor.weighted_score == 25.0  # 50 * 0.5

    def test_risk_level_thresholds(self) -> None:
        """Test risk level determination."""
        from bracc.services.scoring_service import _determine_risk_level

        assert _determine_risk_level(85) == "critical"
        assert _determine_risk_level(70) == "high"
        assert _determine_risk_level(50) == "medium"
        assert _determine_risk_level(30) == "low"
        assert _determine_risk_level(10) == "minimal"

    def test_confidence_calculation(self) -> None:
        """Test confidence calculation."""
        from bracc.services.scoring_service import (
            ScoreFactor,
            _calculate_confidence,
        )

        # Factors with evidence
        factors = [
            ScoreFactor(
                name="f1",
                score=50.0,
                weight=0.5,
                evidence=["e1"],
                sources=["s1"],
            ),
            ScoreFactor(
                name="f2",
                score=30.0,
                weight=0.5,
                evidence=["e2"],
                sources=["s2"],
            ),
        ]

        confidence = _calculate_confidence(factors)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be high with evidence

    def test_format_factor_explanation_pt(self) -> None:
        """Test Portuguese explanation formatting."""
        from bracc.services.scoring_service import (
            ScoreFactor,
            format_factor_explanation,
        )

        factor = ScoreFactor(
            name="sanctions",
            score=80.0,
            weight=0.25,
            explanation="Entity has sanctions",
            evidence=["CEIS record"],
            sources=["ceis"],
        )

        formatted = format_factor_explanation(factor, "pt")
        assert "sanctions" in formatted
        assert "80.0" in formatted or "80,0" in formatted
        assert "25%" in formatted or "0.25" in formatted

    def test_format_factor_explanation_en(self) -> None:
        """Test English explanation formatting."""
        from bracc.services.scoring_service import (
            ScoreFactor,
            format_factor_explanation,
        )

        factor = ScoreFactor(
            name="sanctions",
            score=80.0,
            weight=0.25,
            explanation="Entity has sanctions",
            evidence=["CEIS record"],
            sources=["ceis"],
        )

        formatted = format_factor_explanation(factor, "en")
        assert "sanctions" in formatted
        assert "80.0" in formatted
        assert "weight" in formatted.lower()


class TestCache:
    """Tests for AI query caching."""

    @pytest.mark.anyio
    async def test_cache_operations(self) -> None:
        """Test basic cache operations."""
        from bracc.services.ai_service import QueryCache, CacheEntry
        from datetime import datetime, timedelta, timezone

        cache = QueryCache(ttl_seconds=3600, max_size=100)

        # Test set and get
        await cache.set("op1", {"key": "value"}, {"result": "data"}, ["source1"])

        result = await cache.get("op1", {"key": "value"})
        assert result == {"result": "data"}

        # Test non-existent key
        result = await cache.get("op1", {"key": "other"})
        assert result is None

    @pytest.mark.anyio
    async def test_cache_expiration(self) -> None:
        """Test cache entry expiration."""
        from bracc.services.ai_service import QueryCache

        cache = QueryCache(ttl_seconds=0, max_size=100)  # Immediate expiration

        await cache.set("op1", {"key": "value"}, {"result": "data"})

        # Should be expired immediately
        result = await cache.get("op1", {"key": "value"})
        assert result is None

    @pytest.mark.anyio
    async def test_cache_invalidation(self) -> None:
        """Test cache invalidation."""
        from bracc.services.ai_service import QueryCache

        cache = QueryCache(ttl_seconds=3600, max_size=100)

        await cache.set("op1", {"key": "value1"}, {"result": "data1"})
        await cache.set("op1", {"key": "value2"}, {"result": "data2"})
        await cache.set("op2", {"key": "value"}, {"result": "data3"})

        # Invalidate specific operation
        count = await cache.invalidate("op1")
        assert count == 2

        # Check op2 still exists
        result = await cache.get("op2", {"key": "value"})
        assert result == {"result": "data3"}


class TestAnomalyDetection:
    """Tests for anomaly detection with explanations."""

    def test_detect_high_connectivity_anomaly(self) -> None:
        """Test detection of high connectivity anomaly."""
        from bracc.services.ai_service import _detect_anomalies_with_explanation

        entity_data = {"name": "Test Entity"}
        relationships = []
        degree = 75  # High connectivity

        anomalies = _detect_anomalies_with_explanation(
            entity_data, relationships, degree, "pt"
        )

        assert len(anomalies) > 0
        high_conn = [a for a in anomalies if a.anomaly_type == "high_connectivity"]
        assert len(high_conn) == 1
        assert high_conn[0].is_anomaly
        assert "75" in high_conn[0].why_explanation
        assert len(high_conn[0].contributing_factors) > 0
        assert len(high_conn[0].recommended_actions) > 0

    def test_detect_temporal_clustering(self) -> None:
        """Test detection of temporal clustering anomaly."""
        from bracc.services.ai_service import _detect_anomalies_with_explanation

        entity_data = {"name": "Test Entity"}
        relationships = [
            {"timestamp": "2024-01-01"},
            {"timestamp": "2024-01-02"},
            {"timestamp": "2024-01-03"},
            {"timestamp": "2024-01-04"},
            {"timestamp": "2024-01-05"},
        ]
        degree = 10

        anomalies = _detect_anomalies_with_explanation(
            entity_data, relationships, degree, "pt"
        )

        temporal = [a for a in anomalies if a.anomaly_type == "temporal_clustering"]
        assert len(temporal) == 1
        assert temporal[0].is_anomaly

    def test_detect_cross_source_presence(self) -> None:
        """Test detection of cross-source presence."""
        from bracc.services.ai_service import _detect_anomalies_with_explanation

        entity_data = {
            "name": "Test Entity",
            "source": ["cnpj", "tse", "transparencia", "ibama", "cvm"],
        }
        relationships = []
        degree = 10

        anomalies = _detect_anomalies_with_explanation(
            entity_data, relationships, degree, "pt"
        )

        cross_source = [a for a in anomalies if a.anomaly_type == "cross_source_presence"]
        assert len(cross_source) == 1
        assert cross_source[0].is_anomaly

    def test_english_explanations(self) -> None:
        """Test that English explanations are generated correctly."""
        from bracc.services.ai_service import _detect_anomalies_with_explanation

        entity_data = {"name": "Test Entity"}
        relationships = []
        degree = 75

        anomalies = _detect_anomalies_with_explanation(
            entity_data, relationships, degree, "en"
        )

        assert len(anomalies) > 0
        # Check English content
        assert "connections" in anomalies[0].why_explanation.lower()


class TestVoiceService:
    """Tests for voice service functions."""

    def test_detect_language_portuguese(self) -> None:
        """Test Portuguese language detection."""
        from bracc.services.voice_service import _detect_language

        text = "Esta é uma frase em português com acentuação."
        assert _detect_language(text) == "pt"

    def test_detect_language_english(self) -> None:
        """Test English language detection."""
        from bracc.services.voice_service import _detect_language

        text = "This is a sentence in English with some words."
        assert _detect_language(text) == "en"

    def test_make_concise_short_text(self) -> None:
        """Test concise generation with short text."""
        from bracc.services.voice_service import _make_concise

        text = "Short text."
        result = _make_concise(text, max_length=1000)
        assert result == text

    def test_make_concise_long_text(self) -> None:
        """Test concise generation with long text."""
        from bracc.services.voice_service import _make_concise

        text = "First sentence. Second sentence. Third sentence. " * 100
        result = _make_concise(text, max_length=100)
        assert len(result) <= 103  # Allow for "..."
        assert result.endswith("...") or len(result) < 100

    def test_estimate_confidence(self) -> None:
        """Test confidence estimation."""
        from bracc.services.voice_service import _estimate_confidence

        # Good quality text
        confidence = _estimate_confidence("This is a well formed sentence.")
        assert confidence > 0.5

        # Empty text
        confidence = _estimate_confidence("")
        assert confidence == 0.0

        # Text with uncertain markers
        confidence = _estimate_confidence("Um... I think... uh... maybe?")
        assert confidence < 0.85  # Should be reduced

    def test_create_summary_pt(self) -> None:
        """Test Portuguese summary creation."""
        from bracc.services.voice_service import _create_summary

        text = "Primeira parte do texto. Segunda parte. Terceira parte."
        summary = _create_summary(text, 100, "pt")

        assert summary.startswith("Resumo")
        assert "Primeira" in summary

    def test_create_summary_en(self) -> None:
        """Test English summary creation."""
        from bracc.services.voice_service import _create_summary

        text = "First part of text. Second part. Third part."
        summary = _create_summary(text, 100, "en")

        assert summary.startswith("Summary")
        assert "First" in summary
