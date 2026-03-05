"""ML Predictions page."""
from __future__ import annotations

import streamlit as st
import pandas as pd

from data.market_data import get_default_provider
from ml.models import ModelType
from ml.training import train_model
from ml.inference import predict
from visualization.ml_charts import plot_model_comparison, plot_feature_importance
from ui.components import SidebarParams, metric_row


def render(p: SidebarParams) -> None:
    st.header("ML Volatility Predictions")

    st.markdown(
        "Train and compare models that predict **forward 20-day realised volatility** "
        "from price-based features.  Uses time-series split (no future leakage)."
    )

    # Model selection
    model_types = st.multiselect(
        "Models to train",
        [m.value for m in ModelType],
        default=["linear", "xgboost"],
    )

    if st.button("Train & Evaluate"):
        provider = get_default_provider()
        try:
            prices, _ = provider.get_stock_data(p.ticker, period=p.history_period)
        except Exception as e:
            st.error(f"Data fetch failed: {e}")
            return

        if len(prices) < 100:
            st.warning("Need at least 100 data points for meaningful training.")
            return

        results = {}
        progress = st.progress(0)
        for i, mt in enumerate(model_types):
            with st.spinner(f"Training {mt}..."):
                try:
                    res = train_model(prices, mt)
                    results[mt] = res
                except Exception as e:
                    st.warning(f"{mt} failed: {e}")
            progress.progress((i + 1) / len(model_types))

        if not results:
            st.error("All models failed.")
            return

        # Comparison chart
        st.subheader("Model Comparison")
        fig_cmp = plot_model_comparison(results)
        st.plotly_chart(fig_cmp, use_container_width=True)

        # Per-model details
        for name, res in results.items():
            with st.expander(f"{name} — Details"):
                metric_row(3,
                    ["Test RMSE", "Test MAE", "Test R²"],
                    [f"{res.test_rmse:.4f}", f"{res.test_mae:.4f}", f"{res.test_r2:.4f}"],
                )
                st.markdown(f"Train: {res.n_train} rows | Test: {res.n_test} rows")

                # Feature importance for XGBoost
                if name == "xgboost" and hasattr(res.model, '_model') and hasattr(res.model._model, 'feature_importances_'):
                    fig_imp = plot_feature_importance(
                        res.feature_names, res.model._model.feature_importances_
                    )
                    st.plotly_chart(fig_imp, use_container_width=True)

        # Store best model in session state for live prediction
        best_name = min(results, key=lambda k: results[k].test_rmse)
        st.session_state["trained_model"] = results[best_name].model
        st.success(f"Best model: **{best_name}** (RMSE={results[best_name].test_rmse:.4f}) — saved for live prediction.")

    # Live prediction
    st.subheader("Live Prediction")
    if "trained_model" in st.session_state:
        provider = get_default_provider()
        try:
            prices, _ = provider.get_stock_data(p.ticker, period="6mo")
            preds = predict(st.session_state["trained_model"], prices, latest_only=True)
            if len(preds) > 0:
                st.metric("Predicted Forward 20d Vol", f"{preds.iloc[-1]:.1%}")
            else:
                st.info("Not enough recent data for prediction.")
        except Exception as e:
            st.warning(f"Prediction failed: {e}")
    else:
        st.info("Train a model first to enable live prediction.")
