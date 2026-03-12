#!/usr/bin/env python3
"""
Debug Statement Scanner

Scans codebase for debug statements (console.log, debug prints, breakpoints,
TODO/FIXME comments) and optionally removes auto-fixable ones.

Run: python scripts/remove_debug.py --dry-run
     python scripts/remove_debug.py --apply
"""

import os
import re
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class IssueType(Enum):
    CONSOLE_LOG = "console.log"
    DEBUG_PRINT = "debug print"
    TODO_COMMENT = "TODO/FIXME"
    DEBUGGER = "debugger statement"


@dataclass
class Issue:
    file: str
    line_num: int
    issue_type: IssueType
    content: str
    can_auto_fix: bool


SCAN_DIRS = ["frontend/src", "backend/app"]
EXTENSIONS = {
    ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript",
    ".py": "python",
}
SKIP_DIRS = {"node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".git", "backup_"}

PATTERNS = {
    "typescript": {
        "console_log": r'^\s*console\.(log|debug)\s*\(',
        "debugger": r'^\s*debugger\s*;?\s*$',
    },
    "javascript": {
        "console_log": r'^\s*console\.(log|debug)\s*\(',
        "debugger": r'^\s*debugger\s*;?\s*$',
    },
    "python": {
        "debug_print": r'^\s*print\s*\(\s*["\']?(debug|DEBUG|test|TEST|TODO|FIXME)',
        "breakpoint": r'^\s*(breakpoint|pdb\.set_trace|ipdb\.set_trace)\s*\(\s*\)',
    },
}

SAFE_PATTERNS = [
    r'console\.(warn|error)\s*\(\s*["\']',
    r'logger\.',
    r'logging\.',
]


def is_safe(line: str) -> bool:
    return any(re.search(p, line) for p in SAFE_PATTERNS)


def scan_file(file_path: Path, lang: str) -> List[Issue]:
    issues = []
    patterns = PATTERNS.get(lang, {})
    try:
        lines = file_path.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception:
        return issues

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        if lang in ("typescript", "javascript"):
            if re.search(patterns.get("console_log", ""), line) and not is_safe(line):
                issues.append(Issue(str(file_path), i, IssueType.CONSOLE_LOG, stripped[:80], True))
            if re.search(patterns.get("debugger", ""), line):
                issues.append(Issue(str(file_path), i, IssueType.DEBUGGER, stripped, True))

        elif lang == "python":
            if re.search(patterns.get("debug_print", ""), line):
                issues.append(Issue(str(file_path), i, IssueType.DEBUG_PRINT, stripped[:80], True))
            if re.search(patterns.get("breakpoint", ""), line):
                issues.append(Issue(str(file_path), i, IssueType.DEBUGGER, stripped, True))

        if re.search(r'(TODO|FIXME|HACK|XXX)\s*:', line, re.IGNORECASE):
            issues.append(Issue(str(file_path), i, IssueType.TODO_COMMENT, stripped[:80], False))

    return issues


def scan_all(dirs: List[str]) -> List[Issue]:
    all_issues = []
    for base in dirs:
        base_path = Path(base)
        if not base_path.exists():
            continue
        for root, dirs_list, files in os.walk(base_path):
            dirs_list[:] = [d for d in dirs_list if not any(s in d for s in SKIP_DIRS)]
            for f in files:
                ext = Path(f).suffix
                if ext in EXTENSIONS:
                    all_issues.extend(scan_file(Path(root) / f, EXTENSIONS[ext]))
    return all_issues


def remove_fixable(issues: List[Issue], dry_run: bool) -> Dict[str, int]:
    by_file: Dict[str, List[int]] = {}
    for iss in issues:
        if iss.can_auto_fix:
            by_file.setdefault(iss.file, []).append(iss.line_num)

    modified = {}
    for fp, line_nums in by_file.items():
        try:
            lines = Path(fp).read_text(encoding='utf-8').splitlines(keepends=True)
            remove_set: set = set()
            for ln in sorted(line_nums):
                idx = ln - 1
                if idx >= len(lines):
                    continue
                # Track parentheses to handle multi-line calls
                depth = 0
                for i in range(idx, len(lines)):
                    depth += lines[i].count('(') - lines[i].count(')')
                    remove_set.add(i + 1)  # 1-based
                    if depth <= 0:
                        break
            new_lines = [l for i, l in enumerate(lines, 1) if i not in remove_set]
            if not dry_run:
                Path(fp).write_text(''.join(new_lines), encoding='utf-8')
            modified[fp] = len(remove_set)
        except Exception as e:
            print(f"  Error: {fp}: {e}")
    return modified


def main():
    parser = argparse.ArgumentParser(description="Scan/remove debug statements")
    parser.add_argument("--apply", action="store_true", help="Remove fixable issues (default: dry-run)")
    parser.add_argument("--dirs", nargs="+", default=SCAN_DIRS)
    args = parser.parse_args()
    dry_run = not args.apply

    print(f"Scanning ({('DRY RUN' if dry_run else 'APPLY')})...")
    issues = scan_all(args.dirs)

    fixable = [i for i in issues if i.can_auto_fix]
    todos = [i for i in issues if i.issue_type == IssueType.TODO_COMMENT]

    print(f"\nFound {len(issues)} issues ({len(fixable)} auto-fixable, {len(todos)} TODOs)")

    if fixable:
        print("\nAuto-fixable:")
        for iss in fixable:
            print(f"  [{iss.issue_type.value}] {iss.file}:{iss.line_num}  {iss.content}")

    if todos:
        print(f"\nTODO/FIXME inventory ({len(todos)}):")
        for iss in todos[:20]:
            print(f"  {iss.file}:{iss.line_num}  {iss.content}")
        if len(todos) > 20:
            print(f"  ... and {len(todos) - 20} more")

    modified = remove_fixable(issues, dry_run)
    if modified:
        action = "Would modify" if dry_run else "Modified"
        print(f"\n{action}:")
        for fp, cnt in modified.items():
            print(f"  {fp}: {cnt} lines")

    if dry_run and fixable:
        print("\nRun with --apply to remove debug statements")

    return 0 if not fixable else 1


if __name__ == "__main__":
    sys.exit(main())
