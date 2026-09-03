CREATE OR REPLACE TABLE top3_by_value AS
SELECT
  category_lvl1,
  product_id,
  product_name,
  discounted_price,
  rating,
  rating_count,
  ROUND(rating / discounted_price, 5) AS value_score,
  ROW_NUMBER() OVER (
    PARTITION BY category_lvl1
    ORDER BY (rating / discounted_price) DESC
  ) AS rank_in_category
FROM amazon_clean
QUALIFY rank_in_category <= 3
ORDER BY category_lvl1, rank_in_category;

SELECT *
FROM top3_by_value
ORDER BY category_lvl1, rank_in_category;