"""
Sentiment analyzer — fetches news via RSS/API and scores with TextBlob / VADER.

The heavy NLP model (VADER) is loaded lazily to avoid import overhead for
pages that don't need sentiment.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SentimentResult:
    """Per-article sentiment score."""
    title: str
    source: str
    polarity: float          # −1 … +1
    subjectivity: float      # 0 … 1
    label: str               # Positive / Negative / Neutral


@dataclass
class SentimentSummary:
    """Aggregate over a batch of articles."""
    results: List[SentimentResult]
    mean_polarity: float
    mean_subjectivity: float
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    overall_label: str


class SentimentAnalyzer:
    """Fetch news headlines and compute sentiment scores.

    Uses Google News RSS (no API key required) and TextBlob for scoring.
    """

    def __init__(self, *, vader: bool = False) -> None:
        self._use_vader = vader

    # ------------------------------------------------------------------ #
    # Data fetching
    # ------------------------------------------------------------------ #
    @staticmethod
    def fetch_news(ticker: str, max_articles: int = 20) -> List[Dict]:
        """Fetch news headlines from Google News RSS.

        Returns list of dicts with keys ``title`` and ``source``.
        """
        try:
            import feedparser
        except ImportError:
            logger.warning("feedparser not installed — returning empty news")
            return []

        url = (
            f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
        )
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:max_articles]:
            source = entry.get("source", {})
            articles.append({
                "title": entry.get("title", ""),
                "source": source.get("title", "Unknown") if isinstance(source, dict) else str(source),
            })
        logger.info("Fetched %d articles for %s", len(articles), ticker)
        return articles

    # ------------------------------------------------------------------ #
    # Scoring
    # ------------------------------------------------------------------ #
    def _score_textblob(self, text: str) -> tuple[float, float]:
        from textblob import TextBlob
        blob = TextBlob(text)
        return blob.sentiment.polarity, blob.sentiment.subjectivity

    def _score_vader(self, text: str) -> tuple[float, float]:
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
        scores = sia.polarity_scores(text)
        return scores["compound"], 0.5  # VADER has no subjectivity

    def score(self, text: str) -> tuple[float, float]:
        """Return (polarity, subjectivity) for a single text."""
        try:
            if self._use_vader:
                return self._score_vader(text)
            return self._score_textblob(text)
        except Exception as exc:
            logger.warning("Sentiment scoring failed: %s", exc)
            return 0.0, 0.0

    @staticmethod
    def _label(polarity: float) -> str:
        if polarity > 0.1:
            return "Positive"
        elif polarity < -0.1:
            return "Negative"
        return "Neutral"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def analyze(self, ticker: str, *, max_articles: int = 20) -> SentimentSummary:
        """End-to-end: fetch → score → summarize."""
        articles = self.fetch_news(ticker, max_articles)
        results: List[SentimentResult] = []
        for art in articles:
            pol, subj = self.score(art["title"])
            results.append(SentimentResult(
                title=art["title"],
                source=art["source"],
                polarity=pol,
                subjectivity=subj,
                label=self._label(pol),
            ))

        if not results:
            return SentimentSummary(
                results=[], mean_polarity=0, mean_subjectivity=0,
                positive_pct=0, negative_pct=0, neutral_pct=0,
                overall_label="Neutral",
            )

        pols = [r.polarity for r in results]
        mean_pol = sum(pols) / len(pols)
        mean_subj = sum(r.subjectivity for r in results) / len(results)
        pos_pct = sum(1 for r in results if r.label == "Positive") / len(results) * 100
        neg_pct = sum(1 for r in results if r.label == "Negative") / len(results) * 100
        neu_pct = 100 - pos_pct - neg_pct

        return SentimentSummary(
            results=results,
            mean_polarity=round(mean_pol, 4),
            mean_subjectivity=round(mean_subj, 4),
            positive_pct=round(pos_pct, 2),
            negative_pct=round(neg_pct, 2),
            neutral_pct=round(neu_pct, 2),
            overall_label=self._label(mean_pol),
        )

    def to_dataframe(self, summary: SentimentSummary) -> pd.DataFrame:
        """Convert results to a DataFrame for display."""
        if not summary.results:
            return pd.DataFrame(columns=["Title", "Source", "Polarity", "Subjectivity", "Label"])
        return pd.DataFrame([
            {
                "Title": r.title,
                "Source": r.source,
                "Polarity": r.polarity,
                "Subjectivity": r.subjectivity,
                "Label": r.label,
            }
            for r in summary.results
        ])
