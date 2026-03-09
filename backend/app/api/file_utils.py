"""Shared file-loading utilities for API endpoints."""
import os
import logging

import pandas as pd
from fastapi import HTTPException

logger = logging.getLogger(__name__)

UPLOAD_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "datasets")
)


def resolve_user_file(filename: str, user_id: int) -> str:
    """Return the absolute path for a file belonging to a specific user.

    Only looks in ``datasets/<user_id>/<filename>`` — strict per-user isolation.
    """
    safe_name = os.path.basename(filename)

    user_path = os.path.join(UPLOAD_FOLDER, str(user_id), safe_name)
    if os.path.isfile(user_path):
        return user_path

    raise HTTPException(status_code=404, detail=f"File not found: {filename}")


def load_df(filename: str, user_id: int) -> pd.DataFrame:
    """Load a CSV or JSON file as a DataFrame, resolving via user isolation."""
    path = resolve_user_file(filename, user_id)
    if path.endswith(".csv"):
        return pd.read_csv(path)
    elif path.endswith(".json"):
        return pd.read_json(path)
    raise HTTPException(status_code=400, detail="Unsupported file format")
