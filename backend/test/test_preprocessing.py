"""Preprocessing Engine unit tests."""
import pytest
import pandas as pd
import numpy as np
from app.services.preprocessing_engine import (
    get_dataset_health,
    step_handle_missing,
    detect_outliers,
    step_feature_engineering,
    step_scale_features,
)


def make_dirty_df():
    """Dataset with missing values, outliers, and categorical columns."""
    rng = np.random.default_rng(42)
    n = 50
    df = pd.DataFrame({
        "age":      rng.integers(20, 70, n).astype(float),
        "income":   rng.normal(50000, 10000, n),
        "category": rng.choice(["A", "B", "C"], n).astype(object),
        "score":    rng.uniform(0, 1, n),
    })
    # Introduce missing values
    df.loc[0:4, "age"] = np.nan
    df.loc[5:9, "category"] = np.nan
    # Introduce a clear outlier
    df.loc[0, "income"] = 999999
    return df


# ── Health Dashboard ──────────────────────────────────────────

def test_health_dashboard_keys():
    df = make_dirty_df()
    health = get_dataset_health(df)
    assert "rows" in health
    assert "columns" in health
    assert "missing_per_col" in health
    assert "dtype_breakdown" in health


def test_health_dashboard_correct_counts():
    df = make_dirty_df()
    health = get_dataset_health(df)
    assert health["rows"] == 50
    assert health["columns"] == 4
    # rows 0..4 are NaN for age → 5 missing values
    assert health["missing_per_col"]["age"]["count"] == 5


def test_health_dashboard_dtype_breakdown():
    df = make_dirty_df()
    health = get_dataset_health(df)
    breakdown = health["dtype_breakdown"]
    assert breakdown["numeric"] >= 3   # age, income, score
    assert breakdown["categorical"] >= 1  # category


# ── Missing Value Imputation ──────────────────────────────────

def test_impute_mean():
    df = make_dirty_df()
    result_df, info = step_handle_missing(df.copy(), {"age": "mean"})
    assert result_df["age"].isnull().sum() == 0


def test_impute_median():
    df = make_dirty_df()
    result_df, info = step_handle_missing(df.copy(), {"age": "median"})
    assert result_df["age"].isnull().sum() == 0


def test_impute_mode_categorical():
    df = make_dirty_df()
    result_df, info = step_handle_missing(df.copy(), {"category": "mode"})
    assert result_df["category"].isnull().sum() == 0


def test_impute_drop_rows():
    df = make_dirty_df()
    before_rows = len(df)
    result_df, info = step_handle_missing(df.copy(), {"age": "drop_rows"})
    assert len(result_df) < before_rows
    assert result_df["age"].isnull().sum() == 0


def test_impute_drop_column():
    df = make_dirty_df()
    result_df, info = step_handle_missing(df.copy(), {"age": "drop_column"})
    assert "age" not in result_df.columns


def test_impute_returns_info_dict():
    df = make_dirty_df()
    result_df, info = step_handle_missing(df.copy(), {"age": "mean"})
    assert "column_results" in info
    assert "age" in info["column_results"]


# ── Outlier Detection ─────────────────────────────────────────

def test_outlier_detection_iqr():
    df = make_dirty_df()
    results = detect_outliers(df, method="iqr")
    assert "income" in results
    assert results["income"]["count"] >= 1


def test_outlier_detection_zscore():
    df = make_dirty_df()
    results = detect_outliers(df, method="zscore", threshold=2.5)
    assert "income" in results
    assert results["income"]["count"] >= 1


def test_outlier_detection_result_structure():
    df = make_dirty_df()
    results = detect_outliers(df, method="iqr")
    for col, data in results.items():
        assert "count" in data
        assert "pct" in data
        assert "indices" in data


def test_outlier_detection_ignores_non_numeric():
    df = make_dirty_df()
    results = detect_outliers(df, method="iqr")
    # category is non-numeric; should not appear in results
    assert "category" not in results


# ── Encoding via step_feature_engineering ────────────────────

def test_onehot_encoding():
    df = pd.DataFrame({"cat": ["A", "B", "C", "A", "B"], "val": [1, 2, 3, 4, 5]})
    result_df, info = step_feature_engineering(df.copy(), {"encoding": {"cat": "onehot"}})
    # Original 'cat' column removed; dummy columns added
    assert "cat" not in result_df.columns
    assert result_df.shape[1] > 1
    assert len(info["new_features"]) > 0


def test_label_encoding():
    df = pd.DataFrame({
        "cat": ["A", "B", "C", "A", "B"],
        "value": [1, 2, 3, 4, 5],
    })
    result_df, info = step_feature_engineering(df.copy(), {"encoding": {"cat": "label"}})
    assert "cat_encoded" in result_df.columns
    assert pd.api.types.is_integer_dtype(result_df["cat_encoded"]) or pd.api.types.is_numeric_dtype(result_df["cat_encoded"])


def test_frequency_encoding():
    df = pd.DataFrame({"cat": ["A", "B", "A", "A", "B"], "val": [1, 2, 3, 4, 5]})
    result_df, info = step_feature_engineering(df.copy(), {"encoding": {"cat": "frequency"}})
    assert "cat_freq" in result_df.columns
    # Frequency values should be between 0 and 1
    assert result_df["cat_freq"].max() <= 1.0


# ── Scaling ──────────────────────────────────────────────────

def test_standard_scaling():
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0, 5.0]})
    result_df, info = step_scale_features(df.copy(), {"method": "standard", "columns": ["a"]})
    assert abs(result_df["a"].mean()) < 1e-9  # mean ≈ 0
    assert info["method"] == "standard"


def test_minmax_scaling():
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0, 5.0]})
    result_df, info = step_scale_features(df.copy(), {"method": "minmax", "columns": ["a"]})
    assert result_df["a"].min() >= 0.0
    assert result_df["a"].max() <= 1.0


def test_robust_scaling():
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0, 100.0]})  # 100 is an outlier
    result_df, info = step_scale_features(df.copy(), {"method": "robust", "columns": ["a"]})
    assert "a" in result_df.columns
    assert info["scaled_columns"] == ["a"]


def test_scaling_returns_info():
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [10.0, 20.0, 30.0]})
    result_df, info = step_scale_features(df.copy(), {"method": "standard", "columns": ["a", "b"]})
    assert "scaled_columns" in info
    assert set(info["scaled_columns"]) == {"a", "b"}


def test_scaling_no_columns_noop():
    """When no numeric columns match, returns df unchanged."""
    df = pd.DataFrame({"cat": ["A", "B", "C"]})
    result_df, info = step_scale_features(df.copy(), {"method": "standard"})
    assert info["scaled_columns"] == []
