-- ============================================================
-- Amazon 이커머스 데이터 정제 파이프라인 (DuckDB)
-- 원본 테이블: amazon (CSV 그대로 로드된 상태)
-- 최종 결과: amazon_clean
-- ============================================================

-- ------------------------------------------------------------
-- STEP 1. 가격/평점 컬럼 타입 변환
--   - discounted_price, actual_price : 문자열("₹399") -> DECIMAL(10,2)
--   - discount_percentage, rating, rating_count : 문자열 -> FLOAT
--   - TRY_CAST 사용: rating 컬럼의 깨진 값('|') 등은 에러 없이 NULL 처리
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE amazon_clean AS
SELECT
  * EXCLUDE (discounted_price, actual_price, discount_percentage, rating, rating_count),

  discounted_price AS discounted_price_raw,
  actual_price AS actual_price_raw,

  TRY_CAST(REPLACE(REPLACE(discounted_price, '₹', ''), ',', '') AS DECIMAL(10,2)) AS discounted_price,
  TRY_CAST(REPLACE(REPLACE(actual_price, '₹', ''), ',', '') AS DECIMAL(10,2)) AS actual_price,
  TRY_CAST(REPLACE(discount_percentage, '%', '') AS FLOAT) AS discount_percentage,
  TRY_CAST(rating AS FLOAT) AS rating,
  TRY_CAST(REPLACE(rating_count, ',', '') AS FLOAT) AS rating_count

FROM amazon;


-- ------------------------------------------------------------
-- STEP 2. rating / rating_count가 NULL인 행 백업 후 삭제
--   - rating: 원본 '|' 깨진 값 1건
--   - rating_count: 원본부터 NULL이던 2건
-- ------------------------------------------------------------

-- 2-1. 삭제 전 백업 (별도 CSV로 저장)
COPY (
  SELECT * FROM amazon_clean
  WHERE rating IS NULL OR rating_count IS NULL
) TO 'amazon_deleted_rows.csv' (HEADER, DELIMITER ',');

-- 2-2. 삭제 실행
DELETE FROM amazon_clean
WHERE rating IS NULL OR rating_count IS NULL;


-- ------------------------------------------------------------
-- STEP 3. category 컬럼을 '|' 기준으로 최대 7단계까지 분리
--   - category_depth : 실제 계층 깊이 (2~7)
--   - category_lvl1~7 : 레벨별 컬럼 (깊이보다 얕으면 NULL)
--   - category_leaf : 가장 세부적인 마지막 단계 (콘텐츠 기반 유사도용)
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE amazon_clean AS
WITH split_category AS (
  SELECT
    *,
    string_split(category, '|') AS category_array
  FROM amazon_clean
)
SELECT
  * EXCLUDE (category_array),
  len(category_array) AS category_depth,
  category_array[1] AS category_lvl1,
  category_array[2] AS category_lvl2,
  category_array[3] AS category_lvl3,
  category_array[4] AS category_lvl4,
  category_array[5] AS category_lvl5,
  category_array[6] AS category_lvl6,
  category_array[7] AS category_lvl7,
  category_array[len(category_array)] AS category_leaf
FROM split_category;


-- ------------------------------------------------------------
-- STEP 4. product_id 중복 제거 (92개 상품, 206행 -> 92행)
--   - 기준: rating_count가 가장 큰(=가장 최근 스냅샷으로 추정되는) 행만 남김
--   - product_link 동률 시 결정론적 정렬을 위한 tiebreaker
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE amazon_clean AS
SELECT *
FROM amazon_clean
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY product_id
  ORDER BY rating_count DESC, product_link ASC
) = 1;


-- ------------------------------------------------------------
-- STEP 5. 검증 쿼리
-- ------------------------------------------------------------
-- 스키마 확인
DESCRIBE amazon_clean;

-- 최종 행 수 = 고유 product_id 수 (중복 완전 제거 확인)
SELECT COUNT(*) AS total_rows, COUNT(DISTINCT product_id) AS unique_ids
FROM amazon_clean;

-- NULL 잔존 여부 확인 (rating, rating_count 삭제 이후엔 없어야 정상)
SELECT
  SUM(CASE WHEN rating IS NULL THEN 1 ELSE 0 END) AS null_rating,
  SUM(CASE WHEN rating_count IS NULL THEN 1 ELSE 0 END) AS null_rating_count
FROM amazon_clean;