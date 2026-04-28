"""Standalone runner to execute the eval suite and write the report."""
import subprocess
import sys

if __name__ == "__main__":
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/eval", "-m", "eval", "-v"],
        check=False,
    )
    sys.exit(result.returncode)
