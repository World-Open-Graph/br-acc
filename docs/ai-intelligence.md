# AI Intelligence Provider

## Overview
The AI Intelligence Provider provides enhanced AI-driven entity analysis, web enrichment, investigative scoring, and timeline generation for the br-acc graph database.

## Features

### AI Entity Analysis
- NLP-powered entity analysis
- Relationship inference using AI
- Anomaly detection in entity networks

### Web Crawling & Enrichment
- Fetch entity-related information from external sources
- News article enrichment
- Social media data aggregation
- Company registry enrichment

### Investigative Scoring
- Risk scoring for entities in investigations
- Priority ranking based on multiple factors
- Pattern-based scoring algorithms

### Journalist Tools
- Source verification
- Document search and aggregation
- Timeline generation
- Export capabilities for investigations

## Configuration

Environment variables:
- `AI_PROVIDER_API_KEY` - API key for AI service
- `AI_PROVIDER_MODEL` - Model to use (default: gpt-4)
- `WEB_CRAWL_TIMEOUT` - Timeout for web requests (default: 30s)
- `WEB_CRAWL_MAX_PAGES` - Maximum pages to crawl per entity (default: 10)
- `JOURNALIST_TOOLS_ENABLED` - Enable journalist tools (default: true)
- `VOICE_ENABLED` - Enable voice interface (default: false)
- `TTS_VOICE` - Text-to-speech voice (default: alloy)
- `STT_MODEL` - Speech-to-text model (default: whisper-1)

## API Endpoints

- `POST /api/v1/ai/analyze` - AI entity analysis
- `POST /api/v1/ai/enrich` - Web enrichment for entities
- `GET /api/v1/ai/score/{investigation_id}` - Get investigative scores
- `POST /api/v1/ai/timeline` - Generate AI-powered timelines
- `GET /api/v1/journalist/sources/{entity_id}` - Get verified sources
- `POST /api/v1/voice/tts` - Text-to-speech conversion
- `POST /api/v1/voice/stt` - Speech-to-text conversion
