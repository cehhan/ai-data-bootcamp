-- SQL 실무 — 사용자 행동 지표 분석
-- 다운로드: 2026. 9. 2. 오후 3:14:08
-- 학습용 SQL 모음 — 각 섹션의 코드와 실습 쿼리를 한 파일에 정리

-- ═════════════════════════════════════════════════
-- 1. 두 환경의 문법 차이 — 한눈에 보기
-- ═════════════════════════════════════════════════

-- [C1] LMS(DuckDB) 준비 — BigQuery로 학습한다면 이 셀은 건너뛰세요.
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

-- [C4]
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
-- 2. ▶️ **코드 실행하기 · 코드 셀 5 [C5]**
-- ═════════════════════════════════════════════════

-- [C5]
SELECT
  COUNT(*) AS PV_상품조회수,
  COUNT(DISTINCT customer_id) AS UV_고유방문자
FROM project_name.dataset_name.events
WHERE
  event_type = 'view'

-- ═════════════════════════════════════════════════
-- 3. ▶️ **코드 실행하기 · 코드 셀 6 [C6]**
-- ═════════════════════════════════════════════════

-- [C6]
WITH revenue AS (
  SELECT
    SUM(amount) AS total_revenue
  FROM project_name.dataset_name.orders
  WHERE
    status NOT IN ('Cancelled', 'Returned')
    AND amount IS NOT NULL
), active AS (
  SELECT
    COUNT(DISTINCT customer_id) AS active_users
  FROM project_name.dataset_name.events
), paying AS (
  SELECT
    COUNT(DISTINCT customer_id) AS paying_users
  FROM project_name.dataset_name.orders
  WHERE
    status NOT IN ('Cancelled', 'Returned')
    AND amount IS NOT NULL
)
SELECT
  total_revenue AS 총매출,
  active_users AS 활성사용자수,
  paying_users AS 구매사용자수,
  ROUND(total_revenue * 1.0 / NULLIF(active_users, 0), 0) AS ARPU,
  ROUND(total_revenue * 1.0 / NULLIF(paying_users, 0), 0) AS ARPPU
FROM revenue
CROSS JOIN active
CROSS JOIN paying

-- ═════════════════════════════════════════════════
-- 4. ⌨️ 백문이 불여일타 (1)
-- ═════════════════════════════════════════════════

-- [C7] ⌨️ 백문이 불여일타 (1) — 전체 이벤트 수(PV)와 고유 사용자 수(UV)

-- 여기에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 5. ▶️ **코드 실행하기 · 코드 셀 8 [C8]**
-- ═════════════════════════════════════════════════

-- [C8]
SELECT
  page,
  COUNT(*) AS PV,
  COUNT(DISTINCT customer_id) AS UV
FROM project_name.dataset_name.events
GROUP BY
  page
ORDER BY
  PV DESC

-- ═════════════════════════════════════════════════
-- 6. ⌨️ 백문이 불여일타 (2)
-- ═════════════════════════════════════════════════

-- [C9] ⌨️ 백문이 불여일타 (2) — 이벤트 종류별 UV 많은 순

-- 여기에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 7. ⌨️ 백문이 불여일타 (3)
-- ═════════════════════════════════════════════════

-- [C10] ⌨️ 백문이 불여일타 (3) — 국가별 구매 고객 수와 ARPPU

-- 여기에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 8. ▶️ **코드 실행하기 · 코드 셀 11 [C11]**
-- ═════════════════════════════════════════════════

-- [C11]
SELECT
  COUNT(DISTINCT CASE WHEN event_type = 'visit' THEN customer_id END) AS visit,
  COUNT(DISTINCT CASE WHEN event_type = 'view' THEN customer_id END) AS view,
  COUNT(DISTINCT CASE WHEN event_type = 'add_to_cart' THEN customer_id END) AS add_to_cart,
  COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN customer_id END) AS purchase
FROM project_name.dataset_name.events

-- ═════════════════════════════════════════════════
-- 9. ▶️ **코드 실행하기 · 코드 셀 12 [C12]**
-- ═════════════════════════════════════════════════

-- [C12]
WITH funnel AS (
  SELECT
    COUNT(DISTINCT CASE WHEN event_type = 'visit' THEN customer_id END) AS visit,
    COUNT(DISTINCT CASE WHEN event_type = 'view' THEN customer_id END) AS view,
    COUNT(DISTINCT CASE WHEN event_type = 'add_to_cart' THEN customer_id END) AS cart,
    COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN customer_id END) AS purchase
  FROM project_name.dataset_name.events
)
SELECT
  visit,
  view,
  cart,
  purchase,
  ROUND(view * 100.0 / NULLIF(visit, 0), 1) AS 방문대비_조회도달률,
  ROUND(cart * 100.0 / NULLIF(visit, 0), 1) AS 방문대비_장바구니도달률,
  ROUND(purchase * 100.0 / NULLIF(visit, 0), 1) AS 방문대비_구매도달률
FROM funnel

-- ═════════════════════════════════════════════════
-- 10. ⌨️ 백문이 불여일타 (4)
-- ═════════════════════════════════════════════════

-- [C13] ⌨️ 백문이 불여일타 (4) — 장바구니 → 구매 전환율

-- 여기에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 11. ▶️ **코드 실행하기 · 코드 셀 14 [C14]**
-- ═════════════════════════════════════════════════

-- [C14]
WITH funnel AS (
  SELECT
    COUNT(DISTINCT CASE WHEN event_type = 'visit' THEN customer_id END) AS visit,
    COUNT(DISTINCT CASE WHEN event_type = 'view' THEN customer_id END) AS view,
    COUNT(DISTINCT CASE WHEN event_type = 'add_to_cart' THEN customer_id END) AS cart,
    COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN customer_id END) AS purchase
  FROM project_name.dataset_name.events
)
SELECT
  visit - view AS 방문후_이탈,
  view - cart AS 조회후_이탈,
  cart - purchase AS 장바구니후_이탈
FROM funnel

-- ═════════════════════════════════════════════════
-- 12. ▶️ **코드 실행하기 · 코드 셀 15 [C15]**
-- ═════════════════════════════════════════════════

-- [C15]
WITH first_seen AS (
  SELECT
    customer_id,
    date_trunc('month', DATE(MIN(event_at))) /* BigQuery: DATE_TRUNC(DATE(MIN(event_at)), MONTH) */ AS cohort_month
  FROM project_name.dataset_name.events
  GROUP BY
    customer_id
)
SELECT
  cohort_month,
  COUNT(*) AS 코호트_고객수
FROM first_seen
GROUP BY
  cohort_month
ORDER BY
  cohort_month NULLS LAST

-- ═════════════════════════════════════════════════
-- 13. ▶️ **코드 실행하기 · 코드 셀 16 [C16]**
-- ═════════════════════════════════════════════════

-- [C16]
WITH first_seen AS (
  SELECT
    customer_id,
    date_trunc('month', DATE(MIN(event_at))) /* BigQuery: DATE_TRUNC(DATE(MIN(event_at)), MONTH) */ AS cohort_month
  FROM project_name.dataset_name.events
  GROUP BY
    customer_id
), activity AS (
  SELECT DISTINCT
    customer_id,
    date_trunc('month', DATE(event_at)) /* BigQuery: DATE_TRUNC(DATE(event_at), MONTH) */ AS active_month
  FROM project_name.dataset_name.events
), joined AS (
  SELECT
    f.cohort_month,
    date_diff('month', f.cohort_month, a.active_month) /* BigQuery: DATE_DIFF(a.active_month, f.cohort_month, MONTH) */ AS month_offset,
    a.customer_id
  FROM first_seen AS f
  JOIN activity AS a
    ON f.customer_id = a.customer_id
)
SELECT
  cohort_month,
  COUNT(DISTINCT CASE WHEN month_offset = 0 THEN customer_id END) AS 경과0개월,
  COUNT(DISTINCT CASE WHEN month_offset = 1 THEN customer_id END) AS 경과1개월,
  COUNT(DISTINCT CASE WHEN month_offset = 2 THEN customer_id END) AS 경과2개월
FROM joined
GROUP BY
  cohort_month
ORDER BY
  cohort_month NULLS LAST

-- ═════════════════════════════════════════════════
-- 14. ⌨️ 백문이 불여일타 (5)
-- ═════════════════════════════════════════════════

-- [C17] ⌨️ 백문이 불여일타 (5) — 코호트 1개월 리텐션율(%)

-- 여기에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 15. ▶️ **코드 실행하기 · 코드 셀 18 [C18]**
-- ═════════════════════════════════════════════════

-- [C18]
SELECT
  customer_id,
  date_diff('day', MAX(order_date), DATE '2024-03-01') /* BigQuery: DATE_DIFF(DATE '2024-03-01', MAX(order_date), DAY) */ AS recency_일,
  COUNT(*) AS frequency_횟수,
  SUM(amount) AS monetary_총액
FROM project_name.dataset_name.orders
WHERE
  status NOT IN ('Cancelled', 'Returned')
  AND amount IS NOT NULL
GROUP BY
  customer_id
ORDER BY
  monetary_총액 DESC

-- ═════════════════════════════════════════════════
-- 16. ▶️ **코드 실행하기 · 코드 셀 19 [C19]**
-- ═════════════════════════════════════════════════

-- [C19]
WITH rfm AS (
  SELECT
    customer_id,
    date_diff('day', MAX(order_date), DATE '2024-03-01') /* BigQuery: DATE_DIFF(DATE '2024-03-01', MAX(order_date), DAY) */ AS recency,
    COUNT(*) AS frequency,
    SUM(amount) AS monetary
  FROM project_name.dataset_name.orders
  WHERE
    status NOT IN ('Cancelled', 'Returned')
    AND amount IS NOT NULL
  GROUP BY
    customer_id
)
SELECT
  customer_id,
  recency,
  frequency,
  monetary,
  CASE
    WHEN monetary >= 300000 AND recency <= 90
    THEN '핵심 고객'
    WHEN recency > 120
    THEN '이탈 위험'
    ELSE '일반 고객'
  END AS 고객등급
FROM rfm
ORDER BY
  monetary DESC

-- ═════════════════════════════════════════════════
-- 17. ⌨️ 백문이 불여일타 (6)
-- ═════════════════════════════════════════════════

-- [C20] ⌨️ 백문이 불여일타 (6) — Monetary 상위 3명 + RANK 순위

-- 여기에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 18. ▶️ **코드 실행하기 · 코드 셀 21 [C21]**
-- ═════════════════════════════════════════════════

-- [C21]
WITH rfm AS (
  SELECT
    customer_id,
    date_diff('day', MAX(order_date), DATE '2024-03-01') /* BigQuery: DATE_DIFF(DATE '2024-03-01', MAX(order_date), DAY) */ AS recency,
    COUNT(*) AS frequency,
    SUM(amount) AS monetary
  FROM project_name.dataset_name.orders
  WHERE
    status NOT IN ('Cancelled', 'Returned')
    AND amount IS NOT NULL
  GROUP BY
    customer_id
)
SELECT
  customer_id,
  recency,
  frequency,
  monetary,
  NTILE(4) OVER (ORDER BY recency DESC NULLS FIRST) AS R점수,
  NTILE(4) OVER (ORDER BY frequency ASC) AS F점수,
  NTILE(4) OVER (ORDER BY monetary ASC) AS M점수
FROM rfm
ORDER BY
  monetary DESC

-- ═════════════════════════════════════════════════
-- 19. ▶️ **코드 실행하기 · 코드 셀 22 [C22]**
-- ═════════════════════════════════════════════════

-- [C22]
SELECT
  COUNT(*) AS 전체주문,
  SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) AS 취소,
  SUM(CASE WHEN status = 'Returned' THEN 1 ELSE 0 END) AS 반품,
  ROUND(
    SUM(CASE WHEN status IN ('Cancelled', 'Returned') THEN 1 ELSE 0 END) * 100.0
      / NULLIF(COUNT(*), 0),
    1
  ) AS 취소반품율_pct
FROM project_name.dataset_name.orders

-- ═════════════════════════════════════════════════
-- 20. ▶️ **코드 실행하기 · 코드 셀 23 [C23]**
-- ═════════════════════════════════════════════════

-- [C23]
SELECT
  status,
  COUNT(*) AS 건수,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS 건수비중_pct,
  SUM(amount) AS 금액,
  ROUND(SUM(amount) * 100.0 / SUM(SUM(amount)) OVER (), 1) AS 금액비중_pct
FROM project_name.dataset_name.orders
GROUP BY
  status
ORDER BY
  건수 DESC

-- ═════════════════════════════════════════════════
-- 21. ▶️ **코드 실행하기 · 코드 셀 24 [C24]**
-- ═════════════════════════════════════════════════

-- [C24]
WITH cust AS (
  SELECT
    customer_id,
    COUNT(*) AS 구매횟수,
    SUM(amount) AS 총구매액,
    MAX(order_date) AS 최근구매일,
    date_diff('day', MAX(order_date), DATE '2024-03-01') /* BigQuery: DATE_DIFF(DATE '2024-03-01', MAX(order_date), DAY) */ AS 경과일
  FROM project_name.dataset_name.orders
  WHERE
    status NOT IN ('Cancelled', 'Returned')
    AND amount IS NOT NULL
  GROUP BY
    customer_id
)
SELECT
  customer_id,
  구매횟수,
  총구매액,
  최근구매일,
  경과일,
  CASE
    WHEN 경과일 > 90 AND 구매횟수 >= 2 THEN '⚠️ 이탈 위험 (단골이었음)'
    WHEN 경과일 > 90 THEN '😐 휴면'
    WHEN 구매횟수 >= 2 THEN '✅ 우량'
    ELSE '🙂 신규·1회'
  END AS 상태
FROM cust
ORDER BY
  경과일 DESC

-- ═════════════════════════════════════════════════
-- 22. 📒 연습 문제 — 고객 행동 지표 (5문항)
-- ═════════════════════════════════════════════════

-- [C25] 📒 연습 문제 — 고객 행동 지표 (1/5)

-- 문제: 전체 이벤트 수(PV)와 고유 사용자 수(UV)를 한 번에 구합니다.

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 23. <details>
-- ═════════════════════════════════════════════════

-- [C26] 📒 연습 문제 — 고객 행동 지표 (2/5)

-- 문제: event_type별 사용자 수를 구하고 많은 순으로 정렬합니다.

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 24. <details>
-- ═════════════════════════════════════════════════

-- [C27] 📒 연습 문제 — 고객 행동 지표 (3/5)

-- 문제: 정상 주문(취소·반품 제외)만으로 ARPPU(구매 사용자 1인당 평균 매출)를 구합니다.

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 25. <details>
-- ═════════════════════════════════════════════════

-- [C28] 📒 연습 문제 — 고객 행동 지표 (4/5)

-- 문제: 고객별 마지막 구매일과 그날로부터 2024-03-01까지 경과일을 구합니다.

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 26. <details>
-- ═════════════════════════════════════════════════

-- [C29] 📒 연습 문제 — 고객 행동 지표 (5/5)

-- 문제: 정상 주문의 고객별 총구매액을 NTILE(3)으로 나누세요. 1은 하, 3은 상으로 해석합니다.

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 27. 🧪 종합 실습 — 퍼널·코호트·RFM 종합 리포트
-- ═════════════════════════════════════════════════

-- [C30] 🧪 종합 실습 — 퍼널·코호트·RFM 종합 리포트 (1/2)

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 28. **질문 2.** RFM 기준으로 고객 등급별 인원을 집계합니다.
-- ═════════════════════════════════════════════════

-- [C31] 🧪 종합 실습 — 퍼널·코호트·RFM 종합 리포트 (2/2)

-- 아래에 SQL 쿼리를 작성하세요.

-- ═════════════════════════════════════════════════
-- 29. 코드 퀴즈
-- ═════════════════════════════════════════════════

-- [C32] 코드 퀴즈 — 이벤트 종류별 발생 횟수 집계

-- 여기에 SQL 쿼리를 작성하세요.
