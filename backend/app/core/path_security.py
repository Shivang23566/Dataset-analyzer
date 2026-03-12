"""
Secure Path Handling Module

Provides utilities for secure file path operations to prevent:
- Path traversal attacks (../ sequences)
- Null byte injection
- Symbolic link attacks
- Absolute path injection

All file operations in the application should use these utilities.
"""

import os
import re
import unicodedata
from pathlib import Path
from typing import Tuple
import logging

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security.path")


class PathTraversalError(Exception):
    """Raised when a path traversal attempt is detected."""


class InvalidFilenameError(Exception):
    """Raised when a filename contains invalid characters."""


# Characters that are never allowed in filenames
FORBIDDEN_CHARS = set('<>:"|?*\x00')

# Patterns that indicate traversal attempts
TRAVERSAL_REGEX = re.compile(
    r'\.\./|\.\.\\|^/|^[A-Za-z]:|\\x00'
)

# Maximum filename length (most filesystems support 255)
MAX_FILENAME_LENGTH = 200


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to remove dangerous characters and patterns.

    Removes path traversal sequences, null bytes, forbidden chars,
    normalizes Unicode, limits length, and strips leading/trailing dots.

    Raises InvalidFilenameError if the result is empty or invalid.
    """
    if not filename:
        raise InvalidFilenameError("Filename cannot be empty")

    original = filename

    # Normalize Unicode (NFC) then strip non-ASCII
    filename = unicodedata.normalize('NFKC', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')

    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Take just the basename (strips directory components)
    filename = os.path.basename(filename)

    # Remove forbidden characters
    for ch in FORBIDDEN_CHARS:
        filename = filename.replace(ch, '')

    # Replace path separators
    filename = filename.replace('/', '_').replace('\\', '_')

    # Collapse consecutive dots
    while '..' in filename:
        filename = filename.replace('..', '.')

    # Collapse consecutive underscores
    while '__' in filename:
        filename = filename.replace('__', '_')

    # Strip leading/trailing whitespace and dots
    filename = filename.strip(' .')

    # Truncate while preserving extension
    if len(filename) > MAX_FILENAME_LENGTH:
        name, ext = os.path.splitext(filename)
        filename = name[: MAX_FILENAME_LENGTH - len(ext)] + ext

    if not filename or filename in ('.', '..'):
        raise InvalidFilenameError(
            f"Filename '{original}' is invalid after sanitization"
        )

    if filename != os.path.basename(original):
        security_logger.warning(
            "FILENAME_SANITIZED | original='%s' | sanitized='%s'",
            original, filename,
        )

    return filename


def validate_file_extension(
    filename: str,
    allowed_extensions: set[str],
) -> Tuple[str, str]:
    """Validate and extract file extension.

    *allowed_extensions* should contain lowercase strings with leading dot,
    e.g. ``{'.csv', '.json'}``.

    Returns ``(name, extension)`` or raises ``InvalidFilenameError``.
    """
    name, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    if ext_lower not in allowed_extensions:
        raise InvalidFilenameError(
            f"File extension '{ext}' not allowed. Allowed: {allowed_extensions}"
        )
    return name, ext_lower


def resolve_safe_path(
    base_dir: str | Path,
    user_path: str,
    create_dirs: bool = False,
) -> Path:
    """Safely resolve *user_path* within *base_dir*.

    Blocks path-traversal attempts, null-byte injection, and symlink escapes.
    Returns a resolved ``Path`` guaranteed to reside inside *base_dir*.

    Raises ``PathTraversalError`` on any violation.
    """
    base_path = Path(base_dir).resolve()

    if not base_path.exists():
        raise FileNotFoundError(f"Base directory does not exist: {base_dir}")
    if not base_path.is_dir():
        raise NotADirectoryError(f"Base path is not a directory: {base_dir}")

    # Quick regex check before resolution
    if TRAVERSAL_REGEX.search(user_path):
        security_logger.error(
            "PATH_TRAVERSAL_BLOCKED | base='%s' | user_path='%s'",
            base_dir, user_path,
        )
        raise PathTraversalError(
            f"Path traversal attempt detected in: {user_path}"
        )

    # Sanitize each component individually
    clean_parts: list[str] = []
    for part in Path(user_path).parts:
        if not part or part == '.':
            continue
        if part == '..':
            security_logger.error(
                "PATH_TRAVERSAL_BLOCKED | base='%s' | part='..'", base_dir,
            )
            raise PathTraversalError("Parent directory reference not allowed")
        clean_parts.append(sanitize_filename(part))

    if not clean_parts:
        raise PathTraversalError("Path resolves to empty after sanitization")

    full_path = base_path.joinpath(*clean_parts)
    resolved = full_path.resolve()

    # Containment check
    try:
        resolved.relative_to(base_path)
    except ValueError:
        security_logger.error(
            "PATH_TRAVERSAL_BLOCKED | base='%s' | resolved='%s' | user_path='%s'",
            base_path, resolved, user_path,
        )
        raise PathTraversalError(
            f"Resolved path escapes base directory: {user_path}"
        )

    # Symlink check
    if resolved.exists() and resolved.is_symlink():
        real = resolved.resolve()
        try:
            real.relative_to(base_path)
        except ValueError:
            security_logger.error(
                "SYMLINK_ATTACK_BLOCKED | symlink='%s' | target='%s'",
                resolved, real,
            )
            raise PathTraversalError(
                "Symbolic link points outside base directory"
            )

    if create_dirs:
        resolved.parent.mkdir(parents=True, exist_ok=True)

    return resolved


def get_user_directory(
    base_dir: str | Path,
    user_id: int,
    create: bool = True,
) -> Path:
    """Return the secure directory for a specific user.

    Raises ``ValueError`` for non-positive *user_id*.
    """
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError(f"Invalid user_id: {user_id}")

    user_dir = Path(base_dir).resolve() / str(user_id)

    # Containment check
    try:
        user_dir.relative_to(Path(base_dir).resolve())
    except ValueError:
        raise PathTraversalError("User directory escapes base")

    if create:
        user_dir.mkdir(parents=True, exist_ok=True)

    return user_dir
