"""
Content enrichment processor for SentinelPi.

Extracts additional metadata from collected items:
- Keywords extraction
- Language detection
- Summary generation
- Entity extraction (optional)
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from src.collectors.base import CollectedItem
from src.utils.config import get_settings
from src.utils.logging import create_logger
from src.utils.parsing import clean_html

log = create_logger("processors.enricher")


# Common stop words for keyword extraction
STOP_WORDS_FR = {
    "le", "la", "les", "un", "une", "des", "de", "du", "au", "aux",
    "ce", "cette", "ces", "mon", "ton", "son", "ma", "ta", "sa",
    "mes", "tes", "ses", "notre", "votre", "leur", "nos", "vos", "leurs",
    "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles",
    "me", "te", "se", "lui", "y", "en",
    "qui", "que", "quoi", "dont", "où", "lequel", "laquelle",
    "et", "ou", "mais", "donc", "or", "ni", "car", "si", "que",
    "dans", "sur", "sous", "avec", "sans", "pour", "par", "entre",
    "vers", "chez", "contre", "depuis", "pendant", "avant", "après",
    "est", "sont", "était", "été", "être", "avoir", "fait", "faire",
    "dit", "dire", "peut", "pouvoir", "doit", "devoir", "veut", "vouloir",
    "plus", "moins", "très", "bien", "aussi", "encore", "toujours",
    "tout", "tous", "toute", "toutes", "autre", "autres", "même", "mêmes",
    "ici", "là", "alors", "ainsi", "comme", "comment", "pourquoi",
    "quand", "tant", "peu", "trop", "assez", "beaucoup",
    "celui", "celle", "ceux", "celles", "ceci", "cela", "ça",
    "pas", "ne", "non", "oui", "si",
}

STOP_WORDS_EN = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can",
    "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "he", "she", "him", "her", "his", "hers", "we", "us", "our", "ours",
    "you", "your", "yours", "i", "me", "my", "mine",
    "who", "what", "which", "when", "where", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "not", "only", "own", "same", "so", "than",
    "too", "very", "just", "also", "now", "here", "there", "then",
    "if", "because", "while", "although", "though", "after", "before",
    "about", "into", "through", "during", "without", "between", "under",
    "again", "further", "once", "any", "over", "down", "up", "out",
}

ALL_STOP_WORDS = STOP_WORDS_FR | STOP_WORDS_EN


@dataclass
class EnrichmentResult:
    """Result of enrichment processing."""

    keywords: list[str]
    language: str | None
    summary: str | None
    sentiment: str | None
    sentiment_score: float | None
    word_count: int
    reading_time_minutes: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "keywords": self.keywords,
            "language": self.language,
            "summary": self.summary,
            "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score,
            "word_count": self.word_count,
            "reading_time_minutes": self.reading_time_minutes,
        }


class KeywordExtractor:
    """
    Simple keyword extraction using TF-based approach.

    Extracts the most frequent meaningful words from text.
    """

    def __init__(
        self,
        max_keywords: int = 10,
        min_word_length: int = 3,
        stop_words: set[str] | None = None,
    ) -> None:
        """
        Initialize the keyword extractor.

        Args:
            max_keywords: Maximum number of keywords to extract.
            min_word_length: Minimum word length to consider.
            stop_words: Set of stop words to exclude.
        """
        self.max_keywords = max_keywords
        self.min_word_length = min_word_length
        self.stop_words = stop_words or ALL_STOP_WORDS

    def extract(self, text: str) -> list[str]:
        """
        Extract keywords from text.

        Args:
            text: Text to extract keywords from.

        Returns:
            List of keywords, ordered by frequency.
        """
        if not text:
            return []

        # Clean and normalize text
        text = clean_html(text)
        text = text.lower()

        # Extract words (alphanumeric sequences)
        words = re.findall(r"\b[a-zà-ÿ0-9]+\b", text)

        # Filter words
        filtered_words = [
            word for word in words
            if len(word) >= self.min_word_length
            and word not in self.stop_words
            and not word.isdigit()
        ]

        # Count frequencies
        word_counts = Counter(filtered_words)

        # Get top keywords
        top_keywords = word_counts.most_common(self.max_keywords)

        return [word for word, count in top_keywords]


class LanguageDetector:
    """
    Simple language detection based on common words.

    Supports French and English detection.
    """

    # Common words that are strong indicators of language
    FR_INDICATORS = {
        "le", "la", "les", "de", "du", "des", "un", "une", "est", "sont",
        "dans", "pour", "avec", "sur", "par", "que", "qui", "nous", "vous",
        "cette", "ces", "mais", "aussi", "plus", "être", "avoir", "fait",
    }

    EN_INDICATORS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "have",
        "has", "had", "do", "does", "did", "will", "would", "could", "should",
        "this", "that", "these", "those", "with", "for", "from", "they",
    }

    def detect(self, text: str) -> str | None:
        """
        Detect the language of text.

        Args:
            text: Text to analyze.

        Returns:
            Language code ('fr', 'en') or None if uncertain.
        """
        if not text or len(text) < 20:
            return None

        text = text.lower()
        words = set(re.findall(r"\b[a-zà-ÿ]+\b", text))

        fr_score = len(words & self.FR_INDICATORS)
        en_score = len(words & self.EN_INDICATORS)

        # Require a minimum match and clear winner
        min_score = 3
        if fr_score >= min_score and fr_score > en_score * 1.5:
            return "fr"
        elif en_score >= min_score and en_score > fr_score * 1.5:
            return "en"

        return None


class Summarizer:
    """
    Simple extractive summarizer.

    Extracts the most important sentences from text.
    """

    def __init__(self, max_length: int = 200) -> None:
        """
        Initialize the summarizer.

        Args:
            max_length: Maximum summary length in characters.
        """
        self.max_length = max_length

    def summarize(self, text: str) -> str | None:
        """
        Generate a summary of text.

        Args:
            text: Text to summarize.

        Returns:
            Summary string or None if text is too short.
        """
        if not text:
            return None

        text = clean_html(text)

        # If text is already short enough, return as-is
        if len(text) <= self.max_length:
            return text

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)

        if not sentences:
            return text[:self.max_length] + "..."

        # Take first sentences until we reach max length
        summary_parts = []
        current_length = 0

        for sentence in sentences:
            if current_length + len(sentence) > self.max_length:
                break
            summary_parts.append(sentence)
            current_length += len(sentence) + 1

        if summary_parts:
            return " ".join(summary_parts)

        # Fall back to truncation
        return text[:self.max_length].rsplit(" ", 1)[0] + "..."


class SentimentAnalyzer:
    """
    Keyword-based sentiment analyzer for French and English text.

    Returns a sentiment label (positive/negative/neutral) and a score
    between -1.0 (very negative) and +1.0 (very positive).
    """

    POSITIVE_FR = {
        "bien", "bon", "bonne", "excellent", "positif", "succès", "réussite",
        "progrès", "croissance", "hausse", "amélioration", "avantage", "gagner",
        "victoire", "record", "meilleur", "bénéfice", "innovation", "opportunité",
        "accord", "soutien", "confiance", "optimiste", "favorable", "efficace",
        "dynamique", "solide", "prometteur", "encourageant", "remarquable",
        "performant", "stable", "fiable", "satisfaisant", "augmentation",
    }

    NEGATIVE_FR = {
        "mal", "mauvais", "mauvaise", "échec", "négatif", "crise", "baisse",
        "perte", "risque", "danger", "problème", "menace", "recul", "chute",
        "scandale", "fraude", "faillite", "déficit", "dette", "inflation",
        "conflit", "guerre", "attaque", "accident", "catastrophe", "inquiétude",
        "instable", "vulnérable", "critique", "grave", "alerte", "pénurie",
        "fermeture", "licenciement", "sanction", "condamnation", "violation",
    }

    POSITIVE_EN = {
        "good", "great", "excellent", "positive", "success", "growth", "gain",
        "profit", "innovation", "opportunity", "improvement", "advantage",
        "progress", "record", "best", "strong", "stable", "reliable", "rise",
        "boost", "win", "victory", "optimistic", "favorable", "confident",
        "efficient", "dynamic", "promising", "encouraging", "remarkable",
        "breakthrough", "achievement", "partnership", "agreement", "support",
    }

    NEGATIVE_EN = {
        "bad", "poor", "negative", "crisis", "loss", "risk", "danger",
        "threat", "decline", "drop", "fall", "scandal", "fraud", "bankruptcy",
        "debt", "inflation", "conflict", "war", "attack", "accident",
        "catastrophe", "concern", "unstable", "vulnerable", "critical",
        "severe", "alert", "shortage", "closure", "layoff", "sanction",
        "failure", "crash", "recession", "downturn", "penalty", "violation",
    }

    def analyze(self, text: str, language: str | None = None) -> tuple[str | None, float | None]:
        """
        Analyze sentiment of text.

        Returns:
            Tuple of (sentiment_label, sentiment_score) where label is
            'positive', 'negative', or 'neutral', and score is -1.0 to 1.0.
            Returns (None, None) if text is too short.
        """
        if not text or len(text) < 30:
            return None, None

        text_lower = clean_html(text).lower()
        words = set(re.findall(r"\b[a-zà-ÿ]+\b", text_lower))

        # Use both languages, weight detected language higher
        pos_score = len(words & self.POSITIVE_FR) + len(words & self.POSITIVE_EN)
        neg_score = len(words & self.NEGATIVE_FR) + len(words & self.NEGATIVE_EN)

        if language == "fr":
            pos_score += len(words & self.POSITIVE_FR)
            neg_score += len(words & self.NEGATIVE_FR)
        elif language == "en":
            pos_score += len(words & self.POSITIVE_EN)
            neg_score += len(words & self.NEGATIVE_EN)

        total = pos_score + neg_score
        if total == 0:
            return "neutral", 0.0

        # Score from -1.0 to 1.0
        raw_score = (pos_score - neg_score) / total

        if raw_score > 0.15:
            label = "positive"
        elif raw_score < -0.15:
            label = "negative"
        else:
            label = "neutral"

        return label, round(raw_score, 2)


class Enricher:
    """
    Main enrichment processor.

    Combines keyword extraction, language detection, summarization, and sentiment.
    """

    def __init__(self) -> None:
        """Initialize the enricher."""
        settings = get_settings()
        processing = settings.processing

        self.keyword_extractor = KeywordExtractor(
            max_keywords=processing.max_keywords,
        )
        self.language_detector = LanguageDetector()
        self.summarizer = Summarizer(
            max_length=processing.summarize_max_length,
        )
        self.sentiment_analyzer = SentimentAnalyzer()

        self.extract_keywords = processing.extract_keywords
        self.detect_language = processing.detect_language
        self.generate_summary = processing.summarize
        self.analyze_sentiment = processing.analyze_sentiment

    def enrich(self, item: CollectedItem) -> EnrichmentResult:
        """
        Enrich an item with additional metadata.

        Args:
            item: Item to enrich.

        Returns:
            EnrichmentResult with extracted metadata.
        """
        # Combine text sources
        text = " ".join(filter(None, [
            item.title,
            item.content,
            item.summary,
        ]))

        # Extract keywords
        keywords = []
        if self.extract_keywords:
            keywords = self.keyword_extractor.extract(text)

        # Detect language
        language = item.language
        if not language and self.detect_language:
            language = self.language_detector.detect(text)

        # Generate summary
        summary = item.summary
        if self.generate_summary and item.content and not summary:
            summary = self.summarizer.summarize(item.content)

        # Analyze sentiment
        sentiment = None
        sentiment_score = None
        if self.analyze_sentiment:
            sentiment, sentiment_score = self.sentiment_analyzer.analyze(text, language)

        # Calculate word count and reading time
        clean_text = clean_html(text)
        word_count = len(clean_text.split())
        reading_time = max(1, word_count // 200)  # ~200 words per minute

        return EnrichmentResult(
            keywords=keywords,
            language=language,
            summary=summary,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            word_count=word_count,
            reading_time_minutes=reading_time,
        )

    def enrich_items(
        self,
        items: Sequence[CollectedItem],
    ) -> list[tuple[CollectedItem, EnrichmentResult]]:
        """
        Enrich multiple items.

        Args:
            items: Items to enrich.

        Returns:
            List of (item, enrichment_result) tuples.
        """
        results = []

        for item in items:
            try:
                result = self.enrich(item)
                results.append((item, result))
            except Exception as e:
                log.warning(f"Failed to enrich item {item.guid}: {e}")
                # Return empty result on error
                results.append((item, EnrichmentResult(
                    keywords=[],
                    language=None,
                    summary=None,
                    sentiment=None,
                    sentiment_score=None,
                    word_count=0,
                    reading_time_minutes=0,
                )))

        return results


def enrich_item(item: CollectedItem) -> EnrichmentResult:
    """
    Convenience function to enrich a single item.

    Args:
        item: Item to enrich.

    Returns:
        EnrichmentResult.
    """
    enricher = Enricher()
    return enricher.enrich(item)
