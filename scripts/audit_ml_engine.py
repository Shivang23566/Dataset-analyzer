#!/usr/bin/env python3
"""
ML Engine Authenticity Audit Script
Analyzes ml_engine.py and ml.py for fake/hardcoded implementations.
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Finding:
    severity: Severity
    category: str
    description: str
    file: str
    line_num: int
    code_snippet: str
    recommendation: str


class MLEngineAuditor(ast.NodeVisitor):
    def __init__(self, source: str, file_path: str):
        self.source = source
        self.lines = source.splitlines()
        self.file_path = file_path
        self.findings: List[Finding] = []
        self.functions: Dict[str, Dict[str, Any]] = {}

    def _line(self, n: int) -> str:
        return self.lines[n - 1].strip() if 1 <= n <= len(self.lines) else ""

    def _func_source(self, node) -> str:
        return ast.get_source_segment(self.source, node) or ""

    def visit_FunctionDef(self, node):
        name = node.name
        src = self._func_source(node)
        self.functions[name] = {"line": node.lineno, "src": src}

        if name == "train_model":
            self._audit_train(node, src)
        elif name == "recommend_model":
            self._audit_recommend(node, src)
        elif name == "detect_task_type":
            self._audit_detect(node, src)
        elif name == "get_model_cards":
            self._audit_cards(node, src)
        elif name == "_build_model":
            self._audit_build_model(node, src)

        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    # ── train_model ──────────────────────────────────────────
    def _audit_train(self, node, src: str):
        # 1. .fit() call
        if not re.search(r'\.fit\s*\(', src):
            self.findings.append(Finding(
                Severity.CRITICAL, "FAKE_TRAINING",
                "train_model() does not call .fit() — NO ACTUAL TRAINING!",
                self.file_path, node.lineno, self._line(node.lineno),
                "Add model.fit(X_train, y_train)"))
        # 2. .predict() call
        if not re.search(r'\.predict\s*\(', src):
            self.findings.append(Finding(
                Severity.CRITICAL, "FAKE_PREDICTIONS",
                "train_model() does not call .predict() — metrics can't be real!",
                self.file_path, node.lineno, self._line(node.lineno),
                "Add y_pred = model.predict(X_test)"))
        # 3. train_test_split
        if not re.search(r'train_test_split', src):
            self.findings.append(Finding(
                Severity.HIGH, "NO_DATA_SPLIT",
                "No train_test_split — model evaluates on training data",
                self.file_path, node.lineno, self._line(node.lineno),
                "Add proper train/test split"))
        # 4. Hardcoded metrics
        for pat in [r'"accuracy"\s*:\s*0\.\d+', r'"f1"\s*:\s*0\.\d+',
                     r'"r2"\s*:\s*0\.\d+', r'"mse"\s*:\s*0\.\d+',
                     r'"precision"\s*:\s*0\.\d+', r'"recall"\s*:\s*0\.\d+']:
            for m in re.finditer(pat, src, re.IGNORECASE):
                ctx = src[max(0, m.start() - 50):m.end() + 50]
                # Distinguish hardcoded returns vs. computed metric storage
                if 'return' in ctx and 'round(' not in ctx:
                    self.findings.append(Finding(
                        Severity.CRITICAL, "HARDCODED_METRICS",
                        f"Possibly hardcoded metric: {m.group()}",
                        self.file_path, node.lineno, m.group(),
                        "Metrics should be computed from predictions"))
        # 5. Fake timing
        if re.search(r'time\.sleep|asyncio\.sleep', src):
            self.findings.append(Finding(
                Severity.HIGH, "FAKE_TIMING",
                "sleep() in train_model — possibly faking training duration",
                self.file_path, node.lineno, "sleep() detected",
                "Remove artificial delays"))
        # 6. Metric imports
        if not re.search(r'accuracy_score|f1_score|r2_score|mean_squared_error|mean_absolute_error', src):
            self.findings.append(Finding(
                Severity.HIGH, "NO_METRIC_CALC",
                "train_model() does not import/call sklearn metric functions",
                self.file_path, node.lineno, self._line(node.lineno),
                "Import and use sklearn.metrics for evaluation"))
        # 7. Hyperparams usage
        if 'hyperparams' in src or 'config' in src:
            if re.search(r'hyperparams|config.*hyperparams', src):
                passed_to_build = re.search(r'_build_model\s*\(.*hyperparams', src) or \
                                  re.search(r'_build_model\s*\(.*config', src) or \
                                  re.search(r"hp\s*=\s*config", src)
                if not passed_to_build:
                    # Check if hyperparams are extracted and used
                    if not re.search(r'hp\.get|hyperparams\.get|hyperparams\[', src):
                        self.findings.append(Finding(
                            Severity.HIGH, "IGNORED_HYPERPARAMS",
                            "Hyperparams may not be passed to model builder",
                            self.file_path, node.lineno, "hyperparams not forwarded",
                            "Pass hyperparams to _build_model()"))
        # 8. Cross-validation
        if re.search(r'cross_val_score', src):
            pass  # Good — has CV
        else:
            self.findings.append(Finding(
                Severity.MEDIUM, "NO_CROSS_VALIDATION",
                "train_model() does not perform cross-validation",
                self.file_path, node.lineno, self._line(node.lineno),
                "Add cross_val_score for robust evaluation"))

    # ── recommend_model ──────────────────────────────────────
    def _audit_recommend(self, node, src: str):
        # 1. Random
        if re.search(r'random\.(choice|randint|sample|shuffle)', src):
            self.findings.append(Finding(
                Severity.CRITICAL, "RANDOM_RECOMMENDATION",
                "recommend_model() uses random selection — NOT DETERMINISTIC!",
                self.file_path, node.lineno, "random.choice() detected",
                "Base recommendations on data characteristics"))
        # 2. Data analysis
        analysis_signals = [r'\.shape', r'\.dtype', r'\.nunique', r'n_samples',
                           r'n_features', r'is_imbalanced', r'cat_cols', r'\.corr']
        if not any(re.search(p, src) for p in analysis_signals):
            self.findings.append(Finding(
                Severity.HIGH, "NO_DATA_ANALYSIS",
                "recommend_model() doesn't analyze data characteristics",
                self.file_path, node.lineno, self._line(node.lineno),
                "Analyze shape, types, distribution"))
        # 3. Single hardcoded return
        returns = list(re.finditer(r'return\s+', src))
        if len(returns) == 1 and re.search(r'return\s+["\']', src):
            self.findings.append(Finding(
                Severity.HIGH, "HARDCODED_RECOMMENDATION",
                "recommend_model() always returns the same model",
                self.file_path, node.lineno, "Single return",
                "Add branching logic based on data"))
        # 4. Check recommendation covers all model card IDs
        # (checked after all functions are visited)

    # ── detect_task_type ─────────────────────────────────────
    def _audit_detect(self, node, src: str):
        if not re.search(r'nunique|unique|is_numeric_dtype', src):
            self.findings.append(Finding(
                Severity.MEDIUM, "WEAK_TASK_DETECTION",
                "detect_task_type() has weak detection logic",
                self.file_path, node.lineno, self._line(node.lineno),
                "Check nunique, dtype, distribution"))
        if not re.search(r'target_col|target', src):
            self.findings.append(Finding(
                Severity.MEDIUM, "NO_TARGET_ANALYSIS",
                "detect_task_type() may not analyze target column",
                self.file_path, node.lineno, self._line(node.lineno),
                "Analyze target column"))

    # ── get_model_cards ──────────────────────────────────────
    def _audit_cards(self, node, src: str):
        if re.search(r'random\.(choice|sample|shuffle)', src):
            self.findings.append(Finding(
                Severity.CRITICAL, "RANDOM_MODEL_CARDS",
                "get_model_cards() uses random — cards change on every call!",
                self.file_path, node.lineno, "random in model cards",
                "Return fixed deterministic list"))
        if re.search(r'\.sort\s*\(\s*key\s*=\s*lambda.*random', src):
            self.findings.append(Finding(
                Severity.CRITICAL, "SHUFFLED_CARDS",
                "Model cards are shuffled randomly",
                self.file_path, node.lineno, "random shuffle detected",
                "Return stable order"))

    # ── _build_model ─────────────────────────────────────────
    def _audit_build_model(self, node, src: str):
        if not re.search(r'hp\.get|hyperparams\.get|hp\[', src):
            self.findings.append(Finding(
                Severity.HIGH, "BUILD_IGNORES_HP",
                "_build_model() does not read user hyperparameters",
                self.file_path, node.lineno, self._line(node.lineno),
                "Use hp.get() to apply user settings"))
        # Check model constructors actually use hp
        model_constructors = re.findall(r'(\w+)\s*\(', src)
        if not any('hp' in src[m.start():m.start()+200] for m in re.finditer(r'return\s+\w+\(', src)):
            pass  # This is weaker; hp.get checks above are enough


def audit_ml_engine(file_path: str) -> List[Finding]:
    path = Path(file_path)
    if not path.exists():
        return [Finding(Severity.CRITICAL, "FILE_NOT_FOUND",
                       f"File not found: {file_path}", file_path, 0, "", "Check path")]

    source = path.read_text(encoding='utf-8')
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [Finding(Severity.CRITICAL, "SYNTAX_ERROR",
                       f"Parse error: {e}", file_path, e.lineno or 0, "", "Fix syntax")]

    auditor = MLEngineAuditor(source, file_path)
    auditor.visit(tree)

    # Post-visit checks
    findings = list(auditor.findings)

    # sklearn imports
    if not re.search(r'from sklearn|import sklearn', source):
        findings.append(Finding(Severity.HIGH, "NO_ML_LIBRARY",
                               "No sklearn import", file_path, 1,
                               "Missing sklearn", "Import sklearn"))

    # metric imports
    metric_names = ['accuracy_score', 'f1_score', 'precision_score', 'recall_score',
                    'mean_squared_error', 'r2_score', 'mean_absolute_error']
    if not any(m in source for m in metric_names):
        findings.append(Finding(Severity.CRITICAL, "NO_METRIC_IMPORTS",
                               "No sklearn.metrics imports — metrics may be fake!",
                               file_path, 1, "Missing metric imports",
                               "Import metric functions"))

    # Check recommendation coverage vs model cards
    rec_func = auditor.functions.get("recommend_model", {}).get("src", "")
    cards_func = auditor.functions.get("get_model_cards", {}).get("src", "")
    if rec_func and cards_func:
        # Extract model IDs from cards
        card_ids = set(re.findall(r'"id"\s*:\s*"([^"]+)"', cards_func))
        # Extract recommended model IDs from recommend_model
        rec_ids = set(re.findall(r'recommended\s*=\s*"([^"]+)"', rec_func))
        if card_ids and rec_ids:
            missing_from_cards = rec_ids - card_ids
            missing_from_recs = card_ids - rec_ids
            if missing_from_cards:
                findings.append(Finding(
                    Severity.HIGH, "REC_NOT_IN_CARDS",
                    f"Recommended models not in model cards: {missing_from_cards}",
                    file_path, auditor.functions["recommend_model"]["line"],
                    str(missing_from_cards),
                    "Ensure every recommended model has a corresponding card"))
            if missing_from_recs:
                findings.append(Finding(
                    Severity.LOW, "CARDS_NOT_RECOMMENDED",
                    f"Model cards never recommended: {missing_from_recs}",
                    file_path, auditor.functions["get_model_cards"]["line"],
                    str(missing_from_recs),
                    "Consider adding these to recommendation logic"))

    return findings


def audit_ml_api(file_path: str) -> List[Finding]:
    findings = []
    path = Path(file_path)
    if not path.exists():
        return [Finding(Severity.CRITICAL, "FILE_NOT_FOUND",
                       f"Not found: {file_path}", file_path, 0, "", "Check path")]
    source = path.read_text(encoding='utf-8')

    # Validates input
    if not re.search(r'target_col|filename', source):
        findings.append(Finding(Severity.HIGH, "NO_INPUT_VALIDATION",
                               "ML API may not validate inputs", file_path, 1,
                               "Missing validation", "Validate inputs"))

    # Calls engine functions
    for func in ['train_model', 'recommend_model', 'detect_task_type', 'get_model_cards']:
        alt = func.replace('train_model', '_train_model')
        if func not in source and alt not in source:
            findings.append(Finding(Severity.MEDIUM, "MISSING_ENGINE_CALL",
                                   f"API doesn't call {func}()", file_path, 1,
                                   f"Missing {func}", f"Add {func}() call"))

    # Thread pool for training
    if 'to_thread' not in source and 'run_in_executor' not in source:
        findings.append(Finding(Severity.MEDIUM, "BLOCKING_TRAINING",
                               "Training may block the event loop", file_path, 1,
                               "Missing async offload",
                               "Use asyncio.to_thread for CPU-bound training"))

    return findings


def print_report(findings: List[Finding]):
    icons = {Severity.CRITICAL: "🔴", Severity.HIGH: "🟠",
             Severity.MEDIUM: "🟡", Severity.LOW: "🟢"}

    print("\n" + "=" * 70)
    print("🔍 ML FEATURE AUTHENTICITY AUDIT REPORT")
    print("=" * 70)

    if not findings:
        print("\n✅ No issues found! ML feature appears authentic.")
        return

    by_sev: Dict[Severity, List[Finding]] = {}
    for f in findings:
        by_sev.setdefault(f.severity, []).append(f)

    print("\n📊 SUMMARY:")
    print("-" * 40)
    for sev in Severity:
        count = len(by_sev.get(sev, []))
        if count:
            print(f"  {icons[sev]} {sev.value}: {count} issues")
    print(f"\n  Total: {len(findings)} issues found")

    for sev in Severity:
        items = by_sev.get(sev, [])
        if not items:
            continue
        print(f"\n\n{icons[sev]} {sev.value} ISSUES:")
        print("=" * 50)
        for i, f in enumerate(items, 1):
            print(f"\n{i}. [{f.category}]")
            print(f"   File: {f.file}:{f.line_num}")
            print(f"   Issue: {f.description}")
            print(f"   Code: {f.code_snippet}")
            print(f"   Fix: {f.recommendation}")

    crit = len(by_sev.get(Severity.CRITICAL, []))
    high = len(by_sev.get(Severity.HIGH, []))

    print("\n" + "=" * 70)
    print("🏁 VERDICT:")
    print("-" * 40)

    if crit > 0:
        print(f"""
❌ ML FEATURE HAS CRITICAL ISSUES

{crit} critical issues found that must be addressed.
Review each finding and apply the recommended fixes.
        """)
    elif high > 0:
        print(f"""
⚠️ ML FEATURE HAS SIGNIFICANT ISSUES

{high} high-severity issues should be fixed for proper functionality.
        """)
    else:
        print("""
✅ ML FEATURE APPEARS FUNCTIONAL

Only minor issues found. Review and address as needed.
        """)


if __name__ == "__main__":
    print("🔍 Starting ML Feature Authenticity Audit...\n")

    all_findings = []

    print("📄 Auditing: backend/app/services/ml_engine.py")
    f1 = audit_ml_engine("backend/app/services/ml_engine.py")
    all_findings.extend(f1)
    print(f"   Found: {len(f1)} issues")

    print("\n📄 Auditing: backend/app/api/ml.py")
    f2 = audit_ml_api("backend/app/api/ml.py")
    all_findings.extend(f2)
    print(f"   Found: {len(f2)} issues")

    print_report(all_findings)
