from __future__ import annotations

import json
import os
from typing import Any, Dict, List

RESULTS_FILE = "results.json"


def _ensure_results_file() -> None:
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def load_results() -> List[Dict[str, Any]]:
    _ensure_results_file()
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_result(record: Dict[str, Any]) -> None:
    _ensure_results_file()
    results = load_results()
    results.append(record)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def clear_results() -> None:
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)