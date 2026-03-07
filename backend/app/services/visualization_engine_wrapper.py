"""
Visualization Engine Wrapper - backwards compatible interface
Delegates to the new ChartEngine system
"""
import pandas as pd
from typing import Any, Optional
from .chart_engine import get_chart_engine


def generate_visualization(
    df: pd.DataFrame,
    chart_type: str,
    x_column: str,
    y_column: Optional[str] = None,
    **kwargs
) -> dict[str, Any]:
    """
    Generate a visualization - backwards compatible interface
    
    Args:
        df: Input dataframe
        chart_type: Type of chart (bar, line, scatter, histogram, pie, boxplot, heatmap)
        x_column: Column for X axis
        y_column: Column for Y axis (optional for some charts)
        **kwargs: Additional parameters (aggregation, color_by, size_by, etc.)
    
    Returns:
        {
            "success": bool,
            "image": str (base64 PNG) or None,
            "error": str or None,
            "code": str or None
        }
    """
    engine = get_chart_engine()
    
    result = engine.generate_chart(
        df=df,
        chart_type=chart_type,
        x_column=x_column,
        y_column=y_column,
        **kwargs
    )
    
    # Transform response format for backwards compatibility
    if result["success"]:
        return {
            "success": True,
            "image": result["image"],
            "error": None,
            "code": None
        }
    else:
        return {
            "success": False,
            "image": None,
            "error": result["error"],
            "code": result["error_code"]
        }


def get_column_metadata(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Get column metadata using the new profiling system
    
    Returns:
        List of column metadata dictionaries with:
        - column_name
        - dtype
        - inferred_type (numeric, categorical, datetime, high_cardinality)
        - unique_count
        - null_count
        - sample_values
    """
    engine = get_chart_engine()
    return engine.get_column_profiles(df)


def get_valid_columns(df: pd.DataFrame, chart_type: str, axis: str) -> list[str]:
    """
    Get valid columns for a specific chart type and axis
    
    Args:
        df: Input dataframe
        chart_type: Type of chart
        axis: 'x' or 'y'
    
    Returns:
        List of valid column names
    """
    engine = get_chart_engine()
    return engine.get_valid_columns_for_chart(df, chart_type, axis)
