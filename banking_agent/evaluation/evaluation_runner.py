import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_CATALOG = Path(__file__).with_name("test_cases.json")


def run_evaluation() -> dict:
    """Execute every scenario linked to an isolated pytest test and report its result."""
    scenarios = json.loads(SCENARIO_CATALOG.read_text(encoding="utf-8"))
    if not scenarios or any(not item.get("test_nodeid") for item in scenarios):
        raise ValueError("Every evaluation scenario must reference an executable pytest node ID")
    if len({item.get("id") for item in scenarios}) != len(scenarios):
        raise ValueError("Evaluation scenario IDs must be unique")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *[item["test_nodeid"] for item in scenarios],
            "-vv",
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
    outcomes = {
        nodeid: status.lower()
        for nodeid, status in re.findall(
            r"^(tests/\S+::\S+)\s+(PASSED|FAILED|SKIPPED)\b",
            summary,
            flags=re.MULTILINE,
        )
    }
    results = [
        {
            "id": item["id"],
            "scenario": item["scenario"],
            "result": outcomes.get(item["test_nodeid"], "not_collected"),
            "test_nodeid": item["test_nodeid"],
        }
        for item in scenarios
    ]
    passed_scenarios = sum(item["result"] == "passed" for item in results)
    failed_scenarios = sum(item["result"] == "failed" for item in results)
    skipped_scenarios = sum(item["result"] == "skipped" for item in results)
    uncollected_scenarios = sum(item["result"] == "not_collected" for item in results)
    return {
        "success": completed.returncode == 0 and failed == 0 and uncollected_scenarios == 0,
        "pytest_tests": {"passed": passed, "failed": failed, "skipped": skipped},
        "executed_scenarios": {
            "total": len(results),
            "passed": passed_scenarios,
            "failed": failed_scenarios,
            "skipped": skipped_scenarios,
            "not_collected": uncollected_scenarios,
            "pass_rate": round(passed_scenarios / max(1, len(results) - skipped_scenarios), 4),
        },
        "scenarios": results,
        "pytest_summary": summary_line,
    }


if __name__ == "__main__":
    result = run_evaluation()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["success"] else 1)
