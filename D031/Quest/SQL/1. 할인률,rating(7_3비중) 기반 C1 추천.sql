CREATE OR REPLACE TABLE top3_by_category AS
WITH normalized AS (
  SELECT
    product_id,
    product_name,
    category_lvl1,
    discount_percentage,
    rating,
    rating_count,

    -- 카테고리 내 min-max 정규화 (분모 0 방지용 NULLIF)
    (discount_percentage - MIN(discount_percentage) OVER (PARTITION BY category_lvl1))
      / NULLIF(MAX(discount_percentage) OVER (PARTITION BY category_lvl1)
             - MIN(discount_percentage) OVER (PARTITION BY category_lvl1), 0) AS discount_norm,

    (rating - MIN(rating) OVER (PARTITION BY category_lvl1))
      / NULLIF(MAX(rating) OVER (PARTITION BY category_lvl1)
             - MIN(rating) OVER (PARTITION BY category_lvl1), 0) AS rating_norm

  FROM amazon_clean
),
scored AS (
  SELECT
    *,
    -- 정규화 결과가 NULL이면(카테고리 내 값이 전부 동일) 0.5로 대체
    0.7 * COALESCE(discount_norm, 0.5) + 0.3 * COALESCE(rating_norm, 0.5) AS recommend_score
  FROM normalized
)
SELECT
  category_lvl1,
  product_id,
  product_name,
  discount_percentage,
  rating,
  rating_count,
  ROUND(recommend_score, 4) AS recommend_score,
  ROW_NUMBER() OVER (PARTITION BY category_lvl1 ORDER BY recommend_score DESC) AS rank_in_category
FROM scored
QUALIFY rank_in_category <= 3
ORDER BY category_lvl1, rank_in_category;

SELECT * 
FROM top3_by_category