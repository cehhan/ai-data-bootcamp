"""전체 파이프라인을 순서대로 실행합니다.

    python scripts/run_all.py                 # 전체 (기준·배율·LightGBM·통계·Chronos)
    python scripts/run_all.py --skip chronos  # Chronos 제외 (모델 내려받기가 싫을 때)
    python scripts/run_all.py --skip stat chronos
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = {"classic": "run_classic.py", "stat": "run_stat.py", "chronos": "run_chronos.py"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip", nargs="*", default=[], choices=list(STEPS))
    args = ap.parse_args()
    for name, script in STEPS.items():
        if name in args.skip:
            print(f"[건너뜀] {script}")
            continue
        print(f"\n===== {script} =====", flush=True)
        subprocess.run([sys.executable, str(HERE / script)], check=True)
    subprocess.run([sys.executable, str(HERE / "compare.py")], check=True)


if __name__ == "__main__":
    main()
