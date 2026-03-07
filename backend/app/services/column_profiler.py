"""
Column Profiler: Analyzes and classifies dataset columns
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from functools import lru_cache
import hashlib


class ColumnMetadata:
    """Represents metadata for a single column"""
    
    def __init__(
        self,
        column_name: str,
        dtype: str,
        inferred_type: str,
        unique_count: int,
        null_count: int,
        sample_values: List[Any]
    ):
        self.column_name = column_name
        self.dtype = dtype
        self.inferred_type = inferred_type
        self.unique_count = unique_count
        self.null_count = null_count
        self.sample_values = sample_values
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'column_name': self.column_name,
            'dtype': self.dtype,
            'inferred_type': self.inferred_type,
            'unique_count': self.unique_count,
            'null_count': self.null_count,
            'sample_values': self.sample_values
        }


class ColumnProfiler:
    """
    Profiles dataset columns and classifies them as:
    - numeric: int64, float64 (continuous or discrete)
    - categorical: object, bool, low-cardinality int (≤ 20 unique values)
    - datetime: datetime64 or parseable date strings
    - high_cardinality: object with > 50% unique values (IDs, names)
    """
    
    HIGH_CARDINALITY_THRESHOLD = 0.5  # 50% uniqueness ratio
    LOW_CARDINALITY_INT_THRESHOLD = 20
    
    @staticmethod
    def _generate_cache_key(df: pd.DataFrame) -> str:
        """Generate a cache key based on dataframe shape and column names"""
        key_str = f"{df.shape}_{','.join(df.columns.tolist())}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    @classmethod
    @lru_cache(maxsize=100)
    def _cached_profile(cls, cache_key: str, df_tuple: tuple) -> Dict[str, ColumnMetadata]:
        """Cached profiling to avoid re-profiling same dataset"""
        # Reconstruct dataframe from tuple (this is a workaround for caching)
        # In production, use Redis or similar for proper caching
        return {}
    
    @classmethod
    def profile_columns(cls, df: pd.DataFrame) -> List[ColumnMetadata]:
        """
        Profile all columns in the dataframe and return metadata
        
        Args:
            df: Input pandas DataFrame
            
        Returns:
            List of ColumnMetadata objects
        """
        profiles = []
        total_rows = len(df)
        
        for col in df.columns:
            col_data = df[col]
            dtype = str(col_data.dtype)
            null_count = int(col_data.isna().sum())
            unique_count = int(col_data.nunique())
            
            # Get sample values (first 5 non-null unique values)
            sample_values = col_data.dropna().unique()[:5].tolist()
            # Convert to JSON-serializable types
            sample_values = [cls._make_serializable(v) for v in sample_values]
            
            # Infer column type
            inferred_type = cls._infer_column_type(col_data, unique_count, total_rows)
            
            metadata = ColumnMetadata(
                column_name=col,
                dtype=dtype,
                inferred_type=inferred_type,
                unique_count=unique_count,
                null_count=null_count,
                sample_values=sample_values
            )
            
            profiles.append(metadata)
        
        return profiles
    
    @classmethod
    def _infer_column_type(cls, col: pd.Series, unique_count: int, total_rows: int) -> str:
        """
        Infer the type of a column based on its properties
        
        Returns:
            "numeric" | "categorical" | "datetime" | "high_cardinality"
        """
        # Check for datetime
        if pd.api.types.is_datetime64_any_dtype(col):
            return "datetime"
        
        # Try to parse as datetime
        if col.dtype == 'object' and unique_count > 10:
            try:
                # Sample check - don't parse entire column
                sample = col.dropna().head(100)
                if len(sample) > 0:
                    pd.to_datetime(sample, errors='raise')
                    return "datetime"
            except:
                pass
        
        # Check for numeric types
        if pd.api.types.is_numeric_dtype(col):
            # Check if it's a low-cardinality integer (might be categorical)
            if pd.api.types.is_integer_dtype(col) and unique_count <= cls.LOW_CARDINALITY_INT_THRESHOLD:
                return "categorical"
            return "numeric"
        
        # Check for boolean
        if pd.api.types.is_bool_dtype(col):
            return "categorical"
        
        # For object types, check cardinality
        if col.dtype == 'object' or col.dtype.name == 'category':
            uniqueness_ratio = unique_count / max(total_rows - col.isna().sum(), 1)
            
            if uniqueness_ratio > cls.HIGH_CARDINALITY_THRESHOLD:
                return "high_cardinality"
            else:
                return "categorical"
        
        # Default to categorical
        return "categorical"
    
    @staticmethod
    def _make_serializable(value: Any) -> Any:
        """Convert numpy/pandas types to JSON-serializable types"""
        if pd.isna(value):
            return None
        if isinstance(value, (np.integer, np.floating)):
            return float(value) if isinstance(value, np.floating) else int(value)
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, (pd.Timestamp, np.datetime64)):
            return str(value)
        return str(value)
    
    @classmethod
    def get_columns_by_type(
        cls, 
        profiles: List[ColumnMetadata], 
        column_types: List[str]
    ) -> List[str]:
        """
        Get column names that match any of the specified types
        
        Args:
            profiles: List of column metadata
            column_types: List of types to filter by (e.g., ['numeric', 'datetime'])
            
        Returns:
            List of column names
        """
        return [
            p.column_name 
            for p in profiles 
            if p.inferred_type in column_types
        ]
