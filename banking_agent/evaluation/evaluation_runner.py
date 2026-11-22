import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_CATALOG = Path(__file__).with_name("test_cases.json")


def run_evaluation() -> dict:
    """Run the deterministic local tests and report the separate scenario catalog size."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit",
            "tests/integration",
            "tests/security",
            "-v",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    summary = (completed.stdout + completed.stderr).strip()
    summary_line = next(
        (line for line in reversed(summary.splitlines())
         if re.search(r"\b(passed|failed|skipped|error|errors)\b", line)),
        "",
    )
    if not summary_line:
        raise RuntimeError(f"Could not parse pytest result (exit {completed.returncode}):\n{summary}")

    def count(pattern: str) -> int:
        match = re.search(pattern, summary_line)
        return int(match.group(1)) if match else 0

    passed = count(r"(\d+) passed")
    failed = count(r"(\d+) failed") + count(r"(\d+) error")
    skipped = count(r"(\d+) skipped")
    catalog = json.loads(SCENARIO_CATALOG.read_text(encoding="utf-8"))
    return {
        "success": completed.returncode == 0,
        "executed_tests": {"passed": passed, "failed": failed, "skipped": skipped},
        "planned_scenario_catalog_count": len(catalog),
        "note": "The scenario catalog is planning data; only pytest results above are executed.",
        "pytest_summary": summary_line,
    }


if __name__ == "__main__":
    result = run_evaluation()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["success"] else 1)
