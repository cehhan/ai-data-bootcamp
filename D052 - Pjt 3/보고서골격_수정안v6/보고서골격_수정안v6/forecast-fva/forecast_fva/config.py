"""경로와 모든 모형이 공유하는 설정."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "train_2023_2025_core_v2.csv"
OUTPUT_DIR = ROOT / "output"

# 원점: 2025년 매월 1일 12개. 원점마다 예측 기간은 그달 전체(28~31일)
ORIGINS = pd.date_range("2025-01-01", "2025-12-01", freq="MS")

# 비용 기준: 모자라면 1명당 60만 원, 남으면 1명당 15만 원, 1명은 하루 2,000명 담당
CU, CO, CAP = 600_000, 150_000, 2_000
QUANTILE = 0.8          # 서비스 수준 (0.8 분위수)
LOOKBACK_WEEKS = 8      # 행 2 보정 배율을 구할 과거 기간

# 기준값 (직전 7일 평균 행 1의 총 비용). 저장소가 제대로 재현되는지 확인하는 데 씁니다.
EXPECTED_BASELINE_COST = 1_702_786_555
