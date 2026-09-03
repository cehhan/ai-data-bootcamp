-- SQL 실무 — 분석용 데이터 마트 설계
-- 다운로드: 2026. 9. 2. 오후 4:17:45
-- 학습용 SQL 모음 — 각 섹션의 코드와 실습 쿼리를 한 파일에 정리

-- ═════════════════════════════════════════════════
-- 1. 두 환경의 문법 차이 — 한눈에 보기
-- ═════════════════════════════════════════════════

-- [C1] LMS(DuckDB) 준비 — BigQuery로 학습한다면 이 셀은 건너뜁니다.
-- BigQuery와 똑같은 `project_name.dataset_name.표` 이름을 쓸 수 있도록 이름 공간을 만듭니다.
ATTACH IF NOT EXISTS ':memory:' AS project_name;
CREATE SCHEMA IF NOT EXISTS project_name.dataset_name;

-- [C2]
CREATE OR REPLACE TABLE project_name.dataset_name.customers (
  customer_id STRING,
  name STRING,
  country STRING,
  signup_date DATE,
  grade STRING
);

INSERT INTO project_name.dataset_name.customers VALUES
  ('C001', '김민준', 'Korea', '2023-01-05', 'Gold'),
  ('C002', '이서연', 'Korea', '2023-02-11', 'Silver'),
  ('C003', '박도윤', 'Japan', '2023-02-20', 'Bronze'),
  ('C004', '최지우', 'USA', '2023-03-03', 'Gold'),
  ('C005', '정하준', 'Korea', '2023-03-15', 'Silver'),
  ('C006', '강서윤', 'Korea', '2023-04-01', 'Bronze'),
  ('C007', '조은우', 'Japan', '2023-04-18', 'Silver'),
  ('C008', '윤지호', 'USA', '2023-05-09', 'Gold'),
  ('C009', '임하은', 'Korea', '2023-05-22', 'Bronze'),
  ('C010', '한예준', 'Korea', '2023-06-02', 'Silver'),
  ('C011', '오시우', NULL, '2023-06-19', 'Bronze'),
  ('C012', '신아린', 'Japan', '2023-07-07', 'Silver'),
  ('C013', '권준서', 'Korea', '2023-07-25', 'Gold'),
  ('C014', '황지안', 'USA', '2023-08-10', NULL),
  ('C015', '안수아', 'Korea', '2023-08-28', 'Bronze')

-- [C3]
CREATE OR REPLACE TABLE project_name.dataset_name.products (
  product_id STRING,
  product_name STRING,
  category STRING,
  price DECIMAL(12,2)
);

INSERT INTO project_name.dataset_name.products VALUES
  ('P01', '에어러너', 'Running', 89000),
  ('P02', '클래식 스니커즈', 'Sneakers', 65000),
  ('P03', '첼시 부츠', 'Boots', 145000),
  ('P04', '여름 샌들', 'Sandals', 38000),
  ('P05', '트레일 러너', 'Running', 119000),
  ('P06', '캔버스 스니커즈', 'Sneakers', 49000),
  ('P07', '워커 부츠', 'Boots', 175000),
  ('P08', '슬리퍼 샌들', 'Sandals', 25000),
  ('P09', '양말 세트', 'Accessory', 12000),
  ('P10', '운동화 끈', 'Accessory', 5000)

-- [C4]
CREATE OR REPLACE TABLE project_name.dataset_name.orders (
  order_id STRING,
  customer_id STRING,
  order_date DATE,
  status STRING,
  amount DECIMAL(12,2)
);

INSERT INTO project_name.dataset_name.orders VALUES
  ('O0001', 'C001', '2023-09-02', 'Paid', 125000),
  ('O0002', 'C002', '2023-09-05', 'Shipped', 89000),
  ('O0003', 'C001', '2023-09-11', 'Returned', 45000),
  ('O0004', 'C003', '2023-09-15', 'Paid', 230000),
  ('O0005', 'C004', '2023-09-20', 'Cancelled', NULL),
  ('O0006', 'C005', '2023-09-25', 'Shipped', 67000),
  ('O0007', 'C002', '2023-10-01', 'Paid', 158000),
  ('O0008', 'C006', '2023-10-04', 'Placed', 32000),
  ('O0009', 'C007', '2023-10-12', 'Shipped', 410000),
  ('O0010', 'C008', '2023-10-19', 'Paid', 99000),
  ('O0011', 'C001', '2023-10-23', 'Paid', 76000),
  ('O0012', 'C009', '2023-10-28', 'Cancelled', NULL),
  ('O0013', 'C010', '2023-11-02', 'Shipped', 142000),
  ('O0014', 'C004', '2023-11-08', 'Paid', 88000),
  ('O0015', 'C011', '2023-11-13', 'Placed', 53000),
  ('O0016', 'C012', '2023-11-19', 'Shipped', 175000),
  ('O0017', 'C002', '2023-11-24', 'Returned', 61000),
  ('O0018', 'C013', '2023-11-29', 'Paid', 320000),
  ('O0019', 'C005', '2023-12-03', 'Paid', 47000),
  ('O0020', 'C008', '2023-12-09', 'Shipped', 215000),
  ('O0021', 'C014', '2023-12-14', 'Placed', 38000),
  ('O0022', 'C001', '2023-12-20', 'Paid', 134000),
  ('O0023', 'C015', '2023-12-25', 'Shipped', 92000),
  ('O0024', 'C007', '2024-01-03', 'Paid', 268000),
  ('O0025', 'C010', '2024-01-09', 'Cancelled', NULL),
  ('O0026', 'C003', '2024-01-15', 'Paid', 119000),
  ('O0027', 'C013', '2024-01-22', 'Shipped', 405000),
  ('O0028', 'C006', '2024-01-28', 'Paid', 58000),
  ('O0029', 'C004', '2024-02-04', 'Returned', 73000),
  ('O0030', 'C012', '2024-02-11', 'Paid', 187000)

-- [C5]
CREATE OR REPLACE TABLE project_name.dataset_name.order_items (
  order_id STRING,
  product_id STRING,
  quantity INT64,
  unit_price DECIMAL(12,2)
);

INSERT INTO project_name.dataset_name.order_items VALUES
  ('O0001', 'P01', 1, 125000),
  ('O0002', 'P02', 2, 44500),
  ('O0003', 'P03', 1, 45000),
  ('O0004', 'P04', 2, 115000),
  ('O0006', 'P05', 1, 67000),
  ('O0007', 'P06', 2, 79000),
  ('O0008', 'P07', 1, 32000),
  ('O0009', 'P08', 2, 205000),
  ('O0010', 'P09', 1, 99000),
  ('O0011', 'P01', 2, 38000),
  ('O0013', 'P02', 1, 142000),
  ('O0014', 'P03', 2, 44000),
  ('O0015', 'P04', 1, 53000),
  ('O0016', 'P05', 2, 87500),
  ('O0017', 'P06', 1, 61000),
  ('O0018', 'P07', 2, 160000),
  ('O0019', 'P08', 1, 47000),
  ('O0020', 'P09', 2, 107500),
  ('O0021', 'P01', 1, 38000),
  ('O0022', 'P02', 2, 67000),
  ('O0023', 'P03', 1, 92000),
  ('O0024', 'P04', 2, 134000),
  ('O0026', 'P05', 1, 119000),
  ('O0027', 'P06', 2, 202500),
  ('O0028', 'P07', 1, 58000),
  ('O0029', 'P08', 2, 36500),
  ('O0030', 'P09', 1, 187000)

-- [C6]
CREATE OR REPLACE TABLE project_name.dataset_name.events (
  event_id INT64,
  customer_id STRING,
  event_type STRING,
  page STRING,
  event_at TIMESTAMP
);

INSERT INTO project_name.dataset_name.events VALUES
  (1, 'C001', 'visit', 'home', TIMESTAMP '2023-09-02 10:02:11'),
  (2, 'C001', 'view', 'product_detail', TIMESTAMP '2023-09-02 10:04:35'),
  (3, 'C001', 'view', 'product_detail', TIMESTAMP '2023-09-02 10:07:20'),
  (4, 'C001', 'add_to_cart', 'cart', TIMESTAMP '2023-09-02 10:11:02'),
  (5, 'C001', 'purchase', 'checkout', TIMESTAMP '2023-09-02 10:14:47'),
  (6, 'C001', 'visit', 'home', TIMESTAMP '2023-10-18 09:31:04'),
  (7, 'C001', 'view', 'product_detail', TIMESTAMP '2023-10-18 09:33:50'),
  (8, 'C001', 'visit', 'home', TIMESTAMP '2023-11-14 20:12:33'),
  (9, 'C002', 'visit', 'home', TIMESTAMP '2023-09-05 14:20:05'),
  (10, 'C002', 'view', 'product_detail', TIMESTAMP '2023-09-05 14:22:41'),
  (11, 'C002', 'add_to_cart', 'cart', TIMESTAMP '2023-09-05 14:27:19'),
  (12, 'C002', 'purchase', 'checkout', TIMESTAMP '2023-09-05 14:31:58'),
  (13, 'C002', 'visit', 'home', TIMESTAMP '2023-10-09 11:05:22'),
  (14, 'C002', 'view', 'product_detail', TIMESTAMP '2023-10-09 11:08:44'),
  (15, 'C003', 'visit', 'home', TIMESTAMP '2023-09-15 09:14:30'),
  (16, 'C003', 'view', 'product_detail', TIMESTAMP '2023-09-15 09:17:12'),
  (17, 'C003', 'add_to_cart', 'cart', TIMESTAMP '2023-09-15 09:21:40'),
  (18, 'C003', 'purchase', 'checkout', TIMESTAMP '2023-09-15 09:26:03'),
  (19, 'C003', 'visit', 'home', TIMESTAMP '2023-11-07 21:40:15'),
  (20, 'C003', 'view', 'product_detail', TIMESTAMP '2023-11-07 21:43:02'),
  (21, 'C004', 'visit', 'home', TIMESTAMP '2023-09-18 16:03:11'),
  (22, 'C004', 'view', 'product_detail', TIMESTAMP '2023-09-18 16:06:29'),
  (23, 'C004', 'visit', 'home', TIMESTAMP '2023-11-05 10:55:07'),
  (24, 'C004', 'view', 'product_detail', TIMESTAMP '2023-11-05 10:58:33'),
  (25, 'C005', 'visit', 'home', TIMESTAMP '2023-09-22 08:40:19'),
  (26, 'C006', 'visit', 'home', TIMESTAMP '2023-10-04 13:11:02'),
  (27, 'C006', 'view', 'product_detail', TIMESTAMP '2023-10-04 13:13:47'),
  (28, 'C006', 'add_to_cart', 'cart', TIMESTAMP '2023-10-04 13:18:20'),
  (29, 'C006', 'purchase', 'checkout', TIMESTAMP '2023-10-04 13:22:55'),
  (30, 'C006', 'visit', 'home', TIMESTAMP '2023-11-16 19:02:41'),
  (31, 'C006', 'visit', 'home', TIMESTAMP '2023-12-05 12:30:18'),
  (32, 'C006', 'view', 'product_detail', TIMESTAMP '2023-12-05 12:33:04'),
  (33, 'C007', 'visit', 'home', TIMESTAMP '2023-10-12 10:45:33'),
  (34, 'C007', 'view', 'product_detail', TIMESTAMP '2023-10-12 10:48:09'),
  (35, 'C007', 'view', 'product_detail', TIMESTAMP '2023-10-12 10:52:41'),
  (36, 'C007', 'add_to_cart', 'cart', TIMESTAMP '2023-10-12 10:57:12'),
  (37, 'C007', 'purchase', 'checkout', TIMESTAMP '2023-10-12 11:02:38'),
  (38, 'C007', 'visit', 'home', TIMESTAMP '2023-11-21 15:20:07'),
  (39, 'C007', 'view', 'product_detail', TIMESTAMP '2023-11-21 15:23:55'),
  (40, 'C008', 'visit', 'home', TIMESTAMP '2023-10-16 17:30:44'),
  (41, 'C008', 'view', 'product_detail', TIMESTAMP '2023-10-16 17:33:21'),
  (42, 'C008', 'visit', 'home', TIMESTAMP '2023-12-13 11:15:02'),
  (43, 'C008', 'view', 'product_detail', TIMESTAMP '2023-12-13 11:18:39'),
  (44, 'C009', 'visit', 'home', TIMESTAMP '2023-10-25 20:05:13'),
  (45, 'C009', 'view', 'product_detail', TIMESTAMP '2023-10-25 20:08:47'),
  (46, 'C009', 'add_to_cart', 'cart', TIMESTAMP '2023-10-25 20:14:22'),
  (47, 'C010', 'visit', 'home', TIMESTAMP '2023-11-24 09:50:11'),
  (48, 'C010', 'view', 'product_detail', TIMESTAMP '2023-11-24 09:52:48'),
  (49, 'C010', 'add_to_cart', 'cart', TIMESTAMP '2023-11-24 09:58:30'),
  (50, 'C010', 'visit', 'home', TIMESTAMP '2023-12-18 18:22:05'),
  (51, 'C011', 'visit', 'home', TIMESTAMP '2023-11-10 14:08:26'),
  (52, 'C011', 'view', 'product_detail', TIMESTAMP '2023-11-10 14:11:03'),
  (53, 'C012', 'visit', 'home', TIMESTAMP '2023-11-19 11:40:15'),
  (54, 'C012', 'view', 'product_detail', TIMESTAMP '2023-11-19 11:42:58'),
  (55, 'C012', 'add_to_cart', 'cart', TIMESTAMP '2023-11-19 11:47:33'),
  (56, 'C012', 'purchase', 'checkout', TIMESTAMP '2023-11-19 11:52:10'),
  (57, 'C012', 'visit', 'home', TIMESTAMP '2023-12-27 16:14:40'),
  (58, 'C012', 'view', 'product_detail', TIMESTAMP '2023-12-27 16:17:22'),
  (59, 'C012', 'visit', 'home', TIMESTAMP '2024-01-08 10:20:55'),
  (60, 'C013', 'visit', 'home', TIMESTAMP '2023-11-26 13:05:30'),
  (61, 'C013', 'view', 'product_detail', TIMESTAMP '2023-11-26 13:08:12'),
  (62, 'C013', 'visit', 'home', TIMESTAMP '2024-01-19 09:44:18'),
  (63, 'C013', 'view', 'product_detail', TIMESTAMP '2024-01-19 09:47:01'),
  (64, 'C014', 'visit', 'home', TIMESTAMP '2023-12-11 19:30:22'),
  (65, 'C014', 'visit', 'home', TIMESTAMP '2024-02-06 08:15:44'),
  (66, 'C015', 'visit', 'home', TIMESTAMP '2023-12-22 10:10:05'),
  (67, 'C015', 'view', 'product_detail', TIMESTAMP '2023-12-22 10:13:40'),
  (68, 'C015', 'visit', 'home', TIMESTAMP '2024-01-11 17:55:19')

-- ═════════════════════════════════════════════════
-- 2. ▶️ **코드 실행하기 · 코드 셀 7 [C7]**
-- ═════════════════════════════════════════════════

-- [C7]
WITH order_stats AS (
  SELECT
    customer_id,
    COUNT(*) AS order_count,
    SUM(amount) AS total_spent,
    MAX(order_date) AS last_order_date
  FROM project_name.dataset_name.orders
  WHERE
    status NOT IN ('Cancelled', 'Returned')
    AND amount IS NOT NULL
  GROUP BY
    customer_id
), seg AS (
  SELECT
    COALESCE(os.total_spent, 0) AS total_spent,
    CASE
      WHEN COALESCE(os.total_spent, 0) >= 300000
      AND date_diff('day', os.last_order_date, DATE '2024-03-01') /* BigQuery: DATE_DIFF(DATE '2024-03-01', os.last_order_date, DAY) */ <= 90
      THEN '핵심 고객'
      WHEN COALESCE(os.order_count, 0) = 0
      THEN '미구매'
      WHEN date_diff('day', os.last_order_date, DATE '2024-03-01') /* BigQuery: DATE_DIFF(DATE '2024-03-01', os.last_order_date, DAY) */ > 120
      THEN '이탈 위험'
      ELSE '일반 고객'
    END AS segment
  FROM project_name.dataset_name.customers AS c
  LEFT JOIN order_stats AS os
    ON c.customer_id = os.customer_id
)
SELECT
  segment,
  COUNT(*) AS 고객수,
  ROUND(AVG(total_spent), 0) AS 평균구매액
FROM seg
GROUP BY
  segment
ORDER BY
  평균구매액 DESC

-- ═════════════════════════════════════════════════
-- 3. ▶️ **코드 실행하기 · 코드 셀 8 [C8]**
-- ═════════════════════════════════════════════════

-- [C8]
CREATE OR REPLACE TABLE project_name.dataset_name.customer_mart AS
WITH order_stats AS (
  SELECT
    customer_id,
    COUNT(*) AS order_count,
    SUM(amount) AS total_spent,
    MAX(order_date) AS last_order_date
  FROM project_name.dataset_name.orders
  WHERE
    status NOT IN ('Cancelled', 'Returned')
    AND amount IS NOT NULL
  GROUP BY
    customer_id
), web_stats AS (
  SELECT
    customer_id,
    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS web_purchased,
    date_trunc('month', DATE(MIN(event_at))) /* BigQuery: DATE_TRUNC(DATE(MIN(event_at)), MONTH) */ AS cohort_month
  FROM project_name.dataset_name.events
  GROUP BY
    customer_id
)
SELECT
  c.customer_id,
  c.name,
  c.country,
  c.grade,
  COALESCE(os.order_count, 0) AS order_count,
  COALESCE(os.total_spent, 0) AS total_spent,
  os.last_order_date,
  date_diff('day', os.last_order_date, DATE '2024-03-01') /* BigQuery: DATE_DIFF(DATE '2024-03-01', os.last_order_date, DAY) */ AS recency_days,
  CASE WHEN COALESCE(os.order_count, 0) > 0 THEN 1 ELSE 0 END AS ever_purchased,
  COALESCE(ws.web_purchased, 0) AS web_purchased,
  ws.cohort_month
FROM project_name.dataset_name.customers AS c
LEFT JOIN order_stats AS os
  ON c.customer_id = os.customer_id
LEFT JOIN web_stats AS ws
  ON c.customer_id = ws.customer_id

-- ═════════════════════════════════════════════════
-- 4. ▶️ **코드 실행하기 · 코드 셀 9 [C9]**
-- ═════════════════════════════════════════════════

-- [C9]
CREATE OR REPLACE TABLE project_name.dataset_name.customer_mart AS
SELECT
  *,
  CASE
    WHEN total_spent >= 300000 AND recency_days <= 90
    THEN '핵심 고객'
    WHEN order_count = 0
    THEN '미구매'
    WHEN recency_days > 120
    THEN '이탈 위험'
    ELSE '일반 고객'
  END AS segment
FROM project_name.dataset_name.customer_mart

-- ═════════════════════════════════════════════════
-- 5. ⌨️ 백문이 불여일타 (1)
-- ═════════════════════════════════════════════════

-- [C10] ⌨️ 백문이 불여일타 (1) — 핵심 고객 세그먼트 조회

-- 여기에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 6. ⌨️ 백문이 불여일타 (2)
-- ═════════════════════════════════════════════════

-- [C11] ⌨️ 백문이 불여일타 (2) — 미구매 고객 찾기

-- 여기에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 7. ▶️ **코드 실행하기 · 코드 셀 12 [C12]**
-- ═════════════════════════════════════════════════

-- [C12]
CREATE OR REPLACE TABLE project_name.dataset_name.daily_sales AS
SELECT
  order_date,
  COUNT(*) AS order_count,
  SUM(amount) AS revenue
FROM project_name.dataset_name.orders
WHERE
  status NOT IN ('Cancelled', 'Returned')
  AND amount IS NOT NULL
GROUP BY
  order_date
ORDER BY
  order_date NULLS LAST

-- ═════════════════════════════════════════════════
-- 8. ▶️ **코드 실행하기 · 코드 셀 13 [C13]**
-- ═════════════════════════════════════════════════

-- [C13]
SELECT
  date_trunc('month', order_date) /* BigQuery: DATE_TRUNC(order_date, MONTH) */ AS month,
  SUM(order_count) AS orders,
  SUM(revenue) AS revenue
FROM project_name.dataset_name.daily_sales
GROUP BY
  month
ORDER BY
  month NULLS LAST

-- ═════════════════════════════════════════════════
-- 9. ⌨️ 백문이 불여일타 (3)
-- ═════════════════════════════════════════════════

-- [C14] ⌨️ 백문이 불여일타 (3) — 하루 매출 TOP 3

-- 여기에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 10. ⌨️ 백문이 불여일타 (4)
-- ═════════════════════════════════════════════════

-- [C15] ⌨️ 백문이 불여일타 (4) — 주별 매출 집계

-- 여기에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 11. ▶️ **코드 실행하기 · 코드 셀 16 [C16]**
-- ═════════════════════════════════════════════════

-- [C16]
SELECT
  segment,
  COUNT(*) AS 고객수,
  ROUND(AVG(total_spent), 0) AS 평균구매액
FROM project_name.dataset_name.customer_mart
GROUP BY
  segment
ORDER BY
  평균구매액 DESC

-- ═════════════════════════════════════════════════
-- 12. ▶️ **코드 실행하기 · 코드 셀 17 [C17]**
-- ═════════════════════════════════════════════════

-- [C17]
SELECT
  country,
  COUNT(*) AS 전체,
  SUM(CASE WHEN segment = '핵심 고객' THEN 1 ELSE 0 END) AS 핵심고객수,
  ROUND(
    SUM(CASE WHEN segment = '핵심 고객' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0),
    1
  ) AS 핵심비율_pct
FROM project_name.dataset_name.customer_mart
WHERE
  country IS NOT NULL
GROUP BY
  country
ORDER BY
  핵심비율_pct DESC

-- ═════════════════════════════════════════════════
-- 13. ▶️ **코드 실행하기 · 코드 셀 18 [C18]**
-- ═════════════════════════════════════════════════

-- [C18]
SELECT
  name,
  total_spent,
  recency_days,
  segment
FROM project_name.dataset_name.customer_mart
WHERE
  segment = '이탈 위험'
ORDER BY
  total_spent DESC

-- ═════════════════════════════════════════════════
-- 14. ▶️ **코드 실행하기 · 코드 셀 19 [C19]**
-- ═════════════════════════════════════════════════

-- [C19]
SELECT
  grade,
  COUNT(*) AS 인원,
  ROUND(AVG(total_spent), 0) AS 평균구매액
FROM project_name.dataset_name.customer_mart
WHERE
  grade IS NOT NULL
GROUP BY
  grade
ORDER BY
  평균구매액 DESC

-- ═════════════════════════════════════════════════
-- 15. ▶️ **코드 실행하기 · 코드 셀 20 [C20]**
-- ═════════════════════════════════════════════════

-- [C20]
SELECT
  COUNT(*) AS 전체고객,
  SUM(CASE WHEN ever_purchased = 1 THEN 1 ELSE 0 END) AS 구매고객,
  ROUND(SUM(total_spent), 0) AS 총매출,
  ROUND(AVG(CASE WHEN order_count > 0 THEN total_spent END), 0) AS 구매자_ARPU
FROM project_name.dataset_name.customer_mart

-- ═════════════════════════════════════════════════
-- 16. ▶️ **코드 실행하기 · 코드 셀 21 [C21]**
-- ═════════════════════════════════════════════════

-- [C21]
CREATE OR REPLACE TABLE project_name.dataset_name.product_mart AS
WITH sales AS (
  SELECT
    oi.product_id,
    SUM(oi.quantity) AS total_qty,
    SUM(oi.quantity * oi.unit_price) AS revenue,
    COUNT(DISTINCT oi.order_id) AS order_count
  FROM project_name.dataset_name.order_items AS oi
  JOIN project_name.dataset_name.orders AS o
    ON oi.order_id = o.order_id
  WHERE
    o.status NOT IN ('Cancelled', 'Returned')
  GROUP BY
    oi.product_id
),
returned AS (
  SELECT
    oi.product_id,
    COUNT(DISTINCT oi.order_id) AS returned_orders
  FROM project_name.dataset_name.order_items AS oi
  JOIN project_name.dataset_name.orders AS o
    ON oi.order_id = o.order_id
  WHERE
    o.status IN ('Cancelled', 'Returned')
  GROUP BY
    oi.product_id
)
SELECT
  p.product_id,
  p.product_name,
  p.category,
  p.price,
  COALESCE(s.total_qty, 0) AS total_qty,
  COALESCE(s.revenue, 0) AS revenue,
  COALESCE(s.order_count, 0) AS order_count,
  COALESCE(r.returned_orders, 0) AS returned_orders,
  CASE WHEN COALESCE(s.order_count, 0) = 0 THEN 0 ELSE 1 END AS ever_sold
FROM project_name.dataset_name.products AS p
LEFT JOIN sales AS s
  ON p.product_id = s.product_id
LEFT JOIN returned AS r
  ON p.product_id = r.product_id

-- ═════════════════════════════════════════════════
-- 17. ▶️ **코드 실행하기 · 코드 셀 22 [C22]**
-- ═════════════════════════════════════════════════

-- [C22]
SELECT
  category,
  COUNT(*) AS 상품수,
  SUM(revenue) AS 매출,
  SUM(returned_orders) AS 취소반품건수,
  ROUND(
    SUM(returned_orders) * 100.0 / NULLIF(SUM(order_count) + SUM(returned_orders), 0),
    1
  ) AS 취소반품율_pct
FROM project_name.dataset_name.product_mart
GROUP BY
  category
ORDER BY
  매출 DESC

-- ═════════════════════════════════════════════════
-- 18. ⌨️ 백문이 불여일타 (5)
-- ═════════════════════════════════════════════════

-- [C23] ⌨️ 백문이 불여일타 (5) — 카테고리별 판매수량과 매출

-- 여기에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 19. ▶️ **코드 실행하기 · 코드 셀 24 [C24]**
-- ═════════════════════════════════════════════════

-- [C24]
CREATE OR REPLACE VIEW project_name.dataset_name.v_active_customers AS
SELECT
  customer_id,
  name,
  country,
  grade
FROM project_name.dataset_name.customers
WHERE
  country IS NOT NULL

-- ═════════════════════════════════════════════════
-- 20. ▶️ **코드 실행하기 · 코드 셀 25 [C25]**
-- ═════════════════════════════════════════════════

-- [C25]
SELECT
  country,
  COUNT(*) AS 고객수
FROM project_name.dataset_name.v_active_customers
GROUP BY
  country
ORDER BY
  고객수 DESC

-- ═════════════════════════════════════════════════
-- 21. 📒 연습 문제 — 데이터 마트 활용 (5문항)
-- ═════════════════════════════════════════════════

-- [C26] 📒 연습 문제 — 데이터 마트 활용 (1/5)

-- 문제: customer_mart에서 recency_days 구간별(0~30일·31~90일·91일 이상) 고객 수와 평균 구매액을 구합니다. (recency_days가 NULL인 고객은 '주문 없음'으로 묶습니다)

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 22. <details>
-- ═════════════════════════════════════════════════

-- [C27] 📒 연습 문제 — 데이터 마트 활용 (2/5)

-- 문제: product_mart에서 한 번도 팔리지 않은 상품을 찾습니다.

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 23. <details>
-- ═════════════════════════════════════════════════

-- [C28] 📒 연습 문제 — 데이터 마트 활용 (3/5)

-- 문제: daily_sales에서 월별 매출과, 첫 달부터 그 달까지 더한 누적 매출을 함께 구합니다.

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 24. <details>
-- ═════════════════════════════════════════════════

-- [C29] 📒 연습 문제 — 데이터 마트 활용 (4/5)

-- 문제: 카테고리별 매출과, 팔린 상품 1개당 평균 매출을 구합니다. (한 번도 팔리지 않은 상품은 분모에서 제외)

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 25. <details>
-- ═════════════════════════════════════════════════

-- [C30] 📒 연습 문제 — 데이터 마트 활용 (5/5)

-- 문제: 등급(grade)이 비어 있지 않은 고객만 담는 뷰 v_graded_customers를 만들고 조회합니다.

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 26. **질문 1.** `daily_sales`에서 **월별 주문수·매출과 전월 대비 증감률(%)** 을 구합니다. 매출 추이 리포트가 됩니다.
-- ═════════════════════════════════════════════════

-- [C31] 🧪 종합 실습 — SQL 분석 포트폴리오 구성 (1/3)

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 27. **질문 2.** `product_mart`에서 **매출 상위 3개 상품**의 상품명·카테고리·매출·취소반품건수를 조회합니다. 상품 리포트가 됩니다.
-- ═════════════════════════════════════════════════

-- [C32] 🧪 종합 실습 — SQL 분석 포트폴리오 구성 (2/3)

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 28. **질문 3.** `customer_mart`에서 세그먼트별 **고객 수·총매출·평균 구매액**과, 각 세그먼트가 **전체 매출에서 차지하는 비중(%)** 을 함께 구합니다. 고객 리포트가 됩니다.
-- ═════════════════════════════════════════════════

-- [C33] 🧪 종합 실습 — SQL 분석 포트폴리오 구성 (3/3)

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 29. 코드 퀴즈
-- ═════════════════════════════════════════════════

-- [C34] 코드 퀴즈 — 세그먼트별 총매출 합계

-- 여기에 SQL 쿼리를 작성하세요.
