"""
Training pipeline — separated from inference.

* Uses time-series-aware train/test split (no future leakage).
* Returns rich ``TrainingResult`` with metrics and trained model.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ml.features import FEATURE_COLS, TARGET_COL, build_feature_matrix
from ml.models import ModelRegistry, ModelType, VolModel

logger = logging.getLogger(__name__)


@dataclass
class TrainingResult:
    model: Any                       # fitted VolModel
    model_type: str
    train_rmse: float
    test_rmse: float
    train_mae: float
    test_mae: float
    train_r2: float
    test_r2: float
    feature_names: list
    n_train: int
    n_test: int
    metadata: Dict = field(default_factory=dict)


def train_model(
    prices: pd.DataFrame,
    model_type: ModelType | str = ModelType.XGBOOST,
    *,
    test_ratio: float = 0.2,
    model_kwargs: Optional[Dict] = None,
) -> TrainingResult:
    """End-to-end: build features → split → train → evaluate.

    Uses a **chronological** split — the last ``test_ratio`` fraction
    of rows form the test set to avoid look-ahead bias.
    """
    feat = build_feature_matrix(prices, target=True, dropna=True)
    X = feat[FEATURE_COLS].values
    y = feat[TARGET_COL].values

    split_idx = int(len(X) * (1 - test_ratio))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    logger.info(
        "Training %s — train=%d, test=%d, features=%d",
        model_type, len(X_train), len(X_test), X.shape[1],
    )

    model = ModelRegistry.create(model_type, **(model_kwargs or {}))
    model.fit(X_train, y_train)

    pred_train = model.predict(X_train)
    pred_test = model.predict(X_test)

    # Handle LSTM shorter predictions (due to windowing)
    if len(pred_test) < len(y_test):
        y_test = y_test[-len(pred_test) :]
    if len(pred_train) < len(y_train):
        y_train = y_train[-len(pred_train) :]

    return TrainingResult(
        model=model,
        model_type=str(model_type),
        train_rmse=float(np.sqrt(mean_squared_error(y_train, pred_train))),
        test_rmse=float(np.sqrt(mean_squared_error(y_test, pred_test))),
        train_mae=float(mean_absolute_error(y_train, pred_train)),
        test_mae=float(mean_absolute_error(y_test, pred_test)),
        train_r2=float(r2_score(y_train, pred_train)),
        test_r2=float(r2_score(y_test, pred_test)),
        feature_names=FEATURE_COLS,
        n_train=len(y_train),
        n_test=len(y_test),
    )
