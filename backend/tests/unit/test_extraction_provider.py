"""Unit tests for extraction provider (mock)."""

import os

os.environ["USE_MOCK_LLM"] = "true"

from app.services.extraction.provider import get_provider, MockExtractionProvider, USE_MOCK


def test_mock_provider_active():
    assert USE_MOCK is True
    provider = get_provider()
    assert isinstance(provider, MockExtractionProvider)


def test_mock_extract_returns_dict():
    provider = MockExtractionProvider()
    text = "INV-2026-001\nIndustrial Motor Qty 100 Rate 52000 Total 5200000"
    raw = provider.extract(text)
    assert "document_type" in raw
    assert "line_items" in raw
    assert isinstance(raw["line_items"], list)
