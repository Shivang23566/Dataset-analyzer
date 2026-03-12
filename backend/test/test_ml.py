"""ML Engine unit tests."""
import os
import pytest
import pandas as pd
import numpy as np
import joblib
from app.services.ml_engine import (
    detect_task_type, get_model_cards,
    train_model, MODEL_STORE, _model_path,
)


# ── Fixtures ──────────────────────────────────────────────────

def make_classification_df(n=100):
    """Small iris-like dataset."""
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "sepal_length": rng.normal(5.0, 0.5, n),
        "sepal_width":  rng.normal(3.0, 0.4, n),
        "petal_length": rng.normal(3.5, 1.0, n),
        "species": rng.choice(["setosa", "versicolor"], n),  # binary
    })


def make_regression_df(n=100):
    """Small regression dataset."""
    rng = np.random.default_rng(42)
    X = rng.normal(0, 1, (n, 3))
    y = X[:, 0] * 2 + X[:, 1] * 0.5 + rng.normal(0, 0.1, n)
    return pd.DataFrame({
        "feature_a": X[:, 0], "feature_b": X[:, 1], "feature_c": X[:, 2],
        "target": y,
    })


# ── Task detection tests ──────────────────────────────────────

def test_detect_task_binary_classification():
    df = make_classification_df()
    result = detect_task_type(df, "species")
    assert result["task"] == "binary_classification"
    assert result["n_classes"] == 2


def test_detect_task_regression():
    df = make_regression_df()
    result = detect_task_type(df, "target")
    assert result["task"] == "regression"
    assert "target_range" in result


def test_detect_task_multiclass():
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "x": rng.normal(0, 1, 150),
        "label": rng.choice(["a", "b", "c"], 150),
    })
    result = detect_task_type(df, "label")
    assert result["task"] == "multiclass_classification"


def test_detect_task_missing_column():
    df = pd.DataFrame({"x": [1, 2, 3]})
    result = detect_task_type(df, "nonexistent")
    assert result["task"] == "unknown"


# ── Model cards tests ─────────────────────────────────────────

def test_get_model_cards_classification():
    cards = get_model_cards("binary_classification")
    assert isinstance(cards, list)
    assert len(cards) > 0
    ids = [c["id"] for c in cards]
    assert "random_forest_classifier" in ids
    assert "logistic_regression" in ids


def test_get_model_cards_regression():
    cards = get_model_cards("regression")
    assert isinstance(cards, list)
    assert len(cards) > 0
    ids = [c["id"] for c in cards]
    assert "random_forest_regressor" in ids


def test_model_card_has_required_fields():
    cards = get_model_cards("binary_classification")
    for card in cards:
        assert "id" in card
        assert "name" in card
        assert "hyperparams" in card


# ── Training tests ─────────────────────────────────────────────
# train_model(df, config) where config = {model_id, target_col, task, hyperparams, ...}

def test_train_model_classification():
    df = make_classification_df(n=80)
    result = train_model(df, {
        "model_id": "random_forest_classifier",
        "target_col": "species",
        "task": "binary_classification",
        "hyperparams": {"n_estimators": 10, "max_depth": 3},
    })
    assert result.get("success") is True
    assert "metrics" in result
    metrics = result["metrics"]
    assert "accuracy" in metrics or "f1_weighted" in metrics
    assert "session_key" in result
    assert result["session_key"] in MODEL_STORE or os.path.exists(_model_path(result["session_key"]))


def test_train_model_regression():
    df = make_regression_df(n=80)
    result = train_model(df, {
        "model_id": "random_forest_regressor",
        "target_col": "target",
        "task": "regression",
        "hyperparams": {"n_estimators": 10, "max_depth": 3},
    })
    assert result.get("success") is True
    metrics = result["metrics"]
    assert any(k in metrics for k in ["r2", "mae", "rmse", "mse"])


def test_train_model_feature_importance():
    df = make_classification_df(n=80)
    result = train_model(df, {
        "model_id": "random_forest_classifier",
        "target_col": "species",
        "task": "binary_classification",
        "hyperparams": {"n_estimators": 10},
    })
    assert result.get("success") is True
    fi = result.get("feature_importance", [])
    assert isinstance(fi, list) and len(fi) > 0


def test_train_model_stores_to_disk():
    df = make_classification_df(n=60)
    result = train_model(df, {
        "model_id": "logistic_regression",
        "target_col": "species",
        "task": "binary_classification",
        "hyperparams": {},
    })
    assert result.get("success") is True
    session_key = result["session_key"]
    path = _model_path(session_key)
    assert os.path.exists(path)
    loaded = joblib.load(path)
    assert loaded is not None


def test_model_export_loadable():
    """Verify saved model file is loadable with joblib."""
    df = make_regression_df(n=60)
    result = train_model(df, {
        "model_id": "linear_regression",
        "target_col": "target",
        "task": "regression",
        "hyperparams": {},
    })
    assert result.get("success") is True
    path = _model_path(result["session_key"])
    if os.path.exists(path):
        artifact = joblib.load(path)
        assert artifact is not None


def test_train_model_missing_target_col():
    df = make_classification_df(n=50)
    result = train_model(df, {
        "model_id": "logistic_regression",
        "target_col": "nonexistent_col",
        "task": "binary_classification",
        "hyperparams": {},
    })
    assert "error" in result


def test_train_model_no_numeric_features():
    df = pd.DataFrame({"label": ["a", "b", "c"] * 10})
    result = train_model(df, {
        "model_id": "logistic_regression",
        "target_col": "label",
        "task": "binary_classification",
        "hyperparams": {},
    })
    assert "error" in result
