"""Chart Engine unit tests."""
import pytest
import base64
import pandas as pd
import numpy as np
from app.services.chart_engine import ChartEngine, ChartGenerationError, get_chart_engine


def make_sample_df(n=50):
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "x":    rng.normal(0, 1, n),
        "y":    rng.normal(5, 2, n),
        "cat":  rng.choice(["A", "B", "C"], n).astype(object),
        "size": rng.integers(1, 100, n).astype(float),
    })


# ── Singleton / Instance ──────────────────────────────────────

def test_get_chart_engine_returns_instance():
    engine = get_chart_engine()
    assert isinstance(engine, ChartEngine)


def test_get_chart_engine_singleton():
    engine1 = get_chart_engine()
    engine2 = get_chart_engine()
    assert engine1 is engine2


# ── Histogram ────────────────────────────────────────────────

def test_histogram_generates_image():
    engine = get_chart_engine()
    df = make_sample_df()
    result = engine.generate_chart(df, chart_type="histogram", x_column="x")
    assert result["success"] is True
    assert result["image"] is not None
    # Verify it's valid base64
    decoded = base64.b64decode(result["image"])
    assert len(decoded) > 0


def test_histogram_metadata():
    engine = get_chart_engine()
    df = make_sample_df()
    result = engine.generate_chart(df, chart_type="histogram", x_column="x")
    assert result["success"] is True
    meta = result["metadata"]
    assert meta["chart_type"] == "histogram"
    assert meta["rows_used"] == len(df)


# ── Bar Chart ────────────────────────────────────────────────

def test_bar_chart_generates_image():
    engine = get_chart_engine()
    df = make_sample_df()
    result = engine.generate_chart(df, chart_type="bar", x_column="cat", y_column="size")
    assert result["success"] is True
    assert result["image"] is not None
    decoded = base64.b64decode(result["image"])
    assert len(decoded) > 0


def test_bar_chart_without_y_fails():
    """Bar charts require a y_column."""
    engine = get_chart_engine()
    df = make_sample_df()
    result = engine.generate_chart(df, chart_type="bar", x_column="cat")
    assert result["success"] is False
    assert result["error"] is not None


# ── Scatter Plot ─────────────────────────────────────────────

def test_scatter_plot_generates_image():
    engine = get_chart_engine()
    df = make_sample_df()
    result = engine.generate_chart(df, chart_type="scatter", x_column="x", y_column="y")
    assert result["success"] is True
    assert result["image"] is not None
    decoded = base64.b64decode(result["image"])
    assert len(decoded) > 0


def test_scatter_plot_metadata():
    engine = get_chart_engine()
    df = make_sample_df()
    result = engine.generate_chart(df, chart_type="scatter", x_column="x", y_column="y")
    assert result["success"] is True
    assert result["metadata"]["x_column"] == "x"
    assert result["metadata"]["y_column"] == "y"


def test_scatter_without_y_fails():
    engine = get_chart_engine()
    df = make_sample_df()
    result = engine.generate_chart(df, chart_type="scatter", x_column="x")
    assert result["success"] is False


# ── Invalid chart type ────────────────────────────────────────

def test_invalid_chart_type_returns_failure():
    engine = get_chart_engine()
    df = make_sample_df()
    result = engine.generate_chart(df, chart_type="does_not_exist", x_column="x")
    assert result["success"] is False
    assert result["image"] is None
    assert result["error"] is not None


# ── Missing column ────────────────────────────────────────────

def test_missing_x_column_returns_failure():
    engine = get_chart_engine()
    df = make_sample_df()
    result = engine.generate_chart(df, chart_type="histogram", x_column="no_such_col")
    assert result["success"] is False
    assert result["image"] is None


# ── Image is valid PNG ────────────────────────────────────────

def test_output_is_png_image():
    """Verify the base64 image decodes to a valid PNG (starts with PNG magic bytes)."""
    engine = get_chart_engine()
    df = make_sample_df()
    result = engine.generate_chart(df, chart_type="histogram", x_column="x")
    assert result["success"] is True
    raw = base64.b64decode(result["image"])
    # PNG magic bytes: \x89PNG
    assert raw[:4] == b'\x89PNG'
