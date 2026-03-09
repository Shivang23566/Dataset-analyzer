"""
Chart Type Definitions and Axis Rules
"""
from __future__ import annotations
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class AxisRule:
    """Defines what column types are allowed for an axis"""
    allowed_types: Set[str]
    required: bool


@dataclass
class ChartTypeConfig:
    """Configuration for a specific chart type"""
    chart_type: str
    display_name: str
    x_axis_rule: AxisRule
    y_axis_rule: AxisRule
    supports_aggregation: bool = False
    supports_color_by: bool = False
    supports_size_by: bool = False
    max_data_points: Optional[int] = None  # For performance


class ChartRules:
    """
    Defines and enforces axis rules for all chart types
    
    | Chart Type  | X Axis Allowed Types         | Y Axis Allowed Types      | Y Required? |
    |-------------|------------------------------|---------------------------|-------------|
    | Bar         | categorical, datetime        | numeric                   | Yes         |
    | Line        | datetime, numeric            | numeric                   | Yes         |
    | Scatter     | numeric                      | numeric                   | Yes         |
    | Histogram   | numeric, categorical         | None (auto-generated)     | No          |
    | Pie         | categorical                  | numeric (optional)        | No          |
    | Box Plot    | categorical (optional)       | numeric                   | Yes         |
    | Heatmap     | categorical, numeric         | categorical, numeric      | Yes (needs both) |
    """
    
    CONFIGS: Dict[str, ChartTypeConfig] = {
        'bar': ChartTypeConfig(
            chart_type='bar',
            display_name='Bar Chart',
            x_axis_rule=AxisRule(
                allowed_types={'categorical', 'datetime'},
                required=True
            ),
            y_axis_rule=AxisRule(
                allowed_types={'numeric'},
                required=True
            ),
            supports_aggregation=True,
            supports_color_by=True,
            max_data_points=10000
        ),
        'line': ChartTypeConfig(
            chart_type='line',
            display_name='Line Chart',
            x_axis_rule=AxisRule(
                allowed_types={'datetime', 'numeric'},
                required=True
            ),
            y_axis_rule=AxisRule(
                allowed_types={'numeric'},
                required=True
            ),
            supports_aggregation=False,
            supports_color_by=True,
            max_data_points=5000
        ),
        'scatter': ChartTypeConfig(
            chart_type='scatter',
            display_name='Scatter Plot',
            x_axis_rule=AxisRule(
                allowed_types={'numeric'},
                required=True
            ),
            y_axis_rule=AxisRule(
                allowed_types={'numeric'},
                required=True
            ),
            supports_aggregation=False,
            supports_color_by=True,
            supports_size_by=True,
            max_data_points=10000
        ),
        'histogram': ChartTypeConfig(
            chart_type='histogram',
            display_name='Histogram',
            x_axis_rule=AxisRule(
                allowed_types={'numeric', 'categorical'},
                required=True
            ),
            y_axis_rule=AxisRule(
                allowed_types=set(),  # Auto-generated frequency
                required=False
            ),
            supports_aggregation=False,
            supports_color_by=False,
            max_data_points=50000
        ),
        'pie': ChartTypeConfig(
            chart_type='pie',
            display_name='Pie Chart',
            x_axis_rule=AxisRule(
                allowed_types={'categorical'},
                required=True
            ),
            y_axis_rule=AxisRule(
                allowed_types={'numeric'},
                required=False  # Optional: value_counts if not provided
            ),
            supports_aggregation=True,
            supports_color_by=False,
            max_data_points=None  # Will aggregate
        ),
        'boxplot': ChartTypeConfig(
            chart_type='boxplot',
            display_name='Box Plot',
            x_axis_rule=AxisRule(
                allowed_types={'categorical', 'datetime'},  # Optional grouping
                required=False
            ),
            y_axis_rule=AxisRule(
                allowed_types={'numeric'},
                required=True
            ),
            supports_aggregation=False,
            supports_color_by=True,
            max_data_points=20000
        ),
        'heatmap': ChartTypeConfig(
            chart_type='heatmap',
            display_name='Heatmap',
            x_axis_rule=AxisRule(
                allowed_types={'numeric'},  # For correlation matrix
                required=False  # Will use all numeric if not specified
            ),
            y_axis_rule=AxisRule(
                allowed_types={'numeric'},
                required=False
            ),
            supports_aggregation=False,
            supports_color_by=False,
            max_data_points=None  # Operates on correlation
        )
    }
    
    @classmethod
    def get_config(cls, chart_type: str) -> ChartTypeConfig:
        """Get configuration for a chart type"""
        config = cls.CONFIGS.get(chart_type.lower())
        if not config:
            raise ValueError(
                f"Unsupported chart type '{chart_type}'. "
                f"Supported types: {', '.join(cls.CONFIGS.keys())}"
            )
        return config
    
    @classmethod
    def get_valid_columns(
        cls,
        df: pd.DataFrame,
        column_profiles: List,  # List[ColumnMetadata]
        chart_type: str,
        axis: str,
        x_column: Optional[str] = None
    ) -> List[str]:
        """
        Get valid columns for the specified axis and chart type
        
        Args:
            df: The dataframe
            column_profiles: List of ColumnMetadata objects
            chart_type: Type of chart
            axis: "x" or "y"
            x_column: Already selected X column (to exclude from Y options)
            
        Returns:
            List of valid column names
        """
        config = cls.get_config(chart_type)
        
        if axis.lower() == 'x':
            rule = config.x_axis_rule
        elif axis.lower() == 'y':
            rule = config.y_axis_rule
        else:
            raise ValueError(f"Invalid axis '{axis}'. Must be 'x' or 'y'")
        
        # If no types allowed (e.g., histogram Y axis), return empty
        if not rule.allowed_types:
            return []
        
        # Filter columns by allowed types
        valid_columns = [
            prof.column_name
            for prof in column_profiles
            if prof.inferred_type in rule.allowed_types
        ]
        
        # For Y axis, exclude the already-selected X column
        if axis.lower() == 'y' and x_column and x_column in valid_columns:
            valid_columns.remove(x_column)
        
        return valid_columns
    
    @classmethod
    def validate_column_for_axis(
        cls,
        column_type: str,
        chart_type: str,
        axis: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if a column type is allowed for the given axis and chart type
        
        Returns:
            (is_valid, error_message)
        """
        config = cls.get_config(chart_type)
        rule = config.x_axis_rule if axis.lower() == 'x' else config.y_axis_rule
        
        if column_type not in rule.allowed_types:
            allowed = ', '.join(sorted(rule.allowed_types)) if rule.allowed_types else 'None'
            return False, (
                f"Column type '{column_type}' is not allowed for {axis.upper()} axis "
                f"in {config.display_name}. Allowed types: {allowed}"
            )
        
        return True, None
    
    @classmethod
    def is_y_required(cls, chart_type: str) -> bool:
        """Check if Y column is required for the chart type"""
        config = cls.get_config(chart_type)
        return config.y_axis_rule.required
    
    @classmethod
    def get_supported_chart_types(cls) -> List[str]:
        """Get list of all supported chart types"""
        return list(cls.CONFIGS.keys())
