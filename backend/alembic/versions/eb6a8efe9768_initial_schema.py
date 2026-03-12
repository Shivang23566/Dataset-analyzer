"""initial_schema

Revision ID: eb6a8efe9768
Revises: 
Create Date: 2026-03-10 10:08:14.090621

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb6a8efe9768'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all application tables."""

    # ── users ──────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("email", sa.String, unique=True, index=True, nullable=False),
        sa.Column("hashed_password", sa.String, nullable=False),
        sa.Column("full_name", sa.String, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_superuser", sa.Boolean, default=False),
        sa.Column("subscription_plan", sa.String, default="free", nullable=False),
        sa.Column("subscription_status", sa.String, default="active", nullable=False),
        sa.Column("razorpay_customer_id", sa.String, nullable=True),
        sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── datasets ───────────────────────────────────────────────
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("original_filename", sa.String, nullable=False),
        sa.Column("saved_filename", sa.String, nullable=False),
        sa.Column("storage_path", sa.String, nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("col_count", sa.Integer, nullable=True),
        sa.Column("is_deleted", sa.Boolean, default=False, nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── analysis_sessions ──────────────────────────────────────
    op.create_table(
        "analysis_sessions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("dataset_id", sa.Integer, sa.ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_key", sa.String, unique=True, index=True, nullable=False),
        sa.Column("session_type", sa.String, nullable=False),
        sa.Column("status", sa.String, default="completed", nullable=False),
        sa.Column("result_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── downloads ──────────────────────────────────────────────
    op.create_table(
        "downloads",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("analysis_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("file_type", sa.String, nullable=False),
        sa.Column("original_filename", sa.String, nullable=False),
        sa.Column("stored_path", sa.String, nullable=False),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── subscriptions ──────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("plan", sa.String, default="free", nullable=False),
        sa.Column("status", sa.String, default="active", nullable=False),
        sa.Column("razorpay_subscription_id", sa.String, nullable=True),
        sa.Column("razorpay_customer_id", sa.String, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean, default=False, nullable=False),
    )

    # ── coupons ────────────────────────────────────────────────
    op.create_table(
        "coupons",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("code", sa.String, unique=True, index=True, nullable=False),
        sa.Column("discount_type", sa.String, default="full_access", nullable=False),
        sa.Column("duration_days", sa.Integer, default=30, nullable=False),
        sa.Column("max_uses", sa.Integer, default=1, nullable=False),
        sa.Column("uses_count", sa.Integer, default=0, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── coupon_redemptions ─────────────────────────────────────
    op.create_table(
        "coupon_redemptions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("coupon_id", sa.Integer, sa.ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── email_verifications ────────────────────────────────────
    op.create_table(
        "email_verifications",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("email", sa.String, index=True, nullable=False),
        sa.Column("otp_hash", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean, default=False),
        sa.Column("attempts", sa.Integer, default=0),
        sa.Column("temp_password_hash", sa.String, nullable=True),
        sa.Column("temp_full_name", sa.String, nullable=True),
    )

    # ── refresh_tokens ─────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token_hash", sa.String, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("refresh_tokens")
    op.drop_table("email_verifications")
    op.drop_table("coupon_redemptions")
    op.drop_table("coupons")
    op.drop_table("subscriptions")
    op.drop_table("downloads")
    op.drop_table("analysis_sessions")
    op.drop_table("datasets")
    op.drop_table("users")
