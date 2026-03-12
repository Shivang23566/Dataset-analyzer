"""
Smart Data Preprocessing Engine
Implements a 9-step modular preprocessing pipeline for any dataset.
"""
import json
import io
import os
import base64
import warnings
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple
from scipy import stats
from datetime import datetime

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# DATASET HEALTH DASHBOARD
# ─────────────────────────────────────────────────────────────

def get_dataset_health(df: pd.DataFrame) -> Dict[str, Any]:
    """Return a comprehensive health snapshot of the dataset."""
    n_rows, n_cols = df.shape
    memory_mb = round(df.memory_usage(deep=True).sum() / 1024 / 1024, 3)

    # Data type breakdown
    dtype_breakdown = {"numeric": 0, "categorical": 0, "datetime": 0, "boolean": 0}
    for col in df.columns:
        if pd.api.types.is_bool_dtype(df[col]):
            dtype_breakdown["boolean"] += 1
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            dtype_breakdown["datetime"] += 1
        elif pd.api.types.is_numeric_dtype(df[col]):
            dtype_breakdown["numeric"] += 1
        else:
            dtype_breakdown["categorical"] += 1

    # Missing value info per column
    missing_per_col = {}
    for col in df.columns:
        pct = round(float(df[col].isnull().mean() * 100), 2)
        color = "green" if pct < 5 else ("yellow" if pct <= 20 else "red")
        missing_per_col[col] = {"pct": pct, "color": color, "count": int(df[col].isnull().sum())}

    # Duplicates
    dup_count = int(df.duplicated().sum())

    # Constant / near-constant columns
    constant_cols = [c for c in df.columns if df[c].nunique() <= 1]
    near_constant_cols = [c for c in df.columns if 1 < df[c].nunique() <= max(2, int(n_rows * 0.01))]

    # Skewness & kurtosis for numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    skewness_summary = {}
    kurtosis_summary = {}
    for col in numeric_cols:
        try:
            skewness_summary[col] = round(float(df[col].skew()), 4)
            kurtosis_summary[col] = round(float(df[col].kurtosis()), 4)
        except Exception:
            pass

    # Cardinality for categorical columns
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    cardinality = {col: int(df[col].nunique()) for col in cat_cols}

    # Missing heatmap data (column vs missing flag as fraction)
    heatmap_data = []
    for col in df.columns:
        missing_mask = df[col].isnull().astype(int).tolist()
        heatmap_data.append({"column": col, "missing_flags": missing_mask[:200]})  # first 200 rows

    return {
        "rows": n_rows,
        "columns": n_cols,
        "memory_mb": memory_mb,
        "dtype_breakdown": dtype_breakdown,
        "missing_per_col": missing_per_col,
        "duplicate_count": dup_count,
        "constant_columns": constant_cols,
        "near_constant_columns": near_constant_cols,
        "skewness_summary": skewness_summary,
        "kurtosis_summary": kurtosis_summary,
        "cardinality": cardinality,
    }


def _safe_val(v):
    """Convert numpy/pandas scalar to JSON-safe Python type."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def _df_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Compact dataset stats for before/after comparison."""
    n_rows, n_cols = df.shape
    memory_mb = round(df.memory_usage(deep=True).sum() / 1024 / 1024, 3)
    total_missing = int(df.isnull().sum().sum())
    dtype_counts = df.dtypes.value_counts().to_dict()
    return {
        "rows": n_rows,
        "columns": n_cols,
        "memory_mb": memory_mb,
        "total_missing": total_missing,
        "dtype_counts": {str(k): int(v) for k, v in dtype_counts.items()},
    }


# ─────────────────────────────────────────────────────────────
# STEP 1 — DUPLICATE REMOVAL
# ─────────────────────────────────────────────────────────────

def step_remove_duplicates(df: pd.DataFrame, keep: str = "first") -> Tuple[pd.DataFrame, Dict]:
    before = len(df)
    if keep == "none":
        df = df.drop_duplicates(keep=False)
    else:
        df = df.drop_duplicates(keep=keep)
    after = len(df)
    return df, {"removed": before - after, "before_rows": before, "after_rows": after}


# ─────────────────────────────────────────────────────────────
# STEP 2 — MISSING VALUE TREATMENT
# ─────────────────────────────────────────────────────────────

def _recommend_imputation(df: pd.DataFrame, col: str) -> str:
    """AI-recommend imputation strategy for a column."""
    missing_pct = df[col].isnull().mean() * 100
    if missing_pct > 40:
        return "drop_column"
    if missing_pct < 5:
        return "drop_rows"
    if pd.api.types.is_numeric_dtype(df[col]):
        try:
            skew = abs(float(df[col].skew()))
            if skew > 1:
                return "median"
        except Exception:
            pass
        return "knn"
    return "mode"


def step_handle_missing(df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict]:
    """
    config: { col_name: strategy }
    strategies: drop_rows, drop_column, mean, median, mode, forward_fill,
                backward_fill, knn, constant, unknown
    """
    from sklearn.impute import KNNImputer, SimpleImputer

    results = {}
    cols_to_drop = []

    for col, strategy in config.items():
        if col not in df.columns:
            continue
        before_missing = int(df[col].isnull().sum())
        if before_missing == 0:
            continue

        if strategy == "drop_column":
            cols_to_drop.append(col)
            results[col] = {"strategy": strategy, "before_missing": before_missing, "after_missing": 0}
            continue

        if strategy == "drop_rows":
            df = df.dropna(subset=[col])
        elif strategy == "mean" and pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(df[col].mean())
        elif strategy == "median" and pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(df[col].median())
        elif strategy == "mode":
            mode_val = df[col].mode()
            if len(mode_val) > 0:
                df[col] = df[col].fillna(mode_val[0])
        elif strategy == "forward_fill":
            df[col] = df[col].ffill()
        elif strategy == "backward_fill":
            df[col] = df[col].bfill()
        elif strategy == "knn" and pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if col in numeric_cols:
                imputer = KNNImputer(n_neighbors=5)
                df[numeric_cols] = imputer.fit_transform(df[numeric_cols])
        elif strategy == "constant":
            fill_value = config.get(f"{col}_constant", 0 if pd.api.types.is_numeric_dtype(df[col]) else "Unknown")
            df[col] = df[col].fillna(fill_value)
        elif strategy == "unknown":
            df[col] = df[col].fillna("Unknown")
        else:
            # fallback: mode
            mode_val = df[col].mode()
            if len(mode_val) > 0:
                df[col] = df[col].fillna(mode_val[0])

        after_missing = int(df[col].isnull().sum()) if col in df.columns else 0
        results[col] = {"strategy": strategy, "before_missing": before_missing, "after_missing": after_missing}

    if cols_to_drop:
        df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    return df, {"column_results": results}


def get_missing_recommendations(df: pd.DataFrame) -> Dict[str, str]:
    """Auto-generate imputation recommendations for all columns with missing data."""
    return {col: _recommend_imputation(df, col) for col in df.columns if df[col].isnull().any()}


# ─────────────────────────────────────────────────────────────
# STEP 3 — OUTLIER DETECTION & TREATMENT
# ─────────────────────────────────────────────────────────────

def detect_outliers(df: pd.DataFrame, method: str = "iqr", threshold: float = 3.0) -> Dict[str, Any]:
    """Detect outliers per numeric column, return counts and indices."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    results = {}

    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        if method == "iqr":
            Q1, Q3 = series.quantile(0.25), series.quantile(0.75)
            IQR = Q3 - Q1
            mask = (df[col] < Q1 - 1.5 * IQR) | (df[col] > Q3 + 1.5 * IQR)
        elif method == "zscore":
            z = np.abs(stats.zscore(series))
            mask = pd.Series(False, index=df.index)
            mask[series.index[z > threshold]] = True
        else:
            mask = pd.Series(False, index=df.index)

        outlier_count = int(mask.sum())
        results[col] = {
            "count": outlier_count,
            "pct": round(outlier_count / len(df) * 100, 2),
            "indices": mask[mask].index.tolist()[:50],  # cap at 50 for response size
        }

    return results


def step_treat_outliers(df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict]:
    """
    config: { method: 'iqr'|'zscore', threshold: 3.0, treatment: 'remove'|'cap'|'median'|'flag', columns: [...] }
    """
    method = config.get("method", "iqr")
    threshold = float(config.get("threshold", 3.0))
    treatment = config.get("treatment", "cap")
    columns = config.get("columns", df.select_dtypes(include=[np.number]).columns.tolist())

    rows_before = len(df)
    outlier_detected = detect_outliers(df, method=method, threshold=threshold)
    total_treated = 0

    for col in columns:
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        series = df[col].dropna()
        if len(series) == 0:
            continue

        if method == "iqr":
            Q1, Q3 = series.quantile(0.25), series.quantile(0.75)
            IQR = Q3 - Q1
            lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
            mask = (df[col] < lower) | (df[col] > upper)
        else:
            z = np.abs((df[col] - df[col].mean()) / df[col].std(ddof=0))
            mask = z > threshold
            lower = df[col].mean() - threshold * df[col].std(ddof=0)
            upper = df[col].mean() + threshold * df[col].std(ddof=0)

        count = int(mask.sum())
        if count == 0:
            continue
        total_treated += count

        if treatment == "remove":
            df = df[~mask]
        elif treatment == "cap":
            p1, p99 = df[col].quantile(0.01), df[col].quantile(0.99)
            df[col] = df[col].clip(lower=p1, upper=p99)
        elif treatment == "median":
            df.loc[mask, col] = df[col].median()
        elif treatment == "flag":
            df[f"{col}_is_outlier"] = mask.astype(int)

    return df, {
        "total_treated": total_treated,
        "rows_before": rows_before,
        "rows_after": len(df),
        "per_column": {k: v["count"] for k, v in outlier_detected.items()},
    }


# ─────────────────────────────────────────────────────────────
# STEP 4 — DATA TYPE CORRECTION
# ─────────────────────────────────────────────────────────────

def step_fix_dtypes(df: pd.DataFrame, overrides: Optional[Dict[str, str]] = None) -> Tuple[pd.DataFrame, Dict]:
    """Auto-detect and fix mismatched column types, then apply overrides."""
    from dateutil import parser as dateutil_parser

    changes = {}

    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col]):
            # Try numeric conversion
            numeric_try = pd.to_numeric(df[col], errors="coerce")
            non_null_orig = df[col].dropna()
            if len(non_null_orig) > 0 and numeric_try.notna().sum() / len(non_null_orig) > 0.9:
                df[col] = numeric_try
                changes[col] = {"from": "object", "to": "numeric"}
                continue

            # Try boolean
            bool_map = {"yes": True, "no": False, "true": True, "false": False, "1": True, "0": False}
            lower_vals = df[col].dropna().str.lower().unique()
            if set(lower_vals).issubset(set(bool_map.keys())):
                df[col] = df[col].str.lower().map(bool_map)
                changes[col] = {"from": "object", "to": "boolean"}
                continue

            # Try datetime
            try:
                sample = df[col].dropna().head(10)
                parsed = [dateutil_parser.parse(str(v)) for v in sample]
                if len(parsed) > 0:
                    df[col] = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
                    changes[col] = {"from": "object", "to": "datetime"}
            except Exception:
                pass

    # Extract datetime features
    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
    for col in datetime_cols:
        df[f"{col}_year"] = df[col].dt.year
        df[f"{col}_month"] = df[col].dt.month
        df[f"{col}_day"] = df[col].dt.day
        df[f"{col}_dayofweek"] = df[col].dt.dayofweek
        df[f"{col}_is_weekend"] = df[col].dt.dayofweek.isin([5, 6]).astype(int)
        changes[col] = {**changes.get(col, {}), "datetime_features_extracted": True}
        df = df.drop(columns=[col])

    # Apply user overrides
    if overrides:
        for col, dtype_str in overrides.items():
            if col not in df.columns:
                continue
            try:
                if dtype_str == "numeric":
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                elif dtype_str == "string":
                    df[col] = df[col].astype(str)
                elif dtype_str == "datetime":
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                elif dtype_str == "boolean":
                    df[col] = df[col].astype(bool)
                elif dtype_str == "category":
                    df[col] = df[col].astype("category")
                changes[col] = {**changes.get(col, {}), "override": dtype_str}
            except Exception as e:
                changes[col] = {**changes.get(col, {}), "override_error": str(e)}

    return df, {"type_changes": changes}


# ─────────────────────────────────────────────────────────────
# STEP 5 — FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────

def step_feature_engineering(df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict]:
    """
    config keys:
      - log_transform: [col_names]
      - sqrt_transform: [col_names]
      - binning: [{col, strategy, n_bins}]
      - interactions: [{col1, col2, operation}]  # product | ratio
      - encoding: {col: strategy}  # label | onehot | frequency
      - polynomial: {columns: [], degree: 2}
    """
    new_features = []

    # Log transform
    for col in config.get("log_transform", []):
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            df[f"{col}_log"] = np.log1p(df[col].clip(lower=0))
            new_features.append(f"{col}_log")

    # Sqrt transform
    for col in config.get("sqrt_transform", []):
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            df[f"{col}_sqrt"] = np.sqrt(df[col].clip(lower=0))
            new_features.append(f"{col}_sqrt")

    # Binning
    for bin_cfg in config.get("binning", []):
        col = bin_cfg.get("col")
        strategy = bin_cfg.get("strategy", "equal_width")
        n_bins = int(bin_cfg.get("n_bins", 5))
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        new_col = f"{col}_bin"
        if strategy == "equal_width":
            df[new_col] = pd.cut(df[col], bins=n_bins, labels=False)
        elif strategy == "quantile":
            df[new_col] = pd.qcut(df[col], q=n_bins, labels=False, duplicates="drop")
        new_features.append(new_col)

    # Interaction terms
    for inter in config.get("interactions", []):
        c1, c2 = inter.get("col1"), inter.get("col2")
        op = inter.get("operation", "product")
        if c1 not in df.columns or c2 not in df.columns:
            continue
        if not (pd.api.types.is_numeric_dtype(df[c1]) and pd.api.types.is_numeric_dtype(df[c2])):
            continue
        if op == "product":
            df[f"{c1}_x_{c2}"] = df[c1] * df[c2]
            new_features.append(f"{c1}_x_{c2}")
        elif op == "ratio":
            df[f"{c1}_div_{c2}"] = df[c1] / (df[c2].replace(0, np.nan))
            new_features.append(f"{c1}_div_{c2}")

    # Encoding
    from sklearn.preprocessing import LabelEncoder
    for col, enc_strategy in config.get("encoding", {}).items():
        if col not in df.columns:
            continue
        if enc_strategy == "label":
            le = LabelEncoder()
            df[f"{col}_encoded"] = le.fit_transform(df[col].astype(str))
            new_features.append(f"{col}_encoded")
        elif enc_strategy == "onehot":
            cardinality = df[col].nunique()
            if cardinality > 20:
                continue  # skip high cardinality
            dummies = pd.get_dummies(df[col], prefix=col, drop_first=False)
            df = pd.concat([df, dummies], axis=1)
            new_features.extend(dummies.columns.tolist())
            df = df.drop(columns=[col])
        elif enc_strategy == "frequency":
            freq_map = df[col].value_counts(normalize=True).to_dict()
            df[f"{col}_freq"] = df[col].map(freq_map)
            new_features.append(f"{col}_freq")

    # Polynomial features
    poly_cfg = config.get("polynomial", {})
    if poly_cfg:
        from sklearn.preprocessing import PolynomialFeatures
        poly_cols = [c for c in poly_cfg.get("columns", []) if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
        degree = int(poly_cfg.get("degree", 2))
        if poly_cols:
            pf = PolynomialFeatures(degree=degree, include_bias=False, interaction_only=False)
            poly_data = pf.fit_transform(df[poly_cols])
            poly_feature_names = pf.get_feature_names_out(poly_cols)
            poly_df = pd.DataFrame(poly_data, columns=poly_feature_names, index=df.index)
            # Only add new columns (not originals)
            new_poly_cols = [c for c in poly_feature_names if c not in poly_cols]
            df = pd.concat([df, poly_df[new_poly_cols]], axis=1)
            new_features.extend(new_poly_cols)

    return df, {"new_features": new_features, "feature_count": len(df.columns)}


# ─────────────────────────────────────────────────────────────
# STEP 6 — SCALING & NORMALIZATION
# ─────────────────────────────────────────────────────────────

def step_scale_features(df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict]:
    """
    config: { method: 'standard'|'minmax'|'robust'|'maxabs'|'log'|'power'|'normalizer',
              columns: [col_names] (optional, defaults to all numeric) }
    """
    from sklearn.preprocessing import (
        StandardScaler, MinMaxScaler, RobustScaler,
        MaxAbsScaler, Normalizer, PowerTransformer
    )

    method = config.get("method", "standard")
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    columns = [c for c in config.get("columns", numeric_cols) if c in numeric_cols]

    if not columns:
        return df, {"method": method, "scaled_columns": []}

    scaler_map = {
        "standard": StandardScaler(),
        "minmax": MinMaxScaler(),
        "robust": RobustScaler(),
        "maxabs": MaxAbsScaler(),
        "normalizer": Normalizer(),
    }

    if method == "log":
        for col in columns:
            df[col] = np.log1p(df[col].clip(lower=0))
    elif method == "power":
        pt = PowerTransformer(method="yeo-johnson")
        df[columns] = pt.fit_transform(df[columns])
    elif method in scaler_map:
        scaler = scaler_map[method]
        df[columns] = scaler.fit_transform(df[columns])

    return df, {"method": method, "scaled_columns": columns}


# ─────────────────────────────────────────────────────────────
# STEP 7 — CLASS IMBALANCE HANDLING
# ─────────────────────────────────────────────────────────────

def detect_class_imbalance(df: pd.DataFrame, target_col: str) -> Dict[str, Any]:
    """Check class distribution of the target column."""
    if target_col not in df.columns:
        return {"imbalanced": False}
    vc = df[target_col].value_counts()
    minority_pct = float(vc.min() / vc.sum() * 100)
    return {
        "imbalanced": minority_pct < 20,
        "minority_pct": round(minority_pct, 2),
        "class_distribution": vc.to_dict(),
    }


def step_handle_imbalance(df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict]:
    """
    config: { target_col: str, method: 'smote'|'adasyn'|'over'|'under'|'smotetomek' }
    """
    target_col = config.get("target_col")
    method = config.get("method", "smote")

    if not target_col or target_col not in df.columns:
        return df, {"error": "Invalid target column"}

    X = df.drop(columns=[target_col])
    y = df[target_col]

    # Only numeric features for resampling
    numeric_X = X.select_dtypes(include=[np.number])
    if numeric_X.shape[1] == 0:
        return df, {"error": "No numeric features for resampling"}

    before_dist = y.value_counts().to_dict()

    try:
        if method == "smote":
            from imblearn.over_sampling import SMOTE
            sampler = SMOTE(random_state=42)
        elif method == "adasyn":
            from imblearn.over_sampling import ADASYN
            sampler = ADASYN(random_state=42)
        elif method == "over":
            from imblearn.over_sampling import RandomOverSampler
            sampler = RandomOverSampler(random_state=42)
        elif method == "under":
            from imblearn.under_sampling import RandomUnderSampler
            sampler = RandomUnderSampler(random_state=42)
        elif method == "smotetomek":
            from imblearn.combine import SMOTETomek
            sampler = SMOTETomek(random_state=42)
        else:
            return df, {"error": f"Unknown method: {method}"}

        X_res, y_res = sampler.fit_resample(numeric_X, y)
        df_res = pd.DataFrame(X_res, columns=numeric_X.columns)
        df_res[target_col] = y_res
        after_dist = df_res[target_col].value_counts().to_dict()

        return df_res, {
            "method": method,
            "before_distribution": before_dist,
            "after_distribution": after_dist,
            "rows_before": len(df),
            "rows_after": len(df_res),
        }
    except Exception as e:
        return df, {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# STEP 8 — DIMENSIONALITY REDUCTION
# ─────────────────────────────────────────────────────────────

def step_reduce_dimensions(df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict]:
    """
    config: {
      method: 'pca'|'remove_low_variance'|'remove_correlated'|'select_kbest',
      n_components: 10,  # for PCA
      variance_threshold: 0.01,  # for near-zero variance
      correlation_threshold: 0.95,
      k: 10,  # for SelectKBest
      target_col: str  # for SelectKBest / LDA
    }
    """
    method = config.get("method", "remove_correlated")
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cols_before = len(df.columns)
    removed = []
    added = []

    if method == "remove_low_variance":
        from sklearn.feature_selection import VarianceThreshold
        threshold = float(config.get("variance_threshold", 0.01))
        vt = VarianceThreshold(threshold=threshold)
        try:
            vt.fit(df[numeric_cols].fillna(0))
            kept = [numeric_cols[i] for i, v in enumerate(vt.get_support()) if v]
            removed_cols = [c for c in numeric_cols if c not in kept]
            if removed_cols:
                df = df.drop(columns=removed_cols)
                removed.extend(removed_cols)
        except Exception:
            pass

    elif method == "remove_correlated":
        threshold = float(config.get("correlation_threshold", 0.95))
        if len(numeric_cols) > 1:
            corr = df[numeric_cols].corr().abs()
            upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
            to_drop = [col for col in upper.columns if any(upper[col] > threshold)]
            if to_drop:
                df = df.drop(columns=[c for c in to_drop if c in df.columns])
                removed.extend(to_drop)

    elif method == "pca":
        from sklearn.decomposition import PCA
        n_components = config.get("n_components", min(len(numeric_cols), 10))
        variance_to_retain = float(config.get("variance_to_retain", 0.95))

        if len(numeric_cols) < 2:
            return df, {"error": "Not enough numeric columns for PCA"}

        data = df[numeric_cols].fillna(0)
        pca = PCA(n_components=min(n_components, len(numeric_cols), len(df)))
        pca.fit(data)

        # Compute explained variance
        cumvar = float(np.sum(pca.explained_variance_ratio_))
        n_components_final = next(
            (i + 1 for i, cv in enumerate(np.cumsum(pca.explained_variance_ratio_)) if cv >= variance_to_retain),
            pca.n_components_
        )

        pca_final = PCA(n_components=n_components_final)
        pca_data = pca_final.fit_transform(data)
        pca_cols = [f"PC{i+1}" for i in range(n_components_final)]
        pca_df = pd.DataFrame(pca_data, columns=pca_cols, index=df.index)

        non_numeric = df.drop(columns=numeric_cols)
        df = pd.concat([non_numeric, pca_df], axis=1)
        removed.extend(numeric_cols)
        added.extend(pca_cols)

        return df, {
            "method": "pca",
            "n_components_before": len(numeric_cols),
            "n_components_after": n_components_final,
            "explained_variance": [round(float(v), 4) for v in pca_final.explained_variance_ratio_],
            "cumulative_variance": round(float(np.sum(pca_final.explained_variance_ratio_)), 4),
            "removed_columns": numeric_cols,
            "added_columns": pca_cols,
        }

    elif method == "select_kbest":
        from sklearn.feature_selection import SelectKBest, f_classif, f_regression
        target_col = config.get("target_col")
        k = int(config.get("k", 10))
        if target_col not in df.columns:
            return df, {"error": "Target column not found"}
        X = df[numeric_cols].fillna(0)
        y = df[target_col]
        if target_col in numeric_cols:
            X = X.drop(columns=[target_col])
        score_func = f_regression if pd.api.types.is_numeric_dtype(y) else f_classif
        selector = SelectKBest(score_func=score_func, k=min(k, len(X.columns)))
        selector.fit(X, y)
        kept = [X.columns[i] for i, v in enumerate(selector.get_support()) if v]
        to_drop = [c for c in numeric_cols if c not in kept and c != target_col]
        if to_drop:
            df = df.drop(columns=to_drop)
            removed.extend(to_drop)

    return df, {
        "method": method,
        "cols_before": cols_before,
        "cols_after": len(df.columns),
        "removed_columns": removed,
        "added_columns": added,
    }


# ─────────────────────────────────────────────────────────────
# STEP 9 — TRAIN/TEST SPLIT
# ─────────────────────────────────────────────────────────────

def step_train_test_split(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    config: { test_size: 0.2, stratify_col: str|None, random_state: 42 }
    Returns info about split sizes (not the actual data splits for memory reasons).
    """
    from sklearn.model_selection import train_test_split

    test_size = float(config.get("test_size", 0.2))
    random_state = int(config.get("random_state", 42))
    stratify_col = config.get("stratify_col")

    stratify = df[stratify_col] if stratify_col and stratify_col in df.columns else None

    try:
        train_df, test_df = train_test_split(df, test_size=test_size, random_state=random_state, stratify=stratify)
        return {
            "train_rows": len(train_df),
            "test_rows": len(test_df),
            "total_rows": len(df),
            "test_size": test_size,
            "train_pct": round((1 - test_size) * 100, 1),
            "test_pct": round(test_size * 100, 1),
            "stratified": stratify is not None,
        }
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# CONFIG TRANSLATION  (frontend keys → internal step keys)
# ─────────────────────────────────────────────────────────────

def _translate_frontend_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Translate the frontend-style config dict (keys like 'duplicate_removal',
    'missing_values', etc.) into the internal step-based keys that
    run_pipeline() uses (step1_enabled, step2_config, …).

    If the config already uses internal keys (step1_enabled …) it is returned
    unchanged so legacy callers continue to work.
    """
    # Already in internal format — nothing to translate
    if any(k.startswith("step") and k.endswith("_enabled") for k in cfg):
        return cfg

    internal: Dict[str, Any] = {}

    # ── Step 1: Duplicate Removal ──────────────────────────
    dup = cfg.get("duplicate_removal")
    if dup is not None:
        internal["step1_enabled"] = True
        internal["step1_keep"] = dup.get("keep", "first")

    # ── Step 2: Missing Values ─────────────────────────────
    missing = cfg.get("missing_values")
    if missing is not None:
        internal["step2_enabled"] = True
        # frontend wraps strategies under a "strategies" key
        strats = missing.get("strategies", missing)
        internal["step2_config"] = strats if isinstance(strats, dict) else {}

    # ── Step 3: Outlier Treatment ──────────────────────────
    outlier = cfg.get("outlier_treatment")
    if outlier is not None:
        internal["step3_enabled"] = True
        internal["step3_config"] = {
            "method":    outlier.get("method",    "iqr"),
            "threshold": outlier.get("threshold", 3.0),
            "treatment": outlier.get("treatment", "cap"),
        }

    # ── Step 4: Type Correction ────────────────────────────
    type_corr = cfg.get("type_correction")
    if type_corr is not None:
        internal["step4_enabled"] = True
        internal["step4_overrides"] = type_corr.get("overrides", {})

    # ── Step 5: Feature Engineering ───────────────────────
    feat = cfg.get("feature_engineering")
    if feat is not None:
        internal["step5_enabled"] = True
        internal["step5_config"] = {
            "log_transform":  feat.get("log_transform",  []),
            "sqrt_transform": feat.get("sqrt_transform", []),
            "encoding":       feat.get("encoding",       {}),
            "binning":        feat.get("binning",        []),
            "interactions":   feat.get("interactions",   []),
            "polynomial":     feat.get("polynomial",     {}),
        }

    # ── Step 6: Scaling ────────────────────────────────────
    scaling = cfg.get("scaling")
    if scaling is not None:
        internal["step6_enabled"] = True
        internal["step6_config"] = {"method": scaling.get("method", "standard")}

    # ── Step 7: Class Imbalance ────────────────────────────
    imbalance = cfg.get("class_imbalance")
    if imbalance is not None:
        internal["step7_enabled"] = True
        internal["step7_config"] = {
            "target_col": imbalance.get("target_col"),
            "method":     imbalance.get("method", "smote"),
        }

    # ── Step 8: Dimensionality Reduction ──────────────────
    dim = cfg.get("dimensionality_reduction")
    if dim is not None:
        internal["step8_enabled"] = True
        internal["step8_config"] = {
            "method":               dim.get("method",          "remove_correlated"),
            "correlation_threshold": dim.get("corr_threshold",  0.95),
            "n_components":         dim.get("pca_components",  10),
            "variance_threshold":   dim.get("variance_threshold", 0.01),
            "k":                    dim.get("k",               10),
            "target_col":           dim.get("target_col",      None),
        }

    # ── Step 9: Train / Test Split ─────────────────────────
    split = cfg.get("train_test_split")
    if split is not None:
        internal["step9_enabled"] = True
        internal["step9_config"] = {
            "test_size":    split.get("test_size",    0.2),
            "stratify_col": split.get("stratify_col", None) or None,
            "random_state": split.get("random_state", 42),
        }

    return internal


# ─────────────────────────────────────────────────────────────
# FULL PIPELINE RUNNER
# ─────────────────────────────────────────────────────────────

def run_pipeline(df: pd.DataFrame, pipeline_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the full preprocessing pipeline based on a config dict.
    Accepts both frontend-style keys (duplicate_removal, missing_values, …)
    and the legacy internal keys (step1_enabled, step2_config, …).
    Returns { steps: {step_name: result}, before_stats, after_stats, preview, columns, success }
    """
    # ── Translate frontend keys to internal format if needed ──
    pipeline_config = _translate_frontend_config(pipeline_config)

    stats_before = _df_stats(df)
    step_results = {}

    # Step 1: Duplicates
    if pipeline_config.get("step1_enabled", False):
        keep = pipeline_config.get("step1_keep", "first")
        df, result = step_remove_duplicates(df, keep=keep)
        step_results["step1_duplicates"] = result

    # Step 2: Missing values
    if pipeline_config.get("step2_enabled", False):
        missing_config = pipeline_config.get("step2_config", {})
        # If no config provided, auto-recommend
        if not missing_config:
            missing_config = get_missing_recommendations(df)
        df, result = step_handle_missing(df, missing_config)
        step_results["step2_missing"] = result

    # Step 3: Outliers
    if pipeline_config.get("step3_enabled", False):
        df, result = step_treat_outliers(df, pipeline_config.get("step3_config", {}))
        step_results["step3_outliers"] = result

    # Step 4: Data type correction
    if pipeline_config.get("step4_enabled", False):
        overrides = pipeline_config.get("step4_overrides", {})
        df, result = step_fix_dtypes(df, overrides if overrides else None)
        step_results["step4_dtypes"] = result

    # Step 5: Feature engineering
    if pipeline_config.get("step5_enabled", False):
        df, result = step_feature_engineering(df, pipeline_config.get("step5_config", {}))
        step_results["step5_features"] = result

    # Step 6: Scaling
    if pipeline_config.get("step6_enabled", False):
        df, result = step_scale_features(df, pipeline_config.get("step6_config", {"method": "standard"}))
        step_results["step6_scaling"] = result

    # Step 7: Class imbalance
    if pipeline_config.get("step7_enabled", False):
        df, result = step_handle_imbalance(df, pipeline_config.get("step7_config", {}))
        step_results["step7_imbalance"] = result

    # Step 8: Dimensionality reduction
    if pipeline_config.get("step8_enabled", False):
        df, result = step_reduce_dimensions(df, pipeline_config.get("step8_config", {}))
        step_results["step8_reduction"] = result

    # Step 9: Train/test split info
    if pipeline_config.get("step9_enabled", False):
        result = step_train_test_split(df, pipeline_config.get("step9_config", {}))
        step_results["step9_split"] = result

    stats_after = _df_stats(df)

    # Serialize result safely
    def safe_json(obj):
        if isinstance(obj, dict):
            return {k: safe_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [safe_json(v) for v in obj]
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return None if np.isnan(obj) else float(obj)
        elif isinstance(obj, (np.bool_,)):
            return bool(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        elif isinstance(obj, pd.Series):
            return obj.tolist()
        else:
            return obj

    return {
        "steps": safe_json(step_results),
        "before_stats": stats_before,
        "after_stats": stats_after,
        "preview": df.head(20).replace({np.nan: None}).to_dict(orient="records"),
        "columns": [
            {"name": c, "dtype": str(df[c].dtype)}
            for c in df.columns
        ],
        "success": True,
    }, df


# ─────────────────────────────────────────────────────────────
# EXPORT HELPERS
# ─────────────────────────────────────────────────────────────

PROCESSED_STORE: Dict[str, Dict] = {}
PROCESSED_STORE_TTL_SECONDS = 3600  # 1 hour
MAX_STORE_SIZE = 50


def _evict_processed():
    """Remove expired entries and enforce MAX_STORE_SIZE cap."""
    import time as _time
    now = _time.monotonic()
    expired = [k for k, v in PROCESSED_STORE.items() if now - v.get("_created_at", now) > PROCESSED_STORE_TTL_SECONDS]
    for k in expired:
        del PROCESSED_STORE[k]
    # If still over capacity, drop oldest entries
    if len(PROCESSED_STORE) > MAX_STORE_SIZE:
        by_age = sorted(PROCESSED_STORE.items(), key=lambda kv: kv[1].get("_created_at", 0))
        for k, _ in by_age[: len(PROCESSED_STORE) - MAX_STORE_SIZE]:
            del PROCESSED_STORE[k]


def store_processed_df(session_key: str, df: pd.DataFrame, user_id: int = None):
    import time as _time
    _evict_processed()
    PROCESSED_STORE[session_key] = {"df": df.copy(), "_created_at": _time.monotonic(), "user_id": user_id}
    # Persist to cache backend so data survives restarts
    try:
        from app.core.cache import df_cache
        df_cache.store_df(session_key, df)
    except Exception:
        pass


def get_processed_df(session_key: str) -> Optional[pd.DataFrame]:
    entry = PROCESSED_STORE.get(session_key)
    if entry is None:
        # Try persistent cache backend (file/Redis)
        try:
            from app.core.cache import df_cache
            cached_df = df_cache.get_df(session_key)
            if cached_df is not None:
                import time as _time
                PROCESSED_STORE[session_key] = {"df": cached_df, "_created_at": _time.monotonic()}
                return cached_df
        except Exception:
            pass
        return None
    return entry.get("df")


def get_processed_owner(session_key: str) -> Optional[int]:
    """Return the user_id that owns the processed session, or None if not found."""
    entry = PROCESSED_STORE.get(session_key)
    if entry is None:
        return None
    return entry.get("user_id")


def export_dataframe(df: pd.DataFrame, fmt: str) -> Tuple[bytes, str, str]:
    """Export dataframe to bytes. Returns (data, media_type, extension)."""
    buf = io.BytesIO()
    if fmt == "csv":
        df.to_csv(buf, index=False)
        return buf.getvalue(), "text/csv", ".csv"
    elif fmt == "excel":
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        return buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"
    elif fmt == "parquet":
        df.to_parquet(buf, index=False)
        return buf.getvalue(), "application/octet-stream", ".parquet"
    elif fmt == "json":
        df.to_json(buf, orient="records")
        return buf.getvalue(), "application/json", ".json"
    else:
        df.to_csv(buf, index=False)
        return buf.getvalue(), "text/csv", ".csv"
