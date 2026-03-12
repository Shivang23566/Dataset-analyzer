#!/usr/bin/env python3
"""
Cleanup Verification Script

Validates the codebase cleanup was successful by checking:
  1. Files that should NOT exist are gone
  2. Files that SHOULD exist are present
  3. Directories are clean (no stale artifacts)
  4. No secrets or credentials in tracked files

Run: python scripts/verify_cleanup.py
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Files/dirs that should NOT exist after cleanup
SHOULD_NOT_EXIST = [
    # Root scripts
    "create_dirs.bat", "create_dirs.js", "create_dirs.py",
    "execute_setup.bat", "execute_setup.js", "execute_setup.py",
    "install_pyjwt.bat", "minimal_setup.py", "quick_setup.py",
    "run_create_dirs.bat", "run_node_setup.bat", "run_script.bat",
    "run_setup_simple.bat", "run_setup_wrapper.ps1", "run_setup.py",
    "runner.py", "setup_css.bat", "setup_css.sh", "setup_executor.py",
    "setup_run.bat", "temp_run.bat",
    # Backend temp
    "backend/server.log", "backend/server_err.log", "backend/uvicorn.log",
    "backend/dataset_analyser.db", "backend/.DS_Store",
    "backend/run_compile_test.bat", "backend/.pytest_cache",
    "backend/cache", "backend/venv",
    # Frontend temp
    "frontend/tsconfig.tsbuildinfo",
    # User data
    "datasets/1",
]

# Files/dirs that SHOULD exist
SHOULD_EXIST = [
    ".gitignore",
    "docker-compose.yml",
    "render.yaml",
    "README.md",
    "setup-dirs.js",
    "datasets/.gitkeep",
    "backend/store/.gitkeep",
    "backend/static/assets/.gitkeep",
    "backend/app/main.py",
    "backend/app/core/config.py",
    "backend/app/core/security.py",
    "backend/requirements.txt",
    "backend/alembic.ini",
    "frontend/package.json",
    "frontend/vite.config.ts",
    "frontend/src/App.tsx",
    "frontend/src/main.tsx",
    "scripts/remove_debug.py",
    "scripts/remove_unused_imports.py",
    "scripts/verify_cleanup.py",
]

# Patterns that indicate secrets (check tracked .py/.ts/.js/.yaml files)
SECRET_PATTERNS = [
    (r'postgresql://[^/]+:[^@]+@[^/]+', "Hardcoded database URL"),
    (r'(password|secret|api_key)\s*=\s*["\'][^"\']{8,}', "Possible hardcoded secret"),
]

# Files to exempt from secret scanning
SECRET_EXEMPT = {
    ".env", ".env.example", ".env.local", ".env.production",
    "config.py",  # Uses os.getenv
}


def check_should_not_exist() -> list:
    failures = []
    for rel in SHOULD_NOT_EXIST:
        p = ROOT / rel
        if p.exists():
            failures.append(f"FAIL: Should not exist: {rel}")
    return failures


def check_should_exist() -> list:
    failures = []
    for rel in SHOULD_EXIST:
        p = ROOT / rel
        if not p.exists():
            failures.append(f"FAIL: Missing: {rel}")
    return failures


def check_clean_dirs() -> list:
    """Check for stale __pycache__, .pyc, .log, .db files."""
    failures = []
    stale_exts = {'.pyc', '.pyo', '.log', '.sqlite3'}
    stale_dirs = {'__pycache__', '.pytest_cache'}

    for root, dirs, files in os.walk(ROOT):
        # Skip .git, node_modules, venv
        rel_root = Path(root).relative_to(ROOT)
        parts = set(rel_root.parts)
        if parts & {'.git', 'node_modules', '.venv', 'venv', 'dist'}:
            dirs[:] = []
            continue

        for d in dirs:
            if d in stale_dirs:
                failures.append(f"WARN: Stale dir: {rel_root / d}")
        for f in files:
            ext = Path(f).suffix
            if ext in stale_exts:
                failures.append(f"WARN: Stale file: {rel_root / f}")
            if f == '.DS_Store':
                failures.append(f"WARN: .DS_Store: {rel_root / f}")

    return failures


def check_secrets() -> list:
    """Scan tracked code files for hardcoded secrets."""
    failures = []
    check_exts = {'.py', '.ts', '.tsx', '.js', '.jsx', '.yaml', '.yml'}

    for root, dirs, files in os.walk(ROOT):
        rel_root = Path(root).relative_to(ROOT)
        parts = set(rel_root.parts)
        if parts & {'.git', 'node_modules', '.venv', 'venv', 'dist', 'alembic'}:
            dirs[:] = []
            continue

        for f in files:
            if Path(f).suffix not in check_exts:
                continue
            if f in SECRET_EXEMPT:
                continue

            fp = Path(root) / f
            try:
                content = fp.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue

            for pattern, desc in SECRET_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    rel = fp.relative_to(ROOT)
                    failures.append(f"WARN: {desc} in {rel}")
                    break

    return failures


def main():
    print("=" * 60)
    print("  Cleanup Verification Report")
    print("=" * 60)
    print(f"Root: {ROOT}\n")

    all_issues = []

    print("[1/4] Checking files that should NOT exist...")
    issues = check_should_not_exist()
    all_issues.extend(issues)
    if not issues:
        print("  PASS: All unwanted files removed")
    else:
        for i in issues:
            print(f"  {i}")

    print("\n[2/4] Checking files that SHOULD exist...")
    issues = check_should_exist()
    all_issues.extend(issues)
    if not issues:
        print("  PASS: All required files present")
    else:
        for i in issues:
            print(f"  {i}")

    print("\n[3/4] Checking for stale artifacts...")
    issues = check_clean_dirs()
    all_issues.extend(issues)
    if not issues:
        print("  PASS: No stale artifacts found")
    else:
        for i in issues[:15]:
            print(f"  {i}")
        if len(issues) > 15:
            print(f"  ... and {len(issues) - 15} more")

    print("\n[4/4] Scanning for hardcoded secrets...")
    issues = check_secrets()
    all_issues.extend(issues)
    if not issues:
        print("  PASS: No hardcoded secrets detected")
    else:
        for i in issues:
            print(f"  {i}")

    fails = [i for i in all_issues if i.startswith("FAIL")]
    warns = [i for i in all_issues if i.startswith("WARN")]

    print(f"\n{'=' * 60}")
    print(f"Results: {len(fails)} failures, {len(warns)} warnings")
    if not fails and not warns:
        print("ALL CHECKS PASSED")
    print("=" * 60)

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
