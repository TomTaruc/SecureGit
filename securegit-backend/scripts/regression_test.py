import os
import subprocess
import sys
from pathlib import Path

def main():
    backend_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_dir)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_regression.py",
        "-v",
        "--tb=short",
    ]

    print("Running:", " ".join(cmd))
    print("Working directory:", backend_dir)

    result = subprocess.run(
        cmd,
        cwd=str(backend_dir),
        env=env,
        text=True,
    )

    if result.returncode != 0:
        print("Regression tests failed.")
        return result.returncode

    print("Regression tests passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
