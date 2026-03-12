#!/usr/bin/env python3
"""
Unused Import Scanner (Python only)

Uses AST parsing to find Python imports that are not referenced in the module body.
Has a SAFE_IMPORTS allowlist for FastAPI/SQLAlchemy/typing re-exports.

Run: python scripts/remove_unused_imports.py --dry-run
     python scripts/remove_unused_imports.py --apply
"""

import ast
import os
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Set

SCAN_DIRS = ["backend/app"]
SKIP_DIRS = {"__pycache__", "venv", ".venv", ".git", "alembic"}

# Imports that look unused but are re-exported or required at module level
SAFE_IMPORTS = {
    # SQLAlchemy
    "Column", "Integer", "String", "Boolean", "DateTime", "Float", "Text",
    "ForeignKey", "Table", "MetaData", "Index", "UniqueConstraint",
    "relationship", "backref", "mapped_column", "Mapped",
    # FastAPI
    "APIRouter", "Depends", "HTTPException", "status", "Request", "Response",
    "Body", "Query", "Path", "File", "UploadFile", "Form", "Header",
    "BackgroundTasks",
    # Pydantic
    "BaseModel", "Field", "validator", "root_validator",
    # Typing
    "Optional", "List", "Dict", "Any", "Union", "Tuple", "Set",
    "Callable", "Awaitable", "Type", "ClassVar", "Literal",
    # Common re-exports from __init__.py
    "Base", "engine", "SessionLocal", "get_db", "get_current_user",
}


@dataclass
class UnusedImport:
    file: str
    line_num: int
    name: str
    full_line: str
    is_safe: bool


def get_imported_names(tree: ast.Module) -> List[tuple]:
    """Return list of (name, alias, line_number, node) for all imports."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                imports.append((name, alias.name, node.lineno, node))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == '*':
                    continue
                name = alias.asname or alias.name
                imports.append((name, alias.name, node.lineno, node))
    return imports


def get_used_names(tree: ast.Module) -> Set[str]:
    """Return all Name references in the module (excluding imports themselves)."""
    used = set()
    import_lines = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_lines.add(node.lineno)

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            # For chained attributes, get the root name
            n = node
            while isinstance(n, ast.Attribute):
                n = n.value
            if isinstance(n, ast.Name):
                used.add(n.id)
        # Check decorators, base classes, type annotations
        if isinstance(node, ast.FunctionDef):
            used.add(node.name)
        elif isinstance(node, ast.ClassDef):
            used.add(node.name)
    return used


def scan_file(file_path: Path) -> List[UnusedImport]:
    issues = []
    try:
        source = file_path.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(source)
    except (SyntaxError, Exception):
        return issues

    lines = source.splitlines()
    imported = get_imported_names(tree)
    used = get_used_names(tree)

    # __init__.py files: all imports are likely re-exports
    is_init = file_path.name == '__init__.py'

    for name, original_name, lineno, node in imported:
        if name in used and name not in {n for n, _, l, _ in imported if l == lineno}:
            continue
        # Check if name appears anywhere in the source as text (catch string refs, __all__)
        if name in used:
            continue

        line_text = lines[lineno - 1] if lineno <= len(lines) else ""
        is_safe = (
            name in SAFE_IMPORTS or
            is_init or
            original_name in SAFE_IMPORTS or
            '__all__' in source and name in source
        )
        issues.append(UnusedImport(str(file_path), lineno, name, line_text.strip()[:80], is_safe))

    return issues


def scan_all(dirs: List[str]) -> List[UnusedImport]:
    all_issues = []
    for base in dirs:
        base_path = Path(base)
        if not base_path.exists():
            continue
        for root, dirs_list, files in os.walk(base_path):
            dirs_list[:] = [d for d in dirs_list if d not in SKIP_DIRS]
            for f in files:
                if f.endswith('.py'):
                    all_issues.extend(scan_file(Path(root) / f))
    return all_issues


def main():
    parser = argparse.ArgumentParser(description="Scan for unused Python imports")
    parser.add_argument("--apply", action="store_true", help="Remove unused imports (CAUTION)")
    parser.add_argument("--dirs", nargs="+", default=SCAN_DIRS)
    args = parser.parse_args()
    dry_run = not args.apply

    print(f"Scanning for unused imports ({('DRY RUN' if dry_run else 'APPLY')})...")
    issues = scan_all(args.dirs)

    unsafe = [i for i in issues if not i.is_safe]
    safe = [i for i in issues if i.is_safe]

    print(f"\nFound {len(issues)} potentially unused imports")
    print(f"  {len(unsafe)} likely unused (review these)")
    print(f"  {len(safe)} likely re-exports / safe (skipped)")

    if unsafe:
        print("\nLikely unused:")
        for iss in unsafe:
            print(f"  {iss.file}:{iss.line_num}  '{iss.name}'  |  {iss.full_line}")

    if safe and '-v' in sys.argv:
        print(f"\nSafe/re-export (skipped):")
        for iss in safe:
            print(f"  {iss.file}:{iss.line_num}  '{iss.name}'")

    if args.apply and unsafe:
        print("\nAuto-removal of imports is high-risk. Review the list above and remove manually.")
        print("This tool is for SCANNING only. Manual removal recommended.")

    return 0 if not unsafe else 1


if __name__ == "__main__":
    sys.exit(main())
