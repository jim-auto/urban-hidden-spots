"""
全ステップを順番に実行するスクリプト。
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def run_step(script_name: str):
    print(f"\n{'='*60}")
    print(f"Running {script_name}...")
    print(f"{'='*60}\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script_name)],
        check=True,
    )
    return result.returncode


def main():
    run_step("fetch_osm_data.py")
    run_step("calculate_hidden_score.py")
    print("\n" + "=" * 60)
    print("All steps completed!")
    print("Open docs/index.html in your browser to view the map.")
    print("=" * 60)


if __name__ == "__main__":
    main()
