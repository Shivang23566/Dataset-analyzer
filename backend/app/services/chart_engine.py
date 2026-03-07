"""
Chart Engine: Production-ready chart generation with registry pattern
Supports Dark Cosmos Theme and extensive customization options
"""
from __future__ import annotations
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Any, Optional, Dict, Callable, List
from abc import ABC, abstractmethod
import math

from .column_profiler import ColumnProfiler, ColumnMetadata
from .chart_rules import ChartRules


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

COSMOS_PALETTE = [COLOR_PRIMARY, COLOR_SKY, COLOR_VIOLET, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER]
COSMOS_GRADIENT = mcolors.LinearSegmentedColormap.from_list(
    'cosmos', [COLOR_PRIMARY, COLOR_SKY, COLOR_VIOLET]
)

# Configure matplotlib for Dark Cosmos Theme
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


class ChartGenerationError(Exception):
    """Custom exception for chart generation errors"""
    def __init__(self, message: str, code: str = "CHART_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class BaseChartHandler(ABC):
    """Abstract base class for chart handlers"""
    
    @abstractmethod
    def generate(
        self,
        df: pd.DataFrame,
        x_column: str,
        y_column: Optional[str] = None,
        **kwargs
    ) -> plt.Figure:
        """Generate the chart and return matplotlib figure"""
        pass
    
    @staticmethod
    def apply_standard_styling(ax, title: str, xlabel: str = '', ylabel: str = ''):
        """Apply consistent Dark Cosmos styling"""
        ax.set_title(title, pad=20, fontsize=14, fontweight=600, color=COLOR_TEXT_PRIMARY)
        
        if xlabel:
            ax.set_xlabel(xlabel, labelpad=10, fontsize=12, fontweight=500, color=COLOR_TEXT_PRIMARY)
        if ylabel:
            ax.set_ylabel(ylabel, labelpad=10, fontsize=12, fontweight=500, color=COLOR_TEXT_PRIMARY)
        
        ax.tick_params(axis='both', colors=COLOR_TEXT_MUTED, labelsize=10)
        
        # Rotate x labels if needed
        labels = ax.get_xticklabels()
        if len(labels) > 6 or any(len(str(l.get_text())) > 12 for l in labels):
            plt.setp(labels, rotation=45, horizontalalignment='right')
        
        ax.grid(True, alpha=0.2, color=COLOR_BORDER, linewidth=0.5, linestyle='-')
        ax.set_axisbelow(True)
        
        for spine in ax.spines.values():
            spine.set_color(COLOR_BORDER)
            spine.set_linewidth(1)
        
        plt.tight_layout()
    
    @staticmethod
    def limit_categories(df: pd.DataFrame, column: str, max_cat: int = 12) -> pd.DataFrame:
        """Limit categorical columns to top N categories"""
        if df[column].dtype == 'object' or df[column].dtype.name == 'category':
            counts = df[column].value_counts()
            if len(counts) > max_cat:
                top_cats = counts.head(max_cat).index
                df = df.copy()
                df[column] = df[column].apply(lambda x: x if x in top_cats else 'Other')
        return df


class BarChartHandler(BaseChartHandler):
    """Bar chart with aggregation support"""
    
    def generate(
        self,
        df: pd.DataFrame,
        x_column: str,
        y_column: Optional[str] = None,
        aggregation: str = 'mean',
        **kwargs
    ) -> plt.Figure:
        fig, ax = plt.subplots(figsize=(12, 7))
        
        if not y_column:
            raise ChartGenerationError(
                "Y column is required for bar charts",
                code="MISSING_Y_COLUMN"
            )
        
        # Handle datetime binning
        if pd.api.types.is_datetime64_any_dtype(df[x_column]):
            df = df.copy()
            # Auto-detect frequency
            date_range = (df[x_column].max() - df[x_column].min()).days
            if date_range > 365:
                freq = 'M'  # Monthly
                df['_plot_x'] = df[x_column].dt.to_period('M').astype(str)
            elif date_range > 30:
                freq = 'W'  # Weekly
                df['_plot_x'] = df[x_column].dt.to_period('W').astype(str)
            else:
                freq = 'D'  # Daily
                df['_plot_x'] = df[x_column].dt.date.astype(str)
            x_plot = '_plot_x'
        else:
            df = self.limit_categories(df, x_column, max_cat=15)
            x_plot = x_column
        
        # Aggregate data
        agg_func = getattr(np, aggregation, np.mean)
        plot_data = df.groupby(x_plot)[y_column].agg(agg_func).reset_index()
        plot_data = plot_data.sort_values(y_column, ascending=False).head(20)
        
        # Create bars
        bars = ax.bar(
            range(len(plot_data)),
            plot_data[y_column],
            color=[COSMOS_PALETTE[i % len(COSMOS_PALETTE)] for i in range(len(plot_data))],
            edgecolor=COLOR_BORDER,
            linewidth=1.5,
            alpha=0.9
        )
        
        # Add value labels
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=9, color=COLOR_TEXT_MUTED
            )
        
        ax.set_xticks(range(len(plot_data)))
        ax.set_xticklabels(plot_data[x_plot].astype(str), rotation=45, ha='right')
        
        title = f"{aggregation.capitalize()} {y_column} by {x_column}"
        self.apply_standard_styling(ax, title, x_column, f"{aggregation.capitalize()} {y_column}")
        
        return fig


class LineChartHandler(BaseChartHandler):
    """Line chart for trends over time or numeric sequences"""
    
    def generate(
        self,
        df: pd.DataFrame,
        x_column: str,
        y_column: Optional[str] = None,
        color_by: Optional[str] = None,
        **kwargs
    ) -> plt.Figure:
        if not y_column:
            raise ChartGenerationError(
                "Y column is required for line charts",
                code="MISSING_Y_COLUMN"
            )
        
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Sort by X
        plot_data = df[[x_column, y_column]].dropna().sort_values(x_column)
        
        if color_by and color_by in df.columns:
            # Multiple lines by category
            for i, (name, group) in enumerate(plot_data.groupby(df[color_by])):
                ax.plot(
                    group[x_column], group[y_column],
                    marker='o', linewidth=2.5, alpha=0.9,
                    color=COSMOS_PALETTE[i % len(COSMOS_PALETTE)],
                    label=str(name)
                )
            ax.legend()
        else:
            # Single line
            ax.plot(
                plot_data[x_column], plot_data[y_column],
                color=COLOR_PRIMARY, linewidth=3, alpha=0.9, label=y_column
            )
            ax.scatter(
                plot_data[x_column], plot_data[y_column],
                color=COLOR_SKY, s=80, alpha=0.8,
                edgecolors=COLOR_BORDER, linewidth=1.5, zorder=3
            )
            ax.fill_between(
                plot_data[x_column], plot_data[y_column],
                alpha=0.15, color=COLOR_PRIMARY
            )
        
        title = f"Trend: {y_column} vs {x_column}"
        self.apply_standard_styling(ax, title, x_column, y_column)
        
        return fig


class ScatterPlotHandler(BaseChartHandler):
    """Scatter plot with optional color and size encoding"""
    
    def generate(
        self,
        df: pd.DataFrame,
        x_column: str,
        y_column: Optional[str] = None,
        color_by: Optional[str] = None,
        size_by: Optional[str] = None,
        **kwargs
    ) -> plt.Figure:
        if not y_column:
            raise ChartGenerationError(
                "Y column is required for scatter plots",
                code="MISSING_Y_COLUMN"
            )
        
        fig, ax = plt.subplots(figsize=(12, 7))
        
        plot_data = df[[x_column, y_column]].dropna()
        
        # Determine colors
        if color_by and color_by in df.columns:
            if pd.api.types.is_numeric_dtype(df[color_by]):
                colors = df.loc[plot_data.index, color_by]
                cmap = COSMOS_GRADIENT
            else:
                # Categorical coloring
                categories = df.loc[plot_data.index, color_by].astype('category')
                colors = categories.cat.codes
                cmap = mcolors.ListedColormap(COSMOS_PALETTE)
        else:
            colors = range(len(plot_data))
            cmap = COSMOS_GRADIENT
        
        # Determine sizes
        if size_by and size_by in df.columns:
            sizes = df.loc[plot_data.index, size_by]
            sizes = (sizes - sizes.min()) / (sizes.max() - sizes.min()) * 200 + 50
        else:
            sizes = 100
        
        scatter = ax.scatter(
            plot_data[x_column], plot_data[y_column],
            c=colors, s=sizes, cmap=cmap,
            alpha=0.7, edgecolors=COLOR_BORDER, linewidth=1.5
        )
        
        # Add regression line
        try:
            z = np.polyfit(plot_data[x_column], plot_data[y_column], 1)
            p = np.poly1d(z)
            ax.plot(
                plot_data[x_column], p(plot_data[x_column]),
                color=COLOR_DANGER, linewidth=2.5,
                linestyle='--', alpha=0.8, label='Trend Line'
            )
            
            # Calculate correlation
            corr = plot_data[x_column].corr(plot_data[y_column])
            ax.text(
                0.05, 0.95, f'Correlation: {corr:.3f}',
                transform=ax.transAxes, fontsize=11,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor=COLOR_BG_DARK, edgecolor=COLOR_BORDER, alpha=0.9),
                color=COLOR_TEXT_PRIMARY
            )
        except:
            pass
        
        title = f"Scatter: {y_column} vs {x_column}"
        self.apply_standard_styling(ax, title, x_column, y_column)
        
        return fig


class HistogramHandler(BaseChartHandler):
    """Histogram with KDE overlay"""
    
    def generate(
        self,
        df: pd.DataFrame,
        x_column: str,
        y_column: Optional[str] = None,
        **kwargs
    ) -> plt.Figure:
        fig, ax = plt.subplots(figsize=(12, 7))
        
        data = df[x_column].dropna()
        
        if pd.api.types.is_numeric_dtype(data):
            # Numeric histogram with Sturges' rule for bins
            n = len(data)
            bins = math.ceil(math.log2(n) + 1) if n > 1 else 10
            bins = min(bins, 50)  # Cap at 50 bins
            
            n, bin_edges, patches = ax.hist(
                data, bins=bins, alpha=0.7,
                edgecolor=COLOR_BORDER, linewidth=1.5
            )
            
            # Color bars with gradient
            for i, patch in enumerate(patches):
                patch.set_facecolor(COSMOS_PALETTE[i % len(COSMOS_PALETTE)])
            
            # Add KDE overlay
            try:
                from scipy import stats
                kde_x = np.linspace(data.min(), data.max(), 200)
                kde = stats.gaussian_kde(data)
                kde_y = kde(kde_x) * len(data) * (bin_edges[1] - bin_edges[0])
                
                ax2 = ax.twinx()
                ax2.plot(kde_x, kde_y, color=COLOR_SKY, linewidth=3, alpha=0.8, label='KDE')
                ax2.fill_between(kde_x, kde_y, alpha=0.2, color=COLOR_SKY)
                ax2.set_ylabel('Density', color=COLOR_TEXT_PRIMARY, labelpad=10)
                ax2.tick_params(axis='y', colors=COLOR_TEXT_MUTED)
                ax2.spines['right'].set_color(COLOR_BORDER)
            except:
                pass
            
            # Add statistics
            stats_text = f'Mean: {data.mean():.2f}\\nMedian: {data.median():.2f}\\nStd: {data.std():.2f}'
            ax.text(
                0.97, 0.97, stats_text,
                transform=ax.transAxes, fontsize=10,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor=COLOR_BG_DARK, edgecolor=COLOR_BORDER, alpha=0.9),
                color=COLOR_TEXT_PRIMARY
            )
        else:
            # Categorical: use count plot
            counts = data.value_counts().head(20)
            bars = ax.bar(
                range(len(counts)), counts.values,
                color=[COSMOS_PALETTE[i % len(COSMOS_PALETTE)] for i in range(len(counts))],
                edgecolor=COLOR_BORDER, linewidth=1.5, alpha=0.9
            )
            ax.set_xticks(range(len(counts)))
            ax.set_xticklabels(counts.index.astype(str), rotation=45, ha='right')
        
        title = f"Distribution of {x_column}"
        self.apply_standard_styling(ax, title, x_column, "Frequency")
        
        return fig


class PieChartHandler(BaseChartHandler):
    """Pie chart with optional value aggregation"""
    
    def generate(
        self,
        df: pd.DataFrame,
        x_column: str,
        y_column: Optional[str] = None,
        aggregation: str = 'sum',
        **kwargs
    ) -> plt.Figure:
        fig, ax = plt.subplots(figsize=(10, 10))
        
        df = self.limit_categories(df, x_column, max_cat=8)
        
        if y_column:
            agg_func = getattr(np, aggregation, np.sum)
            data = df.groupby(x_column)[y_column].agg(agg_func).sort_values(ascending=False)
            title = f"{aggregation.capitalize()} {y_column} by {x_column}"
        else:
            data = df[x_column].value_counts()
            title = f"Distribution of {x_column}"
        
        # Collapse small slices (< 2%) into "Other"
        total = data.sum()
        threshold = total * 0.02
        small_slices = data[data < threshold]
        if len(small_slices) > 1:
            data = data[data >= threshold]
            data['Other'] = small_slices.sum()
        
        wedges, texts, autotexts = ax.pie(
            data.values, labels=data.index,
            autopct='%1.1f%%', startangle=90,
            colors=COSMOS_PALETTE * (len(data) // len(COSMOS_PALETTE) + 1),
            wedgeprops=dict(edgecolor=COLOR_BG_DARK, linewidth=3, antialiased=True),
            textprops=dict(color=COLOR_TEXT_PRIMARY, fontsize=11, fontweight=500)
        )
        
        for autotext in autotexts:
            autotext.set_color(COLOR_BG_DARK)
            autotext.set_fontsize(10)
            autotext.set_fontweight(600)
        
        ax.set_title(title, pad=20, fontsize=14, fontweight=600, color=COLOR_TEXT_PRIMARY)
        plt.tight_layout()
        
        return fig


class BoxPlotHandler(BaseChartHandler):
    """Box plot for distribution analysis"""
    
    def generate(
        self,
        df: pd.DataFrame,
        x_column: str,
        y_column: Optional[str] = None,
        **kwargs
    ) -> plt.Figure:
        if not y_column:
            raise ChartGenerationError(
                "Y column is required for box plots",
                code="MISSING_Y_COLUMN"
            )
        
        fig, ax = plt.subplots(figsize=(12, 7))
        
        if x_column:
            # Grouped box plot
            df = self.limit_categories(df, x_column, max_cat=10)
            box_data = [df[df[x_column] == cat][y_column].dropna() for cat in df[x_column].unique()]
            
            bp = ax.boxplot(
                box_data, labels=df[x_column].unique(),
                patch_artist=True, notch=True,
                boxprops=dict(facecolor=COLOR_PRIMARY, alpha=0.7, edgecolor=COLOR_BORDER, linewidth=1.5),
                whiskerprops=dict(color=COLOR_TEXT_MUTED, linewidth=1.5),
                capprops=dict(color=COLOR_TEXT_MUTED, linewidth=1.5),
                medianprops=dict(color=COLOR_SKY, linewidth=2.5),
                flierprops=dict(marker='o', markerfacecolor=COLOR_DANGER, markersize=6, alpha=0.6, markeredgecolor=COLOR_BORDER)
            )
            
            for i, box in enumerate(bp['boxes']):
                box.set_facecolor(COSMOS_PALETTE[i % len(COSMOS_PALETTE)])
            
            title = f"{y_column} Distribution by {x_column}"
            xlabel = x_column
        else:
            # Single box plot
            bp = ax.boxplot(
                [df[y_column].dropna()],
                vert=True, patch_artist=True, notch=True,
                boxprops=dict(facecolor=COLOR_PRIMARY, alpha=0.8, edgecolor=COLOR_BORDER, linewidth=2),
                whiskerprops=dict(color=COLOR_TEXT_MUTED, linewidth=2),
                capprops=dict(color=COLOR_TEXT_MUTED, linewidth=2),
                medianprops=dict(color=COLOR_SKY, linewidth=3),
                flierprops=dict(marker='o', markerfacecolor=COLOR_DANGER, markersize=8, alpha=0.7, markeredgecolor=COLOR_BORDER)
            )
            title = f"Statistical Summary: {y_column}"
            xlabel = ""
            ax.set_xticklabels([y_column])
        
        self.apply_standard_styling(ax, title, xlabel, y_column)
        
        return fig


class HeatmapHandler(BaseChartHandler):
    """Heatmap for correlation matrix"""
    
    def generate(
        self,
        df: pd.DataFrame,
        x_column: str,
        y_column: Optional[str] = None,
        **kwargs
    ) -> plt.Figure:
        # Get numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_cols) < 2:
            raise ChartGenerationError(
                "At least 2 numeric columns required for heatmap",
                code="INSUFFICIENT_NUMERIC_COLUMNS"
            )
        
        # Limit to reasonable number
        numeric_cols = numeric_cols[:15]
        
        fig, ax = plt.subplots(figsize=(12, 10))
        
        corr_matrix = df[numeric_cols].corr()
        
        im = ax.imshow(corr_matrix, cmap=COSMOS_GRADIENT, aspect='auto', vmin=-1, vmax=1)
        
        ax.set_xticks(range(len(numeric_cols)))
        ax.set_yticks(range(len(numeric_cols)))
        ax.set_xticklabels(numeric_cols, rotation=45, ha='right')
        ax.set_yticklabels(numeric_cols)
        
        # Add correlation values
        for i in range(len(numeric_cols)):
            for j in range(len(numeric_cols)):
                value = corr_matrix.iloc[i, j]
                text_color = COLOR_BG_DARK if abs(value) > 0.5 else COLOR_TEXT_PRIMARY
                ax.text(j, i, f'{value:.2f}',
                       ha='center', va='center',
                       color=text_color, fontsize=9, fontweight=500)
        
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Correlation', rotation=270, labelpad=20, color=COLOR_TEXT_PRIMARY)
        cbar.ax.tick_params(colors=COLOR_TEXT_MUTED)
        cbar.outline.set_edgecolor(COLOR_BORDER)
        
        ax.set_title("Correlation Heatmap", pad=20, fontsize=14, fontweight=600, color=COLOR_TEXT_PRIMARY)
        ax.tick_params(axis='both', colors=COLOR_TEXT_MUTED, labelsize=10)
        
        for spine in ax.spines.values():
            spine.set_color(COLOR_BORDER)
            spine.set_linewidth(1)
        
        plt.tight_layout()
        
        return fig


class ChartEngine:
    """
    Main chart generation engine with registry pattern for extensibility.
    Handles validation, profiling, performance optimization, and chart generation.
    """
    
    def __init__(self):
        self.profiler = ColumnProfiler()
        self.rules = ChartRules()
        self.handlers: Dict[str, BaseChartHandler] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register all default chart handlers"""
        self.handlers['bar'] = BarChartHandler()
        self.handlers['line'] = LineChartHandler()
        self.handlers['scatter'] = ScatterPlotHandler()
        self.handlers['histogram'] = HistogramHandler()
        self.handlers['pie'] = PieChartHandler()
        self.handlers['boxplot'] = BoxPlotHandler()
        self.handlers['heatmap'] = HeatmapHandler()
    
    def register_handler(self, chart_type: str, handler: BaseChartHandler):
        """Register a custom chart handler"""
        self.handlers[chart_type] = handler
    
    def get_column_profiles(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Profile all columns in the dataframe
        Returns list of column metadata dictionaries
        """
        profiles = self.profiler.profile_columns(df)
        return [profile.to_dict() for profile in profiles]
    
    def get_valid_columns_for_chart(
        self,
        df: pd.DataFrame,
        chart_type: str,
        axis: str
    ) -> List[str]:
        """
        Get valid column names for a specific chart type and axis.
        Uses column profiling to determine actual types.
        
        Args:
            df: Input dataframe
            chart_type: Type of chart (bar, line, scatter, etc.)
            axis: Which axis ('x' or 'y')
        
        Returns:
            List of valid column names
        """
        if chart_type not in self.handlers:
            raise ChartGenerationError(
                f"Unsupported chart type: {chart_type}",
                code="UNSUPPORTED_CHART"
            )
        
        profiles = self.profiler.profile_columns(df)
        
        valid_columns = self.rules.get_valid_columns(df, profiles, chart_type, axis)
        return valid_columns
    
    def validate_chart_request(
        self,
        df: pd.DataFrame,
        chart_type: str,
        x_column: str,
        y_column: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a chart generation request
        
        Returns:
            (is_valid, error_message)
        """
        if chart_type not in self.handlers:
            return False, f"Unsupported chart type: {chart_type}"
        
        if x_column not in df.columns:
            return False, f"Column '{x_column}' not found in dataset"
        
        if y_column and y_column not in df.columns:
            return False, f"Column '{y_column}' not found in dataset"
        
        # Check if Y is required for this chart type
        if not y_column and self.rules.is_y_required(chart_type):
            return False, f"Y column is required for {chart_type} charts"
        
        # Validate column types
        profiles = self.profiler.profile_columns(df)
        column_types = {p.column_name: p.inferred_type for p in profiles}
        
        # Validate X column
        x_valid = self.rules.validate_column_for_axis(
            column_types[x_column], chart_type, 'x'
        )
        if not x_valid:
            allowed = self.rules.get_config(chart_type).x_axis.allowed_types
            return False, f"Invalid X column type. Allowed types for {chart_type}: {', '.join(allowed)}"
        
        # Validate Y column if present
        if y_column:
            y_valid = self.rules.validate_column_for_axis(
                column_types[y_column], chart_type, 'y'
            )
            if not y_valid:
                allowed = self.rules.get_config(chart_type).y_axis.allowed_types
                return False, f"Invalid Y column type. Allowed types for {chart_type}: {', '.join(allowed)}"
        
        return True, None
    
    def _sample_dataframe(self, df: pd.DataFrame, max_rows: int = 10000) -> tuple[pd.DataFrame, bool]:
        """
        Sample large dataframes for performance
        
        Returns:
            (sampled_df, was_sampled)
        """
        if len(df) > max_rows:
            sampled = df.sample(n=max_rows, random_state=42)
            return sampled, True
        return df, False
    
    def generate_chart(
        self,
        df: pd.DataFrame,
        chart_type: str,
        x_column: str,
        y_column: Optional[str] = None,
        aggregation: str = 'mean',
        color_by: Optional[str] = None,
        size_by: Optional[str] = None,
        max_rows: int = 50000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a chart and return as base64 PNG
        
        Args:
            df: Input dataframe
            chart_type: Type of chart to generate
            x_column: Column for X axis
            y_column: Column for Y axis (optional for some charts)
            aggregation: Aggregation method (mean, sum, count, median)
            color_by: Column to color points by (scatter/line)
            size_by: Column to size points by (scatter)
            max_rows: Maximum rows before auto-sampling
            **kwargs: Additional chart-specific parameters
        
        Returns:
            {
                "success": bool,
                "image": str (base64 PNG) or None,
                "error": str or None,
                "error_code": str or None,
                "metadata": {
                    "rows_used": int,
                    "was_sampled": bool,
                    "chart_type": str
                }
            }
        """
        try:
            # Validate request
            is_valid, error_msg = self.validate_chart_request(df, chart_type, x_column, y_column)
            if not is_valid:
                return {
                    "success": False,
                    "image": None,
                    "error": error_msg,
                    "error_code": "VALIDATION_ERROR",
                    "metadata": None
                }
            
            # Sample if needed
            plot_df, was_sampled = self._sample_dataframe(df, max_rows)
            
            # Get handler
            handler = self.handlers[chart_type]
            
            # Generate chart
            fig = handler.generate(
                plot_df,
                x_column=x_column,
                y_column=y_column,
                aggregation=aggregation,
                color_by=color_by,
                size_by=size_by,
                **kwargs
            )
            
            # Convert to base64 PNG
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=COLOR_BG_DARK)
            buf.seek(0)
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
            
            return {
                "success": True,
                "image": image_base64,
                "error": None,
                "error_code": None,
                "metadata": {
                    "rows_used": len(plot_df),
                    "was_sampled": was_sampled,
                    "chart_type": chart_type,
                    "x_column": x_column,
                    "y_column": y_column
                }
            }
        
        except ChartGenerationError as e:
            return {
                "success": False,
                "image": None,
                "error": e.message,
                "error_code": e.code,
                "metadata": None
            }
        
        except Exception as e:
            return {
                "success": False,
                "image": None,
                "error": f"Unexpected error: {str(e)}",
                "error_code": "UNKNOWN_ERROR",
                "metadata": None
            }


# Singleton instance for convenience
_chart_engine_instance = None

def get_chart_engine() -> ChartEngine:
    """Get singleton ChartEngine instance"""
    global _chart_engine_instance
    if _chart_engine_instance is None:
        _chart_engine_instance = ChartEngine()
    return _chart_engine_instance
