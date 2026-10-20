"""Run local Dev 3 safety checks without mutating lender state."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str], cwd: Path = ROOT) -> bool:
    print(f"\n=== {label} ===", flush=True)
    result = subprocess.run(command, cwd=cwd, check=False)
    print(f"{label}: {'PASS' if result.returncode == 0 else 'FAIL'}", flush=True)
    return result.returncode == 0


def main() -> int:
    checks = [
        run("Mock LMS fail-closed tests", [sys.executable, "-m", "pytest", "-q", "tests/test_mock_lms.py"]),
        run("Frontend production build", ["npm", "run", "build"], ROOT / "dashboard"),
    ]
    print("\nThis runner does not seed fake proofs or write to the lender API.")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
