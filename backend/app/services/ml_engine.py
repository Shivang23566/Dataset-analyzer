"""
Automated ML Model Builder Engine
Implements model recommendation, training, evaluation, and export.
"""
import io
import json
import pickle
import warnings
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

warnings.filterwarnings("ignore")

# In-memory model store (session_key -> model artifacts)
MODEL_STORE: Dict[str, Dict] = {}


# ─────────────────────────────────────────────────────────────
# TASK DETECTION
# ─────────────────────────────────────────────────────────────

def detect_task_type(df: pd.DataFrame, target_col: str) -> Dict[str, Any]:
    """Auto-detect ML task type from the target column."""
    if target_col not in df.columns:
        return {"task": "unknown", "reason": "Target column not found"}
    target = df[target_col].dropna()
    n_unique = target.nunique()
    is_numeric = pd.api.types.is_numeric_dtype(target)
    if n_unique == 2:
        return {"task": "binary_classification", "n_classes": 2,
                "class_labels": [str(v) for v in target.unique().tolist()]}
    elif 3 <= n_unique <= 20 and (not is_numeric or n_unique <= 10):
        return {"task": "multiclass_classification", "n_classes": n_unique,
                "class_labels": [str(v) for v in target.unique().tolist()]}
    elif is_numeric and n_unique > 20:
        return {"task": "regression",
                "target_range": [float(target.min()), float(target.max())]}
    elif 3 <= n_unique <= 20:
        return {"task": "multiclass_classification", "n_classes": n_unique}
    else:
        return {"task": "regression",
                "target_range": [float(target.min()), float(target.max())]}


# ─────────────────────────────────────────────────────────────
# AI MODEL RECOMMENDATION
# ─────────────────────────────────────────────────────────────

def recommend_model(df: pd.DataFrame, target_col: Optional[str], task_info: Dict) -> Dict[str, Any]:
    """Analyse dataset and recommend the best model with reasoning."""
    n_samples, n_features = df.shape
    task = task_info.get("task", "unknown")
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    has_mixed = len(cat_cols) > 0
    missing_ratio = float(df.isnull().mean().mean())
    is_imbalanced = False

    if target_col and target_col in df.columns and "classification" in task:
        vc = df[target_col].value_counts()
        minority_pct = float(vc.min() / vc.sum() * 100)
        is_imbalanced = minority_pct < 20

    linear_signal = False
    if target_col and task == "regression" and target_col in df.columns:
        try:
            num_only = df.select_dtypes(include=[np.number]).drop(columns=[target_col], errors="ignore")
            if len(num_only.columns) > 0:
                corr = num_only.corrwith(df[target_col]).abs().mean()
                linear_signal = float(corr) > 0.4
        except Exception:
            pass

    high_dim = n_features > n_samples
    reasons = [
        f"Dataset: {n_samples:,} rows × {n_features} features",
        f"Task: {task.replace('_', ' ').title()}",
    ]
    if has_mixed:
        reasons.append(f"Mixed features ({len(cat_cols)} categorical)")
    if is_imbalanced:
        reasons.append("Class imbalance detected (<20% minority)")
    if high_dim:
        reasons.append("High dimensionality (features > samples)")
    if missing_ratio > 0.1:
        reasons.append(f"Significant missing data ({missing_ratio*100:.1f}%)")

    recommended = ""
    reason = ""

    if task == "regression":
        if high_dim:
            recommended = "linear_regression"
            reason = "High dimensionality benefits from Ridge regularization to prevent overfitting"
        elif n_samples < 1000 and linear_signal:
            recommended = "linear_regression"
            reason = "Small dataset with strong linear signal — Ridge Regression is interpretable and effective"
        elif n_samples < 5000:
            recommended = "svr"
            reason = "Medium dataset with non-linear patterns — SVR with RBF kernel performs well"
        elif n_samples > 50000:
            recommended = "xgboost_regressor"
            reason = "Large tabular dataset — XGBoost provides speed and accuracy at scale"
        else:
            recommended = "random_forest_regressor"
            reason = "Mixed features, moderate size — Random Forest is robust and handles mixed types well"
    elif "classification" in task:
        if high_dim:
            recommended = "logistic_regression"
            reason = "High dimensionality — Regularized Logistic Regression prevents overfitting"
        elif is_imbalanced:
            recommended = "xgboost_classifier"
            reason = "Class imbalance — XGBoost handles imbalance natively with scale_pos_weight"
        elif n_samples < 1000:
            recommended = "logistic_regression"
            reason = "Small dataset — Logistic Regression is interpretable and avoids overfitting"
        elif n_samples < 5000:
            recommended = "svm_classifier"
            reason = "Small-medium non-linear dataset — SVM with RBF kernel excels here"
        elif n_samples > 50000:
            recommended = "xgboost_classifier"
            reason = "Large tabular dataset — XGBoost delivers speed and accuracy at scale"
        else:
            recommended = "random_forest_classifier"
            reason = "Mixed features, moderate size — Random Forest is robust and requires minimal tuning"
    elif task == "clustering":
        recommended = "kmeans"
        reason = "KMeans is the standard starting point; compare with DBSCAN for non-spherical clusters"

    return {
        "recommended_model": recommended,
        "reason": reason,
        "analysis_factors": reasons,
        "dataset_summary": {
            "n_samples": n_samples,
            "n_features": n_features,
            "has_mixed_features": has_mixed,
            "is_imbalanced": is_imbalanced,
            "high_dimensionality": high_dim,
            "missing_ratio": round(missing_ratio, 4),
        },
    }


# ─────────────────────────────────────────────────────────────
# MODEL CARDS METADATA
# ─────────────────────────────────────────────────────────────

def get_model_cards(task: str) -> List[Dict]:
    classification_cards = [
        {
            "id": "logistic_regression",
            "name": "Logistic Regression",
            "icon": "📈",
            "best_for": "Linear decision boundaries, interpretable models",
            "pros": ["Highly interpretable", "Fast training", "Works well for high-dimensional data"],
            "cons": ["Assumes linearity", "Sensitive to outliers", "May underfit complex patterns"],
            "interpretability": 5,
            "speed": 5,
            "hyperparams": {
                "C": {"type": "float", "default": 1.0, "min": 0.001, "max": 100.0, "label": "Regularization (C)", "tooltip": "Inverse of regularization strength. Smaller = stronger regularization."},
                "max_iter": {"type": "int", "default": 1000, "min": 100, "max": 10000, "label": "Max Iterations", "tooltip": "Maximum number of iterations for the solver."},
                "solver": {"type": "select", "default": "lbfgs", "options": ["lbfgs", "liblinear", "saga", "sag"], "label": "Solver", "tooltip": "Algorithm to use for optimization."},
            }
        },
        {
            "id": "random_forest_classifier",
            "name": "Random Forest",
            "icon": "🌲",
            "best_for": "Mixed features, non-linear patterns, robustness",
            "pros": ["Handles mixed feature types", "Robust to outliers", "Built-in feature importance"],
            "cons": ["Slower on large datasets", "Less interpretable", "High memory usage"],
            "interpretability": 3,
            "speed": 3,
            "hyperparams": {
                "n_estimators": {"type": "int", "default": 100, "min": 10, "max": 500, "label": "Number of Trees", "tooltip": "More trees = better performance but slower training."},
                "max_depth": {"type": "int", "default": 10, "min": 1, "max": 50, "label": "Max Depth", "tooltip": "Maximum depth of each tree. None = fully grown."},
                "min_samples_split": {"type": "int", "default": 2, "min": 2, "max": 20, "label": "Min Samples Split", "tooltip": "Minimum samples required to split an internal node."},
            }
        },
        {
            "id": "xgboost_classifier",
            "name": "XGBoost Classifier",
            "icon": "⚡",
            "best_for": "Large tabular datasets, imbalanced classes, competitions",
            "pros": ["State-of-the-art performance", "Handles missing values", "Built-in regularization"],
            "cons": ["Many hyperparameters to tune", "Less interpretable", "Slower than linear models"],
            "interpretability": 2,
            "speed": 4,
            "hyperparams": {
                "n_estimators": {"type": "int", "default": 100, "min": 10, "max": 1000, "label": "Estimators", "tooltip": "Number of boosting rounds."},
                "max_depth": {"type": "int", "default": 6, "min": 1, "max": 15, "label": "Max Depth", "tooltip": "Maximum tree depth; higher = more complex model."},
                "learning_rate": {"type": "float", "default": 0.1, "min": 0.001, "max": 1.0, "label": "Learning Rate", "tooltip": "Step size shrinkage to prevent overfitting."},
                "subsample": {"type": "float", "default": 0.8, "min": 0.3, "max": 1.0, "label": "Subsample", "tooltip": "Fraction of samples used per tree."},
            }
        },
        {
            "id": "svm_classifier",
            "name": "SVM Classifier",
            "icon": "🎯",
            "best_for": "Small-medium datasets, high-dimensional spaces",
            "pros": ["Effective in high-dimensional spaces", "Memory efficient", "Versatile kernels"],
            "cons": ["Slow on large datasets", "Requires feature scaling", "Less interpretable"],
            "interpretability": 2,
            "speed": 2,
            "hyperparams": {
                "C": {"type": "float", "default": 1.0, "min": 0.01, "max": 100.0, "label": "Regularization (C)", "tooltip": "Penalty for misclassification. Higher = less regularization."},
                "kernel": {"type": "select", "default": "rbf", "options": ["rbf", "linear", "poly", "sigmoid"], "label": "Kernel", "tooltip": "Type of hyperplane to use."},
                "gamma": {"type": "select", "default": "scale", "options": ["scale", "auto"], "label": "Gamma", "tooltip": "Kernel coefficient."},
            }
        },
    ]

    regression_cards = [
        {
            "id": "linear_regression",
            "name": "Ridge Regression",
            "icon": "📐",
            "best_for": "Linear relationships, interpretable predictions",
            "pros": ["Highly interpretable", "Fast training", "Handles multicollinearity"],
            "cons": ["Assumes linearity", "Sensitive to outliers", "May underfit complex patterns"],
            "interpretability": 5,
            "speed": 5,
            "hyperparams": {
                "alpha": {"type": "float", "default": 1.0, "min": 0.0001, "max": 100.0, "label": "Alpha", "tooltip": "Regularization strength. Higher = stronger."},
                "fit_intercept": {"type": "bool", "default": True, "label": "Fit Intercept", "tooltip": "Whether to calculate the intercept."},
            }
        },
        {
            "id": "random_forest_regressor",
            "name": "Random Forest Regressor",
            "icon": "🌲",
            "best_for": "Non-linear relationships, feature importance",
            "pros": ["Handles non-linearity", "Robust to outliers", "No scaling required"],
            "cons": ["Memory intensive", "Slow on large data", "Less interpretable"],
            "interpretability": 3,
            "speed": 3,
            "hyperparams": {
                "n_estimators": {"type": "int", "default": 100, "min": 10, "max": 500, "label": "Number of Trees", "tooltip": "More trees = better performance but slower."},
                "max_depth": {"type": "int", "default": 10, "min": 1, "max": 50, "label": "Max Depth", "tooltip": "Maximum depth of each tree."},
                "min_samples_split": {"type": "int", "default": 2, "min": 2, "max": 20, "label": "Min Samples Split", "tooltip": "Minimum samples to split a node."},
            }
        },
        {
            "id": "xgboost_regressor",
            "name": "XGBoost Regressor",
            "icon": "⚡",
            "best_for": "Large tabular datasets, complex patterns",
            "pros": ["Excellent performance", "Handles missing values", "Fast with GPU"],
            "cons": ["Complex tuning", "Less interpretable", "Risk of overfitting"],
            "interpretability": 2,
            "speed": 4,
            "hyperparams": {
                "n_estimators": {"type": "int", "default": 100, "min": 10, "max": 1000, "label": "Estimators", "tooltip": "Number of boosting rounds."},
                "max_depth": {"type": "int", "default": 6, "min": 1, "max": 15, "label": "Max Depth", "tooltip": "Maximum tree depth."},
                "learning_rate": {"type": "float", "default": 0.1, "min": 0.001, "max": 1.0, "label": "Learning Rate", "tooltip": "Step size for gradient updates."},
                "subsample": {"type": "float", "default": 0.8, "min": 0.3, "max": 1.0, "label": "Subsample", "tooltip": "Fraction of samples per tree."},
            }
        },
        {
            "id": "svr",
            "name": "Support Vector Regressor",
            "icon": "🎯",
            "best_for": "Small-medium non-linear datasets",
            "pros": ["Works with high-dimensional data", "Robust to outliers", "Flexible kernel"],
            "cons": ["Slow on large datasets", "Requires feature scaling", "Sensitive to hyperparams"],
            "interpretability": 2,
            "speed": 2,
            "hyperparams": {
                "C": {"type": "float", "default": 1.0, "min": 0.01, "max": 100.0, "label": "Regularization (C)", "tooltip": "How much to penalize errors."},
                "kernel": {"type": "select", "default": "rbf", "options": ["rbf", "linear", "poly"], "label": "Kernel", "tooltip": "Type of hyperplane."},
                "epsilon": {"type": "float", "default": 0.1, "min": 0.0, "max": 1.0, "label": "Epsilon", "tooltip": "Insensitive loss tube width."},
            }
        },
    ]

    clustering_cards = [
        {
            "id": "kmeans",
            "name": "K-Means",
            "icon": "🔵",
            "best_for": "Well-separated spherical clusters",
            "pros": ["Simple and fast", "Scales well", "Deterministic with seed"],
            "cons": ["Must specify K", "Assumes spherical clusters", "Sensitive to outliers"],
            "interpretability": 4,
            "speed": 5,
            "hyperparams": {
                "n_clusters": {"type": "int", "default": 3, "min": 2, "max": 20, "label": "K (clusters)", "tooltip": "Number of clusters to find."},
                "n_init": {"type": "int", "default": 10, "min": 1, "max": 50, "label": "Initializations", "tooltip": "Number of times to run with different seeds."},
                "max_iter": {"type": "int", "default": 300, "min": 100, "max": 1000, "label": "Max Iterations", "tooltip": "Maximum iterations per run."},
            }
        },
        {
            "id": "dbscan",
            "name": "DBSCAN",
            "icon": "🌀",
            "best_for": "Arbitrary-shaped clusters, noise detection",
            "pros": ["No need to specify K", "Finds arbitrary shapes", "Identifies noise/outliers"],
            "cons": ["Sensitive to eps/min_samples", "Poor on varying densities", "Memory intensive"],
            "interpretability": 3,
            "speed": 3,
            "hyperparams": {
                "eps": {"type": "float", "default": 0.5, "min": 0.01, "max": 5.0, "label": "Epsilon", "tooltip": "Neighborhood radius."},
                "min_samples": {"type": "int", "default": 5, "min": 1, "max": 50, "label": "Min Samples", "tooltip": "Minimum points to form a dense region."},
            }
        },
        {
            "id": "agglomerative",
            "name": "Agglomerative",
            "icon": "🔗",
            "best_for": "Hierarchical cluster relationships",
            "pros": ["No need to specify K upfront", "Creates hierarchy", "Deterministic"],
            "cons": ["Slow on large datasets", "Not scalable", "Single linkage can chain"],
            "interpretability": 4,
            "speed": 2,
            "hyperparams": {
                "n_clusters": {"type": "int", "default": 3, "min": 2, "max": 20, "label": "Clusters", "tooltip": "Number of clusters."},
                "linkage": {"type": "select", "default": "ward", "options": ["ward", "complete", "average", "single"], "label": "Linkage", "tooltip": "Distance metric between clusters."},
            }
        },
        {
            "id": "gmm",
            "name": "Gaussian Mixture",
            "icon": "📊",
            "best_for": "Probabilistic cluster assignments",
            "pros": ["Soft cluster assignments", "Handles overlapping clusters", "Probabilistic output"],
            "cons": ["Assumes Gaussian distributions", "Sensitive to initialization", "Computationally heavy"],
            "interpretability": 3,
            "speed": 3,
            "hyperparams": {
                "n_components": {"type": "int", "default": 3, "min": 2, "max": 20, "label": "Components", "tooltip": "Number of mixture components."},
                "covariance_type": {"type": "select", "default": "full", "options": ["full", "tied", "diag", "spherical"], "label": "Covariance Type", "tooltip": "Type of covariance matrix."},
            }
        },
    ]

    if "classification" in task:
        return classification_cards
    elif task == "regression":
        return regression_cards
    elif task == "clustering":
        return clustering_cards
    return classification_cards


# ─────────────────────────────────────────────────────────────
# MODEL FACTORY
# ─────────────────────────────────────────────────────────────

def _build_model(model_id: str, hyperparams: Dict, task: str):
    hp = hyperparams or {}
    if model_id == "logistic_regression":
        from sklearn.linear_model import LogisticRegression
        return LogisticRegression(C=float(hp.get("C", 1.0)), max_iter=int(hp.get("max_iter", 1000)),
                                   solver=hp.get("solver", "lbfgs"), random_state=42)
    elif model_id == "random_forest_classifier":
        from sklearn.ensemble import RandomForestClassifier
        md = hp.get("max_depth", 10)
        return RandomForestClassifier(n_estimators=int(hp.get("n_estimators", 100)),
                                       max_depth=int(md) if md and str(md) != "None" else None,
                                       min_samples_split=int(hp.get("min_samples_split", 2)),
                                       random_state=42, n_jobs=-1)
    elif model_id == "xgboost_classifier":
        try:
            from xgboost import XGBClassifier
            return XGBClassifier(n_estimators=int(hp.get("n_estimators", 100)),
                                  max_depth=int(hp.get("max_depth", 6)),
                                  learning_rate=float(hp.get("learning_rate", 0.1)),
                                  subsample=float(hp.get("subsample", 0.8)),
                                  random_state=42, eval_metric="logloss", verbosity=0)
        except ImportError:
            from sklearn.ensemble import GradientBoostingClassifier
            return GradientBoostingClassifier(n_estimators=int(hp.get("n_estimators", 100)), random_state=42)
    elif model_id == "svm_classifier":
        from sklearn.svm import SVC
        return SVC(C=float(hp.get("C", 1.0)), kernel=hp.get("kernel", "rbf"),
                   gamma=hp.get("gamma", "scale"), probability=True, random_state=42)
    elif model_id == "linear_regression":
        from sklearn.linear_model import Ridge
        return Ridge(alpha=float(hp.get("alpha", 1.0)))
    elif model_id == "random_forest_regressor":
        from sklearn.ensemble import RandomForestRegressor
        md = hp.get("max_depth", 10)
        return RandomForestRegressor(n_estimators=int(hp.get("n_estimators", 100)),
                                      max_depth=int(md) if md and str(md) != "None" else None,
                                      min_samples_split=int(hp.get("min_samples_split", 2)),
                                      random_state=42, n_jobs=-1)
    elif model_id == "xgboost_regressor":
        try:
            from xgboost import XGBRegressor
            return XGBRegressor(n_estimators=int(hp.get("n_estimators", 100)),
                                 max_depth=int(hp.get("max_depth", 6)),
                                 learning_rate=float(hp.get("learning_rate", 0.1)),
                                 subsample=float(hp.get("subsample", 0.8)),
                                 random_state=42, verbosity=0)
        except ImportError:
            from sklearn.ensemble import GradientBoostingRegressor
            return GradientBoostingRegressor(n_estimators=int(hp.get("n_estimators", 100)), random_state=42)
    elif model_id == "svr":
        from sklearn.svm import SVR
        return SVR(C=float(hp.get("C", 1.0)), kernel=hp.get("kernel", "rbf"), epsilon=float(hp.get("epsilon", 0.1)))
    elif model_id == "kmeans":
        from sklearn.cluster import KMeans
        return KMeans(n_clusters=int(hp.get("n_clusters", 3)), n_init=int(hp.get("n_init", 10)),
                      max_iter=int(hp.get("max_iter", 300)), random_state=42)
    elif model_id == "dbscan":
        from sklearn.cluster import DBSCAN
        return DBSCAN(eps=float(hp.get("eps", 0.5)), min_samples=int(hp.get("min_samples", 5)))
    elif model_id == "agglomerative":
        from sklearn.cluster import AgglomerativeClustering
        return AgglomerativeClustering(n_clusters=int(hp.get("n_clusters", 3)), linkage=hp.get("linkage", "ward"))
    elif model_id == "gmm":
        from sklearn.mixture import GaussianMixture
        return GaussianMixture(n_components=int(hp.get("n_components", 3)),
                               covariance_type=hp.get("covariance_type", "full"), random_state=42)
    raise ValueError(f"Unknown model_id: {model_id}")


def _get_param_distributions(model_id: str) -> Dict:
    from scipy.stats import randint, uniform
    if "random_forest" in model_id:
        return {"n_estimators": randint(50, 300), "max_depth": [None, 5, 10, 15, 20],
                "min_samples_split": randint(2, 10)}
    elif "xgboost" in model_id:
        return {"n_estimators": randint(50, 300), "max_depth": randint(3, 10),
                "learning_rate": uniform(0.01, 0.3), "subsample": uniform(0.6, 0.4)}
    elif "logistic" in model_id:
        return {"C": [0.001, 0.01, 0.1, 1, 10, 100]}
    elif "svm" in model_id:
        return {"C": [0.1, 1, 10, 100], "gamma": ["scale", "auto"]}
    return {}


# ─────────────────────────────────────────────────────────────
# TRAINING & EVALUATION
# ─────────────────────────────────────────────────────────────

def train_model(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    from sklearn.model_selection import train_test_split, cross_val_score, RandomizedSearchCV
    from sklearn.preprocessing import LabelEncoder

    model_id = config["model_id"]
    target_col = config.get("target_col")
    task = config.get("task", "regression")
    hyperparams = config.get("hyperparams", {})
    auto_tune = config.get("auto_tune", False)
    cv_folds = int(config.get("cv_folds", 5))
    test_size = float(config.get("test_size", 0.2))
    random_state = int(config.get("random_state", 42))

    if task == "clustering":
        X_raw = df.select_dtypes(include=[np.number]).fillna(0)
        y = None
    else:
        if not target_col or target_col not in df.columns:
            return {"error": f"Target column '{target_col}' not found"}
        X_raw = df.drop(columns=[target_col]).select_dtypes(include=[np.number]).fillna(0)
        y_raw = df[target_col]
        le = None
        if not pd.api.types.is_numeric_dtype(y_raw):
            le = LabelEncoder()
            y = pd.Series(le.fit_transform(y_raw.astype(str)), index=y_raw.index)
        else:
            y = y_raw.reset_index(drop=True)
        X_raw = X_raw.reset_index(drop=True)

    if X_raw.shape[1] == 0:
        return {"error": "No numeric features available for training"}
    if len(X_raw) < 10:
        return {"error": "Not enough samples for training (minimum 10)"}

    feature_names = X_raw.columns.tolist()
    model = _build_model(model_id, hyperparams, task)

    # Clustering
    if task == "clustering":
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
        from sklearn.decomposition import PCA
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_raw)
        start = datetime.now()
        labels = model.fit_predict(X_scaled)
        duration = (datetime.now() - start).total_seconds()
        metrics = {}
        n_labels = len(set(labels)) - (1 if -1 in labels else 0)
        if n_labels >= 2:
            try:
                metrics["silhouette_score"] = round(float(silhouette_score(X_scaled, labels, sample_size=min(5000, len(X_scaled)))), 4)
                metrics["davies_bouldin_index"] = round(float(davies_bouldin_score(X_scaled, labels)), 4)
                metrics["calinski_harabasz_score"] = round(float(calinski_harabasz_score(X_scaled, labels)), 4)
            except Exception:
                pass
        unique, counts = np.unique(labels, return_counts=True)
        cluster_dist = {str(int(k)): int(v) for k, v in zip(unique, counts)}
        pca = PCA(n_components=min(2, X_scaled.shape[1]))
        pca_data = pca.fit_transform(X_scaled)
        viz_data = [
            {"x": float(pca_data[i, 0]), "y": float(pca_data[i, 1] if pca_data.shape[1] > 1 else 0), "cluster": int(labels[i])}
            for i in range(min(500, len(pca_data)))
        ]
        session_key = f"{model_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        MODEL_STORE[session_key] = {"model": model, "feature_names": feature_names, "model_id": model_id,
                                     "task": task, "hyperparams": hyperparams, "metrics": metrics,
                                     "training_date": datetime.now().isoformat()}
        return {"success": True, "session_key": session_key, "model_id": model_id, "task": task,
                "training_time_seconds": round(duration, 2), "metrics": metrics,
                "cluster_distribution": cluster_dist, "n_clusters": n_labels, "visualization_data": viz_data}

    # Supervised
    stratify_y = y if "classification" in task else None
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X_raw, y, test_size=test_size, random_state=random_state, stratify=stratify_y)
    except Exception:
        X_train, X_test, y_train, y_test = train_test_split(X_raw, y, test_size=test_size, random_state=random_state)

    best_params = hyperparams
    if auto_tune:
        param_dist = _get_param_distributions(model_id)
        if param_dist:
            try:
                scoring = "roc_auc" if task == "binary_classification" else ("f1_weighted" if "classification" in task else "r2")
                rs = RandomizedSearchCV(model, param_dist, n_iter=15, cv=min(cv_folds, 3),
                                        scoring=scoring, random_state=random_state, n_jobs=-1)
                rs.fit(X_train, y_train)
                model = rs.best_estimator_
                best_params = {k: (int(v) if isinstance(v, np.integer) else (float(v) if isinstance(v, np.floating) else v))
                               for k, v in rs.best_params_.items()}
            except Exception:
                pass

    start = datetime.now()
    model.fit(X_train, y_train)
    duration = (datetime.now() - start).total_seconds()

    cv_scoring = "roc_auc" if task == "binary_classification" else ("f1_weighted" if "classification" in task else "r2")
    cv_mean, cv_std = None, None
    try:
        cv_scores = cross_val_score(model, X_raw, y, cv=min(cv_folds, 5), scoring=cv_scoring, n_jobs=-1)
        cv_mean = round(float(cv_scores.mean()), 4)
        cv_std = round(float(cv_scores.std()), 4)
    except Exception:
        pass

    y_pred = model.predict(X_test)
    metrics = {}
    plots = {}

    if "classification" in task:
        from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                                      roc_auc_score, confusion_matrix, log_loss)
        metrics["accuracy"] = round(float(accuracy_score(y_test, y_pred)), 4)
        metrics["precision_weighted"] = round(float(precision_score(y_test, y_pred, average="weighted", zero_division=0)), 4)
        metrics["recall_weighted"] = round(float(recall_score(y_test, y_pred, average="weighted", zero_division=0)), 4)
        metrics["f1_weighted"] = round(float(f1_score(y_test, y_pred, average="weighted", zero_division=0)), 4)
        metrics["f1_macro"] = round(float(f1_score(y_test, y_pred, average="macro", zero_division=0)), 4)
        try:
            if task == "binary_classification":
                y_prob = model.predict_proba(X_test)[:, 1]
                metrics["roc_auc"] = round(float(roc_auc_score(y_test, y_prob)), 4)
                metrics["log_loss"] = round(float(log_loss(y_test, y_prob)), 4)
                from sklearn.metrics import roc_curve, precision_recall_curve, average_precision_score
                fpr, tpr, _ = roc_curve(y_test, y_prob)
                plots["roc_curve"] = {"fpr": fpr.tolist()[:200], "tpr": tpr.tolist()[:200], "auc": metrics["roc_auc"]}
                prec, rec, _ = precision_recall_curve(y_test, y_prob)
                plots["pr_curve"] = {"precision": prec.tolist()[:200], "recall": rec.tolist()[:200],
                                     "avg_precision": round(float(average_precision_score(y_test, y_prob)), 4)}
        except Exception:
            pass
        cm = confusion_matrix(y_test, y_pred)
        plots["confusion_matrix"] = {"matrix": cm.tolist(), "labels": sorted([str(v) for v in y.unique().tolist()])}

    elif task == "regression":
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        mae = float(mean_absolute_error(y_test, y_pred))
        mse = float(mean_squared_error(y_test, y_pred))
        rmse = float(np.sqrt(mse))
        r2 = float(r2_score(y_test, y_pred))
        n, p = len(y_test), X_test.shape[1]
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1) if n > p + 1 else r2
        metrics.update({"mae": round(mae, 4), "mse": round(mse, 4), "rmse": round(rmse, 4),
                         "r2": round(r2, 4), "adj_r2": round(adj_r2, 4)})
        y_pred_arr, y_test_arr = np.array(y_pred), np.array(y_test)
        residuals = y_test_arr - y_pred_arr
        sz = min(500, len(y_test_arr))
        idx = np.random.choice(len(y_test_arr), sz, replace=False)
        plots["residual_plot"] = {"y_pred": y_pred_arr[idx].tolist(), "residuals": residuals[idx].tolist(),
                                   "y_actual": y_test_arr[idx].tolist()}

    # Feature importance
    feature_importance = []
    try:
        if hasattr(model, "feature_importances_"):
            fi = sorted(zip(feature_names, model.feature_importances_), key=lambda x: x[1], reverse=True)
            feature_importance = [{"feature": f, "importance": round(float(imp), 6)} for f, imp in fi[:15]]
        elif hasattr(model, "coef_"):
            coef = model.coef_
            if coef.ndim > 1:
                coef = np.abs(coef).mean(axis=0)
            fi = sorted(zip(feature_names, np.abs(coef)), key=lambda x: x[1], reverse=True)
            feature_importance = [{"feature": f, "importance": round(float(imp), 6)} for f, imp in fi[:15]]
    except Exception:
        pass

    session_key = f"{model_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    MODEL_STORE[session_key] = {
        "model": model, "feature_names": feature_names, "model_id": model_id,
        "task": task, "hyperparams": best_params, "metrics": metrics,
        "training_date": datetime.now().isoformat(),
        "n_train_samples": len(X_train), "n_test_samples": len(X_test), "n_features": len(feature_names),
    }

    return {
        "success": True, "session_key": session_key, "model_id": model_id, "task": task,
        "training_time_seconds": round(duration, 2), "cv_score_mean": cv_mean, "cv_score_std": cv_std,
        "cv_metric": cv_scoring, "best_params": best_params, "metrics": metrics, "plots": plots,
        "feature_importance": feature_importance,
        "n_train_samples": len(X_train), "n_test_samples": len(X_test),
    }


# ─────────────────────────────────────────────────────────────
# EXPORT HELPERS
# ─────────────────────────────────────────────────────────────

def export_model_pickle(session_key: str) -> Optional[bytes]:
    entry = MODEL_STORE.get(session_key)
    if not entry:
        return None
    return pickle.dumps(entry["model"])


def generate_inference_code(session_key: str) -> str:
    entry = MODEL_STORE.get(session_key)
    if not entry:
        return ""
    fnames = entry.get("feature_names", [])
    return f'''import pickle
import pandas as pd
import numpy as np

# Load trained model
with open("model_{entry.get("model_id", "model")}.pkl", "rb") as f:
    model = pickle.load(f)

# Task: {entry.get("task", "unknown")}
# Features ({len(fnames)} total): {fnames[:5]}{"..." if len(fnames) > 5 else ""}

new_data = pd.read_csv("new_data.csv")
X_new = new_data[{json.dumps(fnames)}].fillna(0)

predictions = model.predict(X_new)
print("Predictions:", predictions[:5])
'''


def generate_model_card_md(session_key: str) -> str:
    entry = MODEL_STORE.get(session_key)
    if not entry:
        return "Model not found"
    metrics = entry.get("metrics", {})
    metrics_str = "\n".join([f"- **{k}**: {v}" for k, v in metrics.items() if not isinstance(v, dict)])
    return f"""# Model Card: {entry.get("model_id", "unknown")}

## Model Details
- **Model Type**: {entry.get("model_id", "N/A")}
- **Task**: {entry.get("task", "N/A")}
- **Training Date**: {entry.get("training_date", "N/A")}

## Training Data
- **Training Samples**: {entry.get("n_train_samples", "N/A")}
- **Test Samples**: {entry.get("n_test_samples", "N/A")}
- **Features**: {entry.get("n_features", "N/A")}

## Hyperparameters
```json
{json.dumps(entry.get("hyperparams", {}), indent=2)}
```

## Evaluation Metrics
{metrics_str}

## Inference
See the inference code snippet for instructions on loading and using this model.
"""
