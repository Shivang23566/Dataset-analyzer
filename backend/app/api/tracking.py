import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.session import AnalysisSession
from app.models.download import Download
from app.models.dataset import Dataset

logger = logging.getLogger(__name__)


async def record_session(
    db: AsyncSession,
    user_id: int,
    session_key: str,
    session_type: str,
    filename: str,
    result_summary: dict[str, Any] | None = None,
) -> int | None:
    """
    Records an analysis session to the database.
    Returns the session id or None if it fails.
    Never raises — always safe to call.
    """
    try:
        # Find dataset_id by matching saved_filename for this user
        dataset_result = await db.execute(
            select(Dataset).where(
                Dataset.user_id == user_id,
                Dataset.saved_filename == filename,
                Dataset.is_deleted == False,
            )
        )
        dataset = dataset_result.scalar_one_or_none()
        dataset_id = dataset.id if dataset else None

        # Update last_accessed_at on the dataset
        if dataset:
            dataset.last_accessed_at = datetime.now(timezone.utc)

        session = AnalysisSession(
            user_id=user_id,
            dataset_id=dataset_id,
            session_key=session_key,
            session_type=session_type,
            status="completed",
            result_summary=json.dumps(result_summary)
            if result_summary else None,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session.id

    except Exception as e:
        logger.error(f"Session tracking failed (non-critical): {e}")
        try:
            await db.rollback()
        except Exception:
            pass
        return None


async def record_download(
    db: AsyncSession,
    user_id: int,
    session_id: int | None,
    file_type: str,
    original_filename: str,
    stored_path: str,
) -> None:
    """
    Records a file download to the database.
    Never raises — always safe to call.
    """
    try:
        download = Download(
            user_id=user_id,
            session_id=session_id,
            file_type=file_type,
            original_filename=original_filename,
            stored_path=stored_path,
        )
        db.add(download)
        await db.commit()
    except Exception as e:
        logger.error(f"Download tracking failed (non-critical): {e}")
        try:
            await db.rollback()
        except Exception:
            pass


def generate_session_key(prefix: str) -> str:
    """Generate a unique session key with given prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
