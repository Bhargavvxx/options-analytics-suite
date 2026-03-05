"""
Inference pipeline — stateless, consumes a pre-trained model.

Separated from training so Streamlit pages can load once and predict
without re-training on every interaction.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ml.features import FEATURE_COLS, build_feature_matrix
from ml.models import VolModel

logger = logging.getLogger(__name__)


def predict(
    model: VolModel,
    prices: pd.DataFrame,
    *,
    latest_only: bool = False,
) -> pd.Series:
    """Run inference on a trained model.

    Parameters
    ----------
    model : VolModel
        A fitted model (from ``train_model(...).model``).
    prices : pd.DataFrame
        OHLCV data (same format as training).
    latest_only : bool
        If True, only return the most recent prediction (for live use).

    Returns
    -------
    pd.Series
        Predicted values, indexed like the input.
    """
    feat = build_feature_matrix(prices, target=False, dropna=False)
    # Keep index aligned — only predict on complete rows
    mask = feat[FEATURE_COLS].notna().all(axis=1)
    X = feat.loc[mask, FEATURE_COLS].values

    if len(X) == 0:
        logger.warning("No complete feature rows — cannot predict")
        return pd.Series(dtype=np.float64)

    preds = model.predict(X)
    out = pd.Series(preds, index=feat.loc[mask].index, name="predicted_vol")

    if latest_only:
        return out.iloc[[-1]]
    return out
