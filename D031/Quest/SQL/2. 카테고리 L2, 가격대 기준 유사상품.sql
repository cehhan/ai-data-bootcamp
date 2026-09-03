CREATE OR REPLACE TABLE similar_products AS
WITH pairs AS (
  SELECT
    a.product_id   AS source_product_id,
    a.product_name AS source_product_name,
    a.category_lvl2,
    a.discounted_price AS source_price,
    b.product_id   AS similar_product_id,
    b.product_name AS similar_product_name,
    b.discounted_price AS similar_price,
    b.rating       AS similar_rating,
    ABS(a.discounted_price - b.discounted_price) AS price_diff
  FROM amazon_clean a
  JOIN amazon_clean b
    ON a.category_lvl2 = b.category_lvl2
   AND a.product_id != b.product_id
)
SELECT
  source_product_id,
  source_product_name,
  category_lvl2,
  similar_product_id,
  similar_product_name,
  similar_price,
  similar_rating,
  price_diff,
  ROW_NUMBER() OVER (PARTITION BY source_product_id ORDER BY price_diff ASC) AS similarity_rank
FROM pairs
QUALIFY similarity_rank <= 3
ORDER BY source_product_id, similarity_rank;

SELECT * FROM similar_products
ORDER BY source_product_id, similarity_rank;