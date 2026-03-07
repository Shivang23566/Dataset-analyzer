
"""
EDA Engine Module for Dataset Analysis for FastAPI backend
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Union


def analyze_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Performs comprehensive exploratory data analysis on a pandas DataFrame.
    
    Args:
        df (pd.DataFrame): Input DataFrame to analyze
        
    Returns:
        dict: JSON-serializable dictionary containing EDA results
    """
    
    # Handle empty DataFrame edge case
    if df.empty:
        return {
            "shape": {"rows": 0, "columns": 0},
            "column_info": {},
            "numeric_summary": {},
            "correlation_matrix": {},
            "missing_summary": {"total_missing": 0}
        }
    
    # Basic shape information
    shape_info = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1])
    }
    
    # Identify numerical and categorical columns
    numerical_columns = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_columns = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
    
    # Column info (combines data types, missing values, and unique counts)
    column_info = {}
    total_missing = 0
    
    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        total_missing += missing_count
        missing_pct = float((missing_count / len(df) * 100) if len(df) > 0 else 0)
        unique_count = int(df[col].nunique())
        
        column_info[col] = {
            "dtype": str(df[col].dtype),
            "missing_pct": round(missing_pct, 2),
            "unique": unique_count
        }
    
    # Numeric summary (descriptive statistics)
    numeric_summary = {}
    for col in numerical_columns:
        col_data = df[col].dropna()
        
        if len(col_data) > 0:
            numeric_summary[col] = {
                "mean": float(col_data.mean()),
                "median": float(col_data.median()),
                "std": float(col_data.std()),
                "min": float(col_data.min()),
                "max": float(col_data.max())
            }
    
    # Correlation matrix for numerical columns
    correlation_matrix = {}
    if len(numerical_columns) >= 2:
        corr_matrix = df[numerical_columns].corr()
        
        for col in corr_matrix.columns:
            correlation_matrix[col] = {
                row: (None if pd.isna(val) else float(val))
                for row, val in corr_matrix[col].items()
            }
    
    # Missing summary
    missing_summary = {
        "total_missing": total_missing
    }
    
    # Assemble final result in the format expected by frontend
    result = {
        "shape": shape_info,
        "column_info": column_info,
        "numeric_summary": numeric_summary,
        "correlation_matrix": correlation_matrix,
        "missing_summary": missing_summary
    }
    
    return result


# Keep the old helper functions for backward compatibility if needed
def _analyze_missing_values(df: pd.DataFrame) -> Dict[str, Dict[str, Union[int, float]]]:
    """
    Analyzes missing values in the DataFrame.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        dict: Dictionary with missing value counts and percentages per column
    """
    missing_info = {}
    total_rows = len(df)
    
    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        missing_percentage = float((missing_count / total_rows * 100) if total_rows > 0 else 0)
        
        missing_info[col] = {
            "count": missing_count,
            "percentage": round(missing_percentage, 2)
        }
    
    return missing_info


def _compute_descriptive_statistics(df: pd.DataFrame, numerical_columns: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Computes descriptive statistics for numerical columns.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        numerical_columns (List[str]): List of numerical column names
        
    Returns:
        dict: Descriptive statistics for each numerical column
    """
    if not numerical_columns:
        return {}
    
    stats = {}
    
    for col in numerical_columns:
        col_data = df[col].dropna()
        
        if len(col_data) == 0:
            stats[col] = {
                "count": 0,
                "mean": None,
                "std": None,
                "min": None,
                "25%": None,
                "50%": None,
                "75%": None,
                "max": None
            }
        else:
            stats[col] = {
                "count": int(col_data.count()),
                "mean": float(col_data.mean()),
                "std": float(col_data.std()),
                "min": float(col_data.min()),
                "25%": float(col_data.quantile(0.25)),
                "50%": float(col_data.quantile(0.50)),
                "75%": float(col_data.quantile(0.75)),
                "max": float(col_data.max())
            }
    
    return stats


def _compute_correlation_matrix(df: pd.DataFrame, numerical_columns: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Computes correlation matrix for numerical columns.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        numerical_columns (List[str]): List of numerical column names
        
    Returns:
        dict: Correlation matrix as nested dictionary
    """
    # Handle edge cases: no numerical columns or only one numerical column
    if len(numerical_columns) < 2:
        return {}
    
    # Compute correlation matrix
    corr_matrix = df[numerical_columns].corr()
    
    # Convert to JSON-serializable nested dictionary
    # Replace NaN values with None for JSON compatibility
    correlation_dict = {}
    for col in corr_matrix.columns:
        correlation_dict[col] = {
            row: (None if pd.isna(val) else float(val))
            for row, val in corr_matrix[col].items()
        }
    
    return correlation_dict
