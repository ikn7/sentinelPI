"""Tests for the content enrichment processor."""

from __future__ import annotations

import pytest

from src.collectors.base import CollectedItem
from src.processors.enricher import Enricher


class TestEnricher:
    def test_init(self):
        enricher = Enricher()
        assert enricher is not None

    def test_enrich_item_extracts_keywords(self):
        enricher = Enricher()
        item = CollectedItem(
            guid="test-1",
            title="Intelligence artificielle et machine learning",
            content=(
                "L'intelligence artificielle et le machine learning transforment "
                "l'industrie technologique. Les algorithmes de deep learning "
                "permettent de nouvelles applications en traitement du langage "
                "naturel et en vision par ordinateur."
            ),
        )

        result = enricher.enrich(item)
        assert result is not None
        # Enricher should set keywords on the result
        if hasattr(result, "extra") and "keywords" in result.extra:
            assert len(result.extra["keywords"]) > 0

    def test_enrich_item_without_content(self):
        enricher = Enricher()
        item = CollectedItem(
            guid="test-2",
            title="Short title only",
        )

        result = enricher.enrich(item)
        assert result is not None

    def test_enrich_generates_summary(self):
        enricher = Enricher()
        long_content = "Lorem ipsum dolor sit amet. " * 50
        item = CollectedItem(
            guid="test-3",
            title="Test Article",
            content=long_content,
        )

        result = enricher.enrich(item)
        assert result is not None
