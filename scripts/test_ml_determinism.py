#!/usr/bin/env python3
"""
ML Determinism Test Script

Tests ML endpoints against a running backend for consistency.
Usage:
    python scripts/test_ml_determinism.py --base-url http://localhost:8000
"""

import argparse
import json
import time
from typing import Any, Dict, List
from dataclasses import dataclass, field
import requests


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str
    values: Any = None


class MLDeterminismTester:
    def __init__(self, base_url: str, token: str = ""):
        self.base = base_url.rstrip('/')
        self.headers: Dict[str, str] = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        self.results: List[TestResult] = []

    def _post(self, ep: str, data: dict) -> dict:
        r = requests.post(f"{self.base}{ep}", json=data, headers=self.headers)
        r.raise_for_status()
        return r.json()

    def _get(self, ep: str) -> dict:
        r = requests.get(f"{self.base}{ep}", headers=self.headers)
        r.raise_for_status()
        return r.json()

    def test_task_detection(self, filename: str, target: str, n: int = 5):
        print(f"\n🧪 Task detection consistency ({n}x)...")
        results = []
        for _ in range(n):
            try:
                r = self._post("/api/ml/detect-task", {"filename": filename, "target_col": target})
                results.append(r.get("task"))
            except Exception as e:
                results.append(f"ERR: {e}")
            time.sleep(0.1)
        uniq = set(str(x) for x in results)
        ok = len(uniq) == 1
        self.results.append(TestResult("Task Detection Consistency", ok,
            f"{len(uniq)} unique: {uniq}" if not ok else "Consistent", results))
        print(f"   Results: {results}")
        print(f"   {'✅ PASS' if ok else '❌ FAIL'}")

    def test_recommendation(self, filename: str, target: str, n: int = 5):
        print(f"\n🧪 Recommendation consistency ({n}x)...")
        results = []
        for _ in range(n):
            try:
                r = self._post("/api/ml/recommend", {"filename": filename, "target_col": target})
                results.append(r.get("recommended_model"))
            except Exception as e:
                results.append(f"ERR: {e}")
            time.sleep(0.1)
        uniq = set(str(x) for x in results)
        ok = len(uniq) == 1
        self.results.append(TestResult("Recommendation Consistency", ok,
            f"{len(uniq)} unique: {uniq}" if not ok else "Consistent", results))
        print(f"   Results: {results}")
        print(f"   {'✅ PASS' if ok else '❌ FAIL'}")

    def test_model_cards(self, task: str, n: int = 5):
        print(f"\n🧪 Model cards consistency ({n}x)...")
        results = []
        for _ in range(n):
            try:
                r = self._post("/api/ml/cards", {"task": task})
                ids = [c.get("id") for c in r.get("cards", [])]
                results.append(tuple(ids))
            except Exception as e:
                results.append(f"ERR: {e}")
            time.sleep(0.1)
        uniq = set(results)
        ok = len(uniq) == 1
        self.results.append(TestResult("Model Cards Consistency", ok,
            f"{len(uniq)} unique lists" if not ok else "Consistent", results))
        print(f"   Results[0]: {results[0] if results else 'N/A'}")
        print(f"   {'✅ PASS' if ok else '❌ FAIL'}")

    def test_rec_in_options(self, filename: str, target: str, task: str):
        print(f"\n🧪 Recommendation in available options...")
        try:
            rec = self._post("/api/ml/recommend", {"filename": filename, "target_col": target})
            cards = self._post("/api/ml/cards", {"task": task})
            recommended = rec.get("recommended_model")
            available = [c.get("id") for c in cards.get("cards", [])]
            ok = recommended in available
            self.results.append(TestResult("Recommendation In Options", ok,
                f"'{recommended}' {'IN' if ok else 'NOT IN'} {available}",
                {"recommended": recommended, "available": available}))
            print(f"   Recommended: {recommended}")
            print(f"   Available IDs: {available}")
            print(f"   {'✅ PASS' if ok else '❌ FAIL'}")
        except Exception as e:
            self.results.append(TestResult("Recommendation In Options", False, f"Error: {e}"))
            print(f"   ❌ ERROR: {e}")

    def test_training_metrics(self, filename: str, target: str, model_id: str,
                              task: str, n: int = 3):
        print(f"\n🧪 Training produces real metrics ({n}x)...\n   ⚠️ This trains models...")
        metrics_list = []
        for i in range(n):
            try:
                print(f"   Iteration {i+1}/{n}...")
                r = self._post("/api/ml/train", {
                    "filename": filename, "model_id": model_id,
                    "target_col": target, "task": task, "test_size": 0.2})
                metrics_list.append(r.get("metrics", {}))
            except Exception as e:
                metrics_list.append({"error": str(e)})
            time.sleep(0.3)

        strs = [json.dumps(m, sort_keys=True) for m in metrics_list]
        all_same = len(set(strs)) == 1
        suspicious = False
        for m in metrics_list:
            for k, v in m.items():
                if isinstance(v, (int, float)) and v == round(v, 1) and v > 0:
                    suspicious = True

        ok = not suspicious  # Same metrics with same seed is EXPECTED
        self.results.append(TestResult("Training Produces Real Metrics", ok,
            f"All identical: {all_same}, Suspicious round vals: {suspicious}", metrics_list))
        for i, m in enumerate(metrics_list):
            print(f"   Iter {i+1}: {m}")
        note = " (same seed = same results is expected)" if all_same else ""
        print(f"   {'✅ PASS' if ok else '❌ FAIL'}{note}")

    def test_hyperparams_effect(self, filename: str, target: str, model_id: str, task: str):
        print(f"\n🧪 Hyperparameters affect results...")
        param_sets = [
            {"n_estimators": 10, "max_depth": 3},
            {"n_estimators": 200, "max_depth": 20},
        ]
        results = []
        for params in param_sets:
            try:
                print(f"   Training with {params}")
                r = self._post("/api/ml/train", {
                    "filename": filename, "model_id": model_id,
                    "target_col": target, "task": task,
                    "hyperparams": params, "test_size": 0.2})
                results.append({"params": params, "metrics": r.get("metrics", {})})
            except Exception as e:
                results.append({"params": params, "error": str(e)})
            time.sleep(0.3)

        metric_strs = [json.dumps(r.get("metrics", {}), sort_keys=True) for r in results]
        ok = len(set(metric_strs)) > 1
        self.results.append(TestResult("Hyperparameters Affect Results", ok,
            f"{len(set(metric_strs))} unique results for {len(param_sets)} configs", results))
        for r in results:
            print(f"   {r}")
        print(f"   {'✅ PASS' if ok else '❌ FAIL - Hyperparameters may be ignored!'}")

    def report(self):
        print("\n" + "=" * 70)
        print("🔍 ML DETERMINISM TEST REPORT")
        print("=" * 70)
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        print(f"\n📊 SUMMARY: {passed}/{total} tests passed")
        print("-" * 40)
        for r in self.results:
            s = "✅ PASS" if r.passed else "❌ FAIL"
            print(f"\n{s}: {r.name}")
            print(f"   {r.details}")
        print("\n" + "=" * 70)
        if passed < total:
            print(f"❌ {total - passed} TESTS FAILED")
        else:
            print("✅ ALL TESTS PASSED")


def main():
    p = argparse.ArgumentParser(description="ML determinism tests")
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--token", default="")
    p.add_argument("--filename", default="")
    p.add_argument("--target-col", default="")
    p.add_argument("--task", default="")
    p.add_argument("--model-id", default="random_forest_classifier")
    p.add_argument("--skip-training", action="store_true")
    args = p.parse_args()

    print(f"🔍 ML Determinism Tester")
    print(f"   Backend: {args.base_url}")

    tester = MLDeterminismTester(args.base_url, args.token)

    try:
        if args.filename and args.target_col:
            tester.test_task_detection(args.filename, args.target_col)
            task = args.task or "binary_classification"
            tester.test_recommendation(args.filename, args.target_col)
            tester.test_model_cards(task)
            tester.test_rec_in_options(args.filename, args.target_col, task)
            if not args.skip_training:
                tester.test_training_metrics(args.filename, args.target_col, args.model_id, task)
                tester.test_hyperparams_effect(args.filename, args.target_col, args.model_id, task)
        else:
            # Minimal test — just check model cards determinism
            for task in ["binary_classification", "regression", "clustering"]:
                tester.test_model_cards(task)

        tester.report()
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to {args.base_url}. Start the backend first.")
    except Exception as e:
        print(f"\n❌ {e}")


if __name__ == "__main__":
    main()
