"""
Model persistence — save / load trained models.

Uses joblib for scikit-learn / XGBoost and torch.save for LSTM.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ARTIFACTS_DIR = Path("ml_artifacts")


def save_model(model: Any, name: str, directory: Path | str | None = None) -> Path:
    """Persist a trained model to disk.

    Parameters
    ----------
    model : VolModel
        Fitted model instance.
    name : str
        Friendly name (used as filename stem).
    directory : Path, optional
        Target folder; defaults to ``ml_artifacts/``.

    Returns
    -------
    Path
        Path to the saved artifact.
    """
    out_dir = Path(directory) if directory else _ARTIFACTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Torch models
    try:
        import torch.nn as nn

        if isinstance(model, nn.Module):
            path = out_dir / f"{name}.pt"
            import torch
            torch.save(model.state_dict(), path)
            logger.info("Saved torch model → %s", path)
            return path
    except ImportError:
        pass

    # Everything else (sklearn, xgboost)
    import joblib

    path = out_dir / f"{name}.joblib"
    joblib.dump(model, path)
    logger.info("Saved model → %s", path)
    return path


def load_model(path: Path | str) -> Any:
    """Load a model artifact from disk.

    Detects ``.pt`` (torch) vs ``.joblib`` automatically.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found: {path}")

    if path.suffix == ".pt":
        import torch
        state = torch.load(path, map_location="cpu")
        logger.info("Loaded torch state dict from %s (reconstruct model externally)", path)
        return state

    import joblib
    model = joblib.load(path)
    logger.info("Loaded model from %s", path)
    return model
