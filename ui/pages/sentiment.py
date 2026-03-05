"""Sentiment Analysis page."""
from __future__ import annotations

import streamlit as st

from sentiment.analyzer import SentimentAnalyzer
from ui.components import SidebarParams, metric_row


def render(p: SidebarParams) -> None:
    st.header("Market Sentiment Analysis")

    analyzer = SentimentAnalyzer()

    if st.button("Fetch & Analyze News"):
        with st.spinner(f"Fetching news for {p.ticker}..."):
            summary = analyzer.analyze(p.ticker, max_articles=20)

        if not summary.results:
            st.warning("No articles found. Install `feedparser` and `textblob`.")
            return

        st.subheader("Sentiment Summary")
        metric_row(4,
            ["Overall", "Avg Polarity", "Positive %", "Negative %"],
            [
                summary.overall_label,
                f"{summary.mean_polarity:+.3f}",
                f"{summary.positive_pct:.0f}%",
                f"{summary.negative_pct:.0f}%",
            ],
        )

        st.subheader("Article Scores")
        df = analyzer.to_dataframe(summary)
        st.dataframe(df, use_container_width=True)

        # Polarity distribution
        import plotly.express as px
        fig = px.histogram(df, x="Polarity", nbins=20, color="Label",
                           title="Polarity Distribution",
                           color_discrete_map={"Positive": "green", "Negative": "red", "Neutral": "grey"})
        st.plotly_chart(fig, use_container_width=True)
