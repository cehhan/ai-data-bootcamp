CREATE OR REPLACE TABLE top3_by_savings AS
SELECT
  category_lvl1,
  product_id,
  product_name,
  actual_price,
  discounted_price,
  ROUND(actual_price - discounted_price, 2) AS savings_amount,
  discount_percentage,
  rating,
  rating_count,
  ROW_NUMBER() OVER (
    PARTITION BY category_lvl1
    ORDER BY (actual_price - discounted_price) DESC
  ) AS rank_in_category
FROM amazon_clean
QUALIFY rank_in_category <= 3
ORDER BY category_lvl1, rank_in_category;

SELECT *
FROM top3_by_savings
ORDER BY category_lvl1, rank_in_category 