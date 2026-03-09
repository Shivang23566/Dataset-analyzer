"""
Accepts a pandas DataFrame and chart configuration, returns a Base64-encoded
image of the chart generated using Matplotlib and Seaborn.
Industry-grade visualization engine with Dark Cosmos Theme integration.
"""
from __future__ import annotations
import io
import base64
import logging
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ═══ DARK COSMOS THEME COLORS ═══
COLOR_PRIMARY = '#6366F1'      # Indigo
COLOR_SKY = '#0EA5E9'          # Sky Blue
COLOR_VIOLET = '#8B5CF6'       # Violet
COLOR_SUCCESS = '#10B981'      # Green
COLOR_WARNING = '#F59E0B'      # Amber
COLOR_DANGER = '#F43F5E'       # Rose
COLOR_BG_DARK = '#0D1221'      # Dark surface
COLOR_TEXT_PRIMARY = '#EFF2F7' # Light text
COLOR_TEXT_MUTED = '#8B9CB8'   # Muted text
COLOR_BORDER = '#1F2A3D'       # Border color

# Custom gradient palette for charts
COSMOS_PALETTE = [COLOR_PRIMARY, COLOR_SKY, COLOR_VIOLET, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER]
COSMOS_GRADIENT = mcolors.LinearSegmentedColormap.from_list(
    'cosmos', [COLOR_PRIMARY, COLOR_SKY, COLOR_VIOLET]
)

# Apply Dark Cosmos Theme to matplotlib
sns.set_theme(style="darkgrid", palette=COSMOS_PALETTE)
plt.rcParams.update({
    'figure.facecolor': COLOR_BG_DARK,
    'axes.facecolor': COLOR_BG_DARK,
    'axes.edgecolor': COLOR_BORDER,
    'axes.grid': True,
    'grid.color': COLOR_BORDER,
    'grid.alpha': 0.3,
    'grid.linewidth': 0.5,
    'axes.labelcolor': COLOR_TEXT_PRIMARY,
    'axes.titlecolor': COLOR_TEXT_PRIMARY,
    'text.color': COLOR_TEXT_PRIMARY,
    'xtick.color': COLOR_TEXT_MUTED,
    'ytick.color': COLOR_TEXT_MUTED,
    'font.family': 'sans-serif',
    'font.sans-serif': ['Inter', 'Segoe UI', 'Arial', 'DejaVu Sans'],
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'axes.titleweight': 600,
    'axes.labelweight': 500,
    'axes.titlepad': 20,
    'axes.labelpad': 8,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'legend.framealpha': 0.9,
    'legend.edgecolor': COLOR_BORDER,
    'legend.facecolor': COLOR_BG_DARK,
})

SUPPORTED_CHART_TYPES: set[str] = {
    "bar",
    "line",
    "pie",
    "scatter",
    "histogram",
    "boxplot",
    "heatmap",
}

_NUMERIC_CHART_TYPES: set[str] = {"line", "scatter", "histogram", "boxplot", "heatmap"}

def _error_response(message: str, code: str = "VISUALIZATION_ERROR") -> dict[str, Any]:
    return {"success": False, "error": message, "code": code}

def _get_base64_image() -> str:
    """Converts the current matplotlib figure to a base64 string with high resolution."""
    buf = io.BytesIO()
    plt.savefig(
        buf, 
        format='png', 
        bbox_inches='tight', 
        dpi=150,  # High quality for crisp charts
        facecolor=COLOR_BG_DARK,
        edgecolor='none',
        pad_inches=0.3
    )
    plt.close('all')  # Close all figures to free memory
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

def _prepare_categorical_data(df: pd.DataFrame, column: str, max_cat: int = 12) -> pd.DataFrame:
    """Caps the number of categories to avoid messy charts."""
    counts = df[column].value_counts()
    if len(counts) > max_cat:
        top_cats = counts.head(max_cat).index
        df = df.copy()
        df[column] = df[column].apply(lambda x: x if x in top_cats else 'Other')
    return df

def _apply_standard_styling(ax, title: str, xlabel: str = '', ylabel: str = ''):
    """Applies consistent Dark Cosmos styling."""
    ax.set_title(title, pad=20, fontsize=14, fontweight=600, color=COLOR_TEXT_PRIMARY)
    
    if xlabel:
        ax.set_xlabel(xlabel, labelpad=10, fontsize=12, fontweight=500, color=COLOR_TEXT_PRIMARY)
    if ylabel:
        ax.set_ylabel(ylabel, labelpad=10, fontsize=12, fontweight=500, color=COLOR_TEXT_PRIMARY)
    
    # Style tick labels
    ax.tick_params(axis='both', colors=COLOR_TEXT_MUTED, labelsize=10)
    
    # Rotate x labels if needed
    labels = ax.get_xticklabels()
    if len(labels) > 6 or any(len(str(l.get_text())) > 12 for l in labels):
        plt.setp(labels, rotation=45, horizontalalignment='right')
    
    # Apply dark theme grid
    ax.grid(True, alpha=0.2, color=COLOR_BORDER, linewidth=0.5, linestyle='-')
    ax.set_axisbelow(True)
    
    # Remove spines for cleaner look
    for spine in ax.spines.values():
        spine.set_color(COLOR_BORDER)
        spine.set_linewidth(1)
    
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
    """Enhanced bar chart with proper aggregation and gradient colors."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    if y_column:
        # Bar chart with Y axis - aggregate by mean
        err = _validate_numeric_column(df, y_column, "y_column")
        if err: return err
        
        # Check if x is categorical or numeric with few unique values
        if pd.api.types.is_numeric_dtype(df[x_column]) and df[x_column].nunique() > 20:
            # Bin numeric x column
            df = df.copy()
            df[f'{x_column}_binned'] = pd.cut(df[x_column], bins=10)
            x_col_plot = f'{x_column}_binned'
        else:
            df = _prepare_categorical_data(df, x_column, max_cat=15)
            x_col_plot = x_column
        
        # Aggregate data
        plot_data = df.groupby(x_col_plot)[y_column].mean().reset_index()
        plot_data = plot_data.sort_values(y_column, ascending=False).head(15)
        
        bars = ax.bar(
            range(len(plot_data)), 
            plot_data[y_column],
            color=COSMOS_PALETTE[:len(plot_data)] if len(plot_data) <= 6 else [COLOR_PRIMARY] * len(plot_data),
            edgecolor=COLOR_BORDER,
            linewidth=1.5,
            alpha=0.9
        )
        
        # Add gradient effect
        for i, bar in enumerate(bars):
            bar.set_facecolor(COSMOS_PALETTE[i % len(COSMOS_PALETTE)])
        
        ax.set_xticks(range(len(plot_data)))
        ax.set_xticklabels(plot_data[x_col_plot].astype(str), rotation=45, ha='right')
        title = f"Average {y_column} by {x_column}"
        ylabel = f"Mean {y_column}"
        xlabel = x_column
    else:
        # Count plot
        df = _prepare_categorical_data(df, x_column, max_cat=15)
        counts = df[x_column].value_counts().head(15)
        
        bars = ax.bar(
            range(len(counts)), 
            counts.values,
            color=[COSMOS_PALETTE[i % len(COSMOS_PALETTE)] for i in range(len(counts))],
            edgecolor=COLOR_BORDER,
            linewidth=1.5,
            alpha=0.9
        )
        
        ax.set_xticks(range(len(counts)))
        ax.set_xticklabels(counts.index.astype(str), rotation=45, ha='right')
        title = f"Distribution of {x_column}"
        ylabel = "Count"
        xlabel = x_column
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=9, color=COLOR_TEXT_MUTED)
    
    _apply_standard_styling(ax, title, xlabel, ylabel)
    return {"success": True, "image": _get_base64_image()}

def _build_line(df: pd.DataFrame, x_column: str, y_column: str) -> dict[str, Any]:
    """Enhanced line chart with gradient coloring and markers."""
    for col, label in ((x_column, "x_column"), (y_column, "y_column")):
        err = _validate_numeric_column(df, col, label)
        if err: return err
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Sort data for proper line chart
    plot_data = df[[x_column, y_column]].dropna().sort_values(x_column)
    
    # Plot line with gradient color
    ax.plot(
        plot_data[x_column], 
        plot_data[y_column],
        color=COLOR_PRIMARY,
        linewidth=3,
        alpha=0.9,
        label=y_column
    )
    
    # Add scatter points with different color
    ax.scatter(
        plot_data[x_column], 
        plot_data[y_column],
        color=COLOR_SKY,
        s=80,
        alpha=0.8,
        edgecolors=COLOR_BORDER,
        linewidth=1.5,
        zorder=3
    )
    
    # Fill area under curve
    ax.fill_between(
        plot_data[x_column], 
        plot_data[y_column],
        alpha=0.15,
        color=COLOR_PRIMARY
    )
    
    _apply_standard_styling(ax, f"Trend: {y_column} vs {x_column}", x_column, y_column)
    return {"success": True, "image": _get_base64_image()}

def _build_pie(df: pd.DataFrame, x_column: str, y_column: Optional[str]) -> dict[str, Any]:
    """Enhanced pie chart with modern styling and better labels."""
    df = _prepare_categorical_data(df, x_column, max_cat=8)
    fig, ax = plt.subplots(figsize=(10, 10))
    
    if y_column:
        err = _validate_numeric_column(df, y_column, "y_column")
        if err: return err
        data = df.groupby(x_column)[y_column].mean().sort_values(ascending=False)
        title = f"Average {y_column} by {x_column}"
    else:
        data = df[x_column].value_counts()
        title = f"Distribution of {x_column}"
    
    # Create pie chart with custom colors
    wedges, texts, autotexts = ax.pie(
        data.values,
        labels=data.index,
        autopct='%1.1f%%',
        startangle=90,
        colors=COSMOS_PALETTE * (len(data) // len(COSMOS_PALETTE) + 1),
        wedgeprops=dict(
            edgecolor=COLOR_BG_DARK,
            linewidth=3,
            antialiased=True
        ),
        textprops=dict(color=COLOR_TEXT_PRIMARY, fontsize=11, fontweight=500)
    )
    
    # Style percentage labels
    for autotext in autotexts:
        autotext.set_color(COLOR_BG_DARK)
        autotext.set_fontsize(10)
        autotext.set_fontweight(600)
    
    ax.set_title(title, pad=20, fontsize=14, fontweight=600, color=COLOR_TEXT_PRIMARY)
    plt.tight_layout()
    return {"success": True, "image": _get_base64_image()}

def _build_scatter(df: pd.DataFrame, x_column: str, y_column: str) -> dict[str, Any]:
    """Enhanced scatter plot with correlation line and gradient colors."""
    for col, label in ((x_column, "x_column"), (y_column, "y_column")):
        err = _validate_numeric_column(df, col, label)
        if err: return err
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Clean data
    plot_data = df[[x_column, y_column]].dropna()
    
    # Create scatter with gradient color based on density
    scatter = ax.scatter(
        plot_data[x_column], 
        plot_data[y_column],
        c=range(len(plot_data)),
        cmap=COSMOS_GRADIENT,
        s=100,
        alpha=0.7,
        edgecolors=COLOR_BORDER,
        linewidth=1.5
    )
    
    # Add regression line
    try:
        z = np.polyfit(plot_data[x_column], plot_data[y_column], 1)
        p = np.poly1d(z)
        ax.plot(
            plot_data[x_column], 
            p(plot_data[x_column]),
            color=COLOR_DANGER,
            linewidth=2.5,
            linestyle='--',
            alpha=0.8,
            label=f'Trend Line'
        )
        
        # Calculate correlation
        corr = plot_data[x_column].corr(plot_data[y_column])
        ax.text(
            0.05, 0.95, 
            f'Correlation: {corr:.3f}',
            transform=ax.transAxes,
            fontsize=11,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor=COLOR_BG_DARK, edgecolor=COLOR_BORDER, alpha=0.9),
            color=COLOR_TEXT_PRIMARY
        )
    except:
        pass
    
    _apply_standard_styling(ax, f"Scatter Plot: {x_column} vs {y_column}", x_column, y_column)
    return {"success": True, "image": _get_base64_image()}

def _build_histogram(df: pd.DataFrame, x_column: str) -> dict[str, Any]:
    """Enhanced histogram with KDE overlay and statistics."""
    err = _validate_numeric_column(df, x_column, "x_column")
    if err: return err
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Clean data
    data = df[x_column].dropna()
    
    # Plot histogram with gradient colors
    n, bins, patches = ax.hist(
        data,
        bins=30,
        alpha=0.7,
        edgecolor=COLOR_BORDER,
        linewidth=1.5
    )
    
    # Color bars with gradient
    for i, patch in enumerate(patches):
        patch.set_facecolor(COSMOS_PALETTE[i % len(COSMOS_PALETTE)])
    
    # Add KDE curve
    try:
        from scipy import stats
        kde_x = np.linspace(data.min(), data.max(), 200)
        kde = stats.gaussian_kde(data)
        kde_y = kde(kde_x)
        # Scale KDE to match histogram
        kde_y = kde_y * len(data) * (bins[1] - bins[0])
        
        ax2 = ax.twinx()
        ax2.plot(kde_x, kde_y, color=COLOR_SKY, linewidth=3, alpha=0.8, label='KDE')
        ax2.fill_between(kde_x, kde_y, alpha=0.2, color=COLOR_SKY)
        ax2.set_ylabel('Density', color=COLOR_TEXT_PRIMARY, labelpad=10)
        ax2.tick_params(axis='y', colors=COLOR_TEXT_MUTED)
        ax2.spines['right'].set_color(COLOR_BORDER)
    except:
        pass
    
    # Add statistics box
    stats_text = f'Mean: {data.mean():.2f}\nMedian: {data.median():.2f}\nStd: {data.std():.2f}'
    ax.text(
        0.97, 0.97, 
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment='top',
        horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor=COLOR_BG_DARK, edgecolor=COLOR_BORDER, alpha=0.9),
        color=COLOR_TEXT_PRIMARY
    )
    
    _apply_standard_styling(ax, f"Distribution of {x_column}", x_column, "Frequency")
    return {"success": True, "image": _get_base64_image()}

def _build_boxplot(df: pd.DataFrame, x_column: str, y_column: Optional[str]) -> dict[str, Any]:
    """Fixed boxplot logic: X=categorical, Y=numeric for grouped boxplot."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    if y_column:
        # Grouped boxplot: Y must be numeric (values), X should be categorical (groups)
        err = _validate_numeric_column(df, y_column, "y_column")
        if err: return err
        
        # Prepare categorical x_column
        df = _prepare_categorical_data(df, x_column, max_cat=10)
        
        # Create boxplot
        box_data = [df[df[x_column] == cat][y_column].dropna() for cat in df[x_column].unique()]
        bp = ax.boxplot(
            box_data,
            labels=df[x_column].unique(),
            patch_artist=True,
            notch=True,
            boxprops=dict(facecolor=COLOR_PRIMARY, alpha=0.7, edgecolor=COLOR_BORDER, linewidth=1.5),
            whiskerprops=dict(color=COLOR_TEXT_MUTED, linewidth=1.5),
            capprops=dict(color=COLOR_TEXT_MUTED, linewidth=1.5),
            medianprops=dict(color=COLOR_SKY, linewidth=2.5),
            flierprops=dict(marker='o', markerfacecolor=COLOR_DANGER, markersize=6, alpha=0.6, markeredgecolor=COLOR_BORDER)
        )
        
        # Color boxes with gradient
        for i, box in enumerate(bp['boxes']):
            box.set_facecolor(COSMOS_PALETTE[i % len(COSMOS_PALETTE)])
        
        title = f"{y_column} Distribution by {x_column}"
        xlabel = x_column
        ylabel = y_column
    else:
        # Single boxplot for numeric column
        err = _validate_numeric_column(df, x_column, "x_column")
        if err: return err
        
        bp = ax.boxplot(
            [df[x_column].dropna()],
            vert=True,
            patch_artist=True,
            notch=True,
            boxprops=dict(facecolor=COLOR_PRIMARY, alpha=0.8, edgecolor=COLOR_BORDER, linewidth=2),
            whiskerprops=dict(color=COLOR_TEXT_MUTED, linewidth=2),
            capprops=dict(color=COLOR_TEXT_MUTED, linewidth=2),
            medianprops=dict(color=COLOR_SKY, linewidth=3),
            flierprops=dict(marker='o', markerfacecolor=COLOR_DANGER, markersize=8, alpha=0.7, markeredgecolor=COLOR_BORDER)
        )
        
        title = f"Statistical Summary: {x_column}"
        xlabel = ""
        ylabel = x_column
        ax.set_xticklabels([x_column])
    
    _apply_standard_styling(ax, title, xlabel, ylabel)
    return {"success": True, "image": _get_base64_image()}

def _build_heatmap(df: pd.DataFrame, x_column: str, y_column: Optional[str]) -> dict[str, Any]:
    """Correlation heatmap for numeric columns with Dark Cosmos Theme."""
    # Get all numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if len(numeric_cols) < 2:
        return _error_response("At least 2 numeric columns required for heatmap.", code="INSUFFICIENT_NUMERIC_COLUMNS")
    
    # Limit to reasonable number of columns
    if len(numeric_cols) > 15:
        numeric_cols = numeric_cols[:15]
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Calculate correlation matrix
    corr_matrix = df[numeric_cols].corr()
    
    # Create heatmap with custom colormap
    im = ax.imshow(corr_matrix, cmap=COSMOS_GRADIENT, aspect='auto', vmin=-1, vmax=1)
    
    # Set ticks and labels
    ax.set_xticks(range(len(numeric_cols)))
    ax.set_yticks(range(len(numeric_cols)))
    ax.set_xticklabels(numeric_cols, rotation=45, ha='right')
    ax.set_yticklabels(numeric_cols)
    
    # Add correlation values as text
    for i in range(len(numeric_cols)):
        for j in range(len(numeric_cols)):
            value = corr_matrix.iloc[i, j]
            text_color = COLOR_BG_DARK if abs(value) > 0.5 else COLOR_TEXT_PRIMARY
            ax.text(j, i, f'{value:.2f}', 
                   ha='center', va='center', 
                   color=text_color, fontsize=9, fontweight=500)
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Correlation', rotation=270, labelpad=20, color=COLOR_TEXT_PRIMARY)
    cbar.ax.tick_params(colors=COLOR_TEXT_MUTED)
    cbar.outline.set_edgecolor(COLOR_BORDER)
    
    ax.set_title("Correlation Heatmap", pad=20, fontsize=14, fontweight=600, color=COLOR_TEXT_PRIMARY)
    ax.tick_params(axis='both', colors=COLOR_TEXT_MUTED, labelsize=10)
    
    # Style spines
    for spine in ax.spines.values():
        spine.set_color(COLOR_BORDER)
        spine.set_linewidth(1)
    
    plt.tight_layout()
    return {"success": True, "image": _get_base64_image()}

_CHART_BUILDERS: dict[str, Any] = {
    "bar": _build_bar,
    "line": _build_line,
    "pie": _build_pie,
    "scatter": _build_scatter,
    "histogram": _build_histogram,
    "boxplot": _build_boxplot,
    "heatmap": _build_heatmap,
}

def generate_visualization(
    df: pd.DataFrame,
    chart_type: str,
    x_column: str,
    y_column: Optional[str] = None,
) -> dict[str, Any]:
    """
    Generate industry-grade visualizations with Dark Cosmos Theme.
    
    Args:
        df: Input DataFrame
        chart_type: Type of chart (bar, line, scatter, histogram, pie, boxplot, heatmap)
        x_column: Column for X axis
        y_column: Column for Y axis (optional for some chart types)
    
    Returns:
        Dictionary with success status and base64 image or error message
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return _error_response("Invalid or empty DataFrame.", code="INVALID_INPUT")

    chart_type = chart_type.strip().lower()
    err = _validate_chart_type(chart_type)
    if err: return err

    # Heatmap doesn't require specific columns
    if chart_type == "heatmap":
        return _build_heatmap(df, x_column, y_column)

    err = _validate_column_exists(df, x_column, "x_column")
    if err: return err

    if y_column:
        err = _validate_column_exists(df, y_column, "y_column")
        if err: return err

    # Validate Y column requirement for specific chart types
    if chart_type in ("line", "scatter") and not y_column:
        return _require_y_column(y_column, chart_type)

    builder = _CHART_BUILDERS[chart_type]
    
    try:
        # Route to appropriate builder
        if chart_type in ("bar", "pie", "boxplot"):
            result = builder(df, x_column, y_column)
        elif chart_type == "histogram":
            result = builder(df, x_column)
        else:  # line, scatter
            result = builder(df, x_column, y_column)

        if result.get("success"):
            result["chart_type"] = chart_type
        return result
    except Exception as e:
        logger.exception("Chart generation failed: %s", e)
        return _error_response(f"Chart generation failed: {str(e)}", code="GENERATION_ERROR")