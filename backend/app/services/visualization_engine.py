"""
Accepts a pandas DataFrame and chart configuration, returns a Base64-encoded
image of the chart generated using Matplotlib and Seaborn.
"""
from __future__ import annotations
import io
import base64
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from typing import Any, Optional

# Set default theme
sns.set_theme(style="white", palette="muted")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Inter', 'Work Sans', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.labelcolor'] = '#4a5568'
plt.rcParams['axes.edgecolor'] = '#cbd5e0'
plt.rcParams['xtick.color'] = '#4a5568'
plt.rcParams['ytick.color'] = '#4a5568'
plt.rcParams['axes.titlepad'] = 20
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.titleweight'] = 'bold'

SUPPORTED_CHART_TYPES: set[str] = {
    "bar",
    "line",
    "pie",
    "scatter",
    "histogram",
    "boxplot",
}

_NUMERIC_CHART_TYPES: set[str] = {"line", "scatter", "histogram", "boxplot"}

def _error_response(message: str, code: str = "VISUALIZATION_ERROR") -> dict[str, Any]:
    return {"success": False, "error": message, "code": code}

def _get_base64_image() -> str:
    """Converts the current matplotlib figure to a base64 string with high resolution."""
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300, transparent=False)
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

def _prepare_categorical_data(df: pd.DataFrame, column: str, max_cat: int = 15) -> pd.DataFrame:
    """Caps the number of categories to avoid messy charts."""
    counts = df[column].value_counts()
    if len(counts) > max_cat:
        top_cats = counts.head(max_cat).index
        df = df.copy()
        df[column] = df[column].apply(lambda x: x if x in top_cats else 'Others')
    return df

def _apply_standard_styling(ax, title: str, xlabel: str, ylabel: str):
    """Applies consistent styling and prevents label overlapping."""
    ax.set_title(title, pad=20)
    ax.set_xlabel(xlabel, labelpad=10)
    ax.set_ylabel(ylabel, labelpad=10)
    
    # Rotate x labels if they are too long or too many
    labels = ax.get_xticklabels()
    if len(labels) > 5 or any(len(l.get_text()) > 10 for l in labels):
        plt.setp(labels, rotation=45, horizontalalignment='right')
    
    sns.despine()
    plt.tight_layout()

def _validate_chart_type(chart_type: str) -> Optional[dict[str, Any]]:
    if chart_type not in SUPPORTED_CHART_TYPES:
        supported = ", ".join(sorted(SUPPORTED_CHART_TYPES))
        return _error_response(
            f"Unsupported chart type '{chart_type}'. Supported types: {supported}.",
            code="INVALID_CHART_TYPE",
        )
    return None

def _validate_column_exists(df: pd.DataFrame, column: str, label: str = "column") -> Optional[dict[str, Any]]:
    if column not in df.columns:
        available = ", ".join(df.columns.tolist())
        return _error_response(
            f"Column '{column}' not found for {label}. Available columns: {available}.",
            code="COLUMN_NOT_FOUND",
        )
    return None

def _validate_numeric_column(df: pd.DataFrame, column: str, label: str = "column") -> Optional[dict[str, Any]]:
    if not pd.api.types.is_numeric_dtype(df[column]):
        return _error_response(
            f"Column '{column}' ({label}) must be numeric for this chart type. "
            f"Detected dtype: {df[column].dtype}.",
            code="NON_NUMERIC_COLUMN",
        )
    return None

def _require_y_column(y_column: Optional[str], chart_type: str) -> Optional[dict[str, Any]]:
    if not y_column:
        return _error_response(
            f"'y_column' is required for chart type '{chart_type}'.",
            code="MISSING_Y_COLUMN",
        )
    return None

def _build_bar(df: pd.DataFrame, x_column: str, y_column: Optional[str]) -> dict[str, Any]:
    df = _prepare_categorical_data(df, x_column)
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if y_column:
        err = _validate_numeric_column(df, y_column, "y_column")
        if err: return err
        sns.barplot(data=df, x=x_column, y=y_column, palette="viridis", hue=x_column, legend=False, ax=ax)
        title, ylabel = f"Average {y_column} by {x_column}", f"Mean {y_column}"
    else:
        sns.countplot(data=df, x=x_column, palette="viridis", hue=x_column, legend=False, ax=ax)
        title, ylabel = f"Frequency of {x_column}", "Count"
    
    _apply_standard_styling(ax, title, x_column, ylabel)
    return {"success": True, "image": _get_base64_image()}

def _build_line(df: pd.DataFrame, x_column: str, y_column: str) -> dict[str, Any]:
    for col, label in ((x_column, "x_column"), (y_column, "y_column")):
        err = _validate_numeric_column(df, col, label)
        if err: return err
    
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.lineplot(data=df.sort_values(x_column), x=x_column, y=y_column, marker='o', color='#a747eb', linewidth=2.5, ax=ax)
    _apply_standard_styling(ax, f"Trend: {y_column} vs {x_column}", x_column, y_column)
    return {"success": True, "image": _get_base64_image()}

def _build_pie(df: pd.DataFrame, x_column: str, y_column: Optional[str]) -> dict[str, Any]:
    df = _prepare_categorical_data(df, x_column, max_cat=10)
    fig, ax = plt.subplots(figsize=(8, 8))
    
    if y_column:
        err = _validate_numeric_column(df, y_column, "y_column")
        if err: return err
        data = df.groupby(x_column)[y_column].mean()
        title = f"Component Wise Average of {y_column}"
    else:
        data = df[x_column].value_counts()
        title = f"Data Distribution: {x_column}"
    
    data.plot.pie(autopct='%1.1f%%', startangle=140, cmap='Pastel1', ax=ax, wedgeprops={'edgecolor': 'white', 'linewidth': 1.5})
    ax.set_ylabel('')
    ax.set_title(title, pad=20, weight='bold')
    plt.tight_layout()
    return {"success": True, "image": _get_base64_image()}

def _build_scatter(df: pd.DataFrame, x_column: str, y_column: str) -> dict[str, Any]:
    for col, label in ((x_column, "x_column"), (y_column, "y_column")):
        err = _validate_numeric_column(df, col, label)
        if err: return err
    
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(data=df, x=x_column, y=y_column, color='#a747eb', alpha=0.6, s=100, edgecolor='white', ax=ax)
    _apply_standard_styling(ax, f"Correlation: {x_column} vs {y_column}", x_column, y_column)
    return {"success": True, "image": _get_base64_image()}

def _build_histogram(df: pd.DataFrame, x_column: str) -> dict[str, Any]:
    err = _validate_numeric_column(df, x_column, "x_column")
    if err: return err
    
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(data=df, x=x_column, kde=True, color='#a747eb', alpha=0.5, ax=ax)
    _apply_standard_styling(ax, f"Distribution Density: {x_column}", x_column, "Frequency")
    return {"success": True, "image": _get_base64_image()}

def _build_boxplot(df: pd.DataFrame, x_column: str, y_column: Optional[str]) -> dict[str, Any]:
    err = _validate_numeric_column(df, x_column, "x_column")
    if err: return err
    
    fig, ax = plt.subplots(figsize=(10, 6))
    if y_column:
        df = _prepare_categorical_data(df, y_column)
        sns.boxplot(data=df, x=y_column, y=x_column, palette="Set3", hue=y_column, legend=False, ax=ax)
        title = f"{x_column} Distribution by {y_column}"
        xlabel = y_column
    else:
        sns.boxplot(data=df, y=x_column, color='#a747eb', ax=ax)
        title = f"Statistical Summary: {x_column}"
        xlabel = ""
    
    _apply_standard_styling(ax, title, xlabel, x_column)
    return {"success": True, "image": _get_base64_image()}

_CHART_BUILDERS: dict[str, Any] = {
    "bar": _build_bar,
    "line": _build_line,
    "pie": _build_pie,
    "scatter": _build_scatter,
    "histogram": _build_histogram,
    "boxplot": _build_boxplot,
}

def generate_visualization(
    df: pd.DataFrame,
    chart_type: str,
    x_column: str,
    y_column: Optional[str] = None,
) -> dict[str, Any]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return _error_response("Invalid or empty DataFrame.", code="INVALID_INPUT")

    chart_type = chart_type.strip().lower()
    err = _validate_chart_type(chart_type)
    if err: return err

    err = _validate_column_exists(df, x_column, "x_column")
    if err: return err

    if y_column:
        err = _validate_column_exists(df, y_column, "y_column")
        if err: return err

    if chart_type in _NUMERIC_CHART_TYPES - {"histogram", "boxplot"} and not y_column:
        return _require_y_column(y_column, chart_type)

    builder = _CHART_BUILDERS[chart_type]
    if chart_type in ("bar", "pie", "boxplot"):
        result = builder(df, x_column, y_column)
    elif chart_type == "histogram":
        result = builder(df, x_column)
    else:
        result = builder(df, x_column, y_column)

    if result.get("success"):
        result["chart_type"] = chart_type
    return result