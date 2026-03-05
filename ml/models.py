"""
Model definitions and registry.

Provides a uniform interface (``fit`` / ``predict``) across:
* Linear Regression (baseline)
* XGBoost
* LSTM (PyTorch-based, optional)
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Protocol, runtime_checkable

import numpy as np

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    LINEAR = "linear"
    XGBOOST = "xgboost"
    LSTM = "lstm"


@runtime_checkable
class VolModel(Protocol):
    """Minimal interface every model must satisfy."""
    def fit(self, X: np.ndarray, y: np.ndarray) -> None: ...
    def predict(self, X: np.ndarray) -> np.ndarray: ...


# ---------------------------------------------------------------------------
# Linear regression (baseline — always available)
# ---------------------------------------------------------------------------

class LinearModel:
    def __init__(self) -> None:
        self._model = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        from sklearn.linear_model import Ridge
        self._model = Ridge(alpha=1.0)
        self._model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model not fitted")
        return self._model.predict(X)


# ---------------------------------------------------------------------------
# XGBoost
# ---------------------------------------------------------------------------

class XGBoostModel:
    def __init__(self, **kwargs: Any) -> None:
        self._params = {
            "n_estimators": 200,
            "max_depth": 5,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "verbosity": 0,
        }
        self._params.update(kwargs)
        self._model = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        try:
            from xgboost import XGBRegressor
        except ImportError:
            logger.warning("xgboost not installed — falling back to LinearModel")
            self._model = LinearModel()
            self._model.fit(X, y)
            return
        self._model = XGBRegressor(**self._params)
        self._model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model not fitted")
        return self._model.predict(X)


# ---------------------------------------------------------------------------
# LSTM (optional — requires torch)
# ---------------------------------------------------------------------------

class LSTMModel:
    """Simple LSTM regressor wrapping PyTorch.

    Uses a sliding window of ``seq_len`` rows to produce a single scalar
    prediction.  Training uses Adam + MSE loss.
    """

    def __init__(
        self,
        seq_len: int = 20,
        hidden_dim: int = 64,
        num_layers: int = 2,
        epochs: int = 50,
        lr: float = 1e-3,
        batch_size: int = 32,
    ) -> None:
        self.seq_len = seq_len
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.epochs = epochs
        self.lr = lr
        self.batch_size = batch_size
        self._model = None
        self._scaler_X = None
        self._scaler_y = None

    def _make_sequences(self, X: np.ndarray, y: np.ndarray | None = None):
        import torch
        seqs, targets = [], []
        for i in range(len(X) - self.seq_len):
            seqs.append(X[i : i + self.seq_len])
            if y is not None:
                targets.append(y[i + self.seq_len])
        X_t = torch.tensor(np.array(seqs), dtype=torch.float32)
        if y is not None:
            y_t = torch.tensor(np.array(targets), dtype=torch.float32).unsqueeze(-1)
            return X_t, y_t
        return X_t, None

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        try:
            import torch
            import torch.nn as nn
            from sklearn.preprocessing import StandardScaler
        except ImportError:
            logger.warning("torch not installed — falling back to LinearModel")
            self._model = LinearModel()
            self._model.fit(X, y)
            return

        self._scaler_X = StandardScaler().fit(X)
        self._scaler_y = StandardScaler().fit(y.reshape(-1, 1))
        X_sc = self._scaler_X.transform(X)
        y_sc = self._scaler_y.transform(y.reshape(-1, 1)).ravel()

        X_t, y_t = self._make_sequences(X_sc, y_sc)

        input_dim = X.shape[1]

        class _LSTM(nn.Module):
            def __init__(me):
                super().__init__()
                me.lstm = nn.LSTM(input_dim, self.hidden_dim, self.num_layers, batch_first=True, dropout=0.2)
                me.fc = nn.Linear(self.hidden_dim, 1)

            def forward(me, x):
                out, _ = me.lstm(x)
                return me.fc(out[:, -1, :])

        net = _LSTM()
        opt = torch.optim.Adam(net.parameters(), lr=self.lr)
        loss_fn = nn.MSELoss()

        dataset = torch.utils.data.TensorDataset(X_t, y_t)
        loader = torch.utils.data.DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

        net.train()
        for epoch in range(self.epochs):
            epoch_loss = 0.0
            for xb, yb in loader:
                opt.zero_grad()
                pred = net(xb)
                loss = loss_fn(pred, yb)
                loss.backward()
                opt.step()
                epoch_loss += loss.item()
            if (epoch + 1) % 10 == 0:
                logger.debug("LSTM epoch %d/%d  loss=%.6f", epoch + 1, self.epochs, epoch_loss / len(loader))

        net.eval()
        self._model = net

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model not fitted")
        # Fallback path
        if isinstance(self._model, LinearModel):
            return self._model.predict(X)

        import torch
        X_sc = self._scaler_X.transform(X)
        X_t, _ = self._make_sequences(X_sc)
        with torch.no_grad():
            pred_sc = self._model(X_t).numpy().ravel()
        return self._scaler_y.inverse_transform(pred_sc.reshape(-1, 1)).ravel()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class ModelRegistry:
    """Factory for model instances."""

    _MAP = {
        ModelType.LINEAR: LinearModel,
        ModelType.XGBOOST: XGBoostModel,
        ModelType.LSTM: LSTMModel,
    }

    @classmethod
    def create(cls, model_type: ModelType | str, **kwargs) -> VolModel:
        if isinstance(model_type, str):
            model_type = ModelType(model_type)
        klass = cls._MAP.get(model_type)
        if klass is None:
            raise ValueError(f"Unknown model type: {model_type}")
        return klass(**kwargs)

    @classmethod
    def available_types(cls):
        return list(cls._MAP.keys())
