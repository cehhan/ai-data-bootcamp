CREATE OR REPLACE TABLE tiered_recommendation AS
WITH tiered AS (
  SELECT
    *,
    NTILE(3) OVER (PARTITION BY category_lvl1 ORDER BY discounted_price) AS price_tier
  FROM amazon_clean
),
ranked AS (
  SELECT
    *,
    CASE price_tier
      WHEN 1 THEN '저가'
      WHEN 2 THEN '중가'
      WHEN 3 THEN '고가'
    END AS price_tier_label,
    ROW_NUMBER() OVER (
      PARTITION BY category_lvl1, price_tier
      ORDER BY rating DESC, rating_count DESC
    ) AS rank_in_tier
  FROM tiered
)
SELECT
  category_lvl1,
  price_tier_label,
  product_id,
  product_name,
  discounted_price,
  rating,
  rating_count
FROM ranked
WHERE rank_in_tier = 1
ORDER BY
  category_lvl1,
  CASE price_tier_label WHEN '저가' THEN 1 WHEN '중가' THEN 2 WHEN '고가' THEN 3 END;

SELECT * FROM tiered_recommendation
ORDER BY category_lvl1,
  CASE price_tier_label WHEN '저가' THEN 1 WHEN '중가' THEN 2 WHEN '고가' THEN 3 END;