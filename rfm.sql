-- ВХОД: fact_orders(customer_id, order_id, order_date, margin, status)
-- Окно: последние 180 дней, только завершённые заказы.

WITH base AS (
  SELECT
    customer_id,
    MAX(order_date) AS last_dt,
    COUNT(*)        AS freq,
    SUM(margin)     AS money
  FROM fact_orders
  WHERE order_date >= CURRENT_DATE - INTERVAL '180 days'
    AND status = 'completed'
  GROUP BY customer_id
),
scored AS (
  SELECT
    customer_id,
    last_dt,
    (CURRENT_DATE - last_dt)                AS r_days,
    freq,
    money,
    -- Баллы 1..4
    (5 - NTILE(4) OVER (ORDER BY (CURRENT_DATE - last_dt) ASC)) AS R4,  -- меньше дней = выше балл
    NTILE(4) OVER (ORDER BY freq  DESC)                           AS F4,
    NTILE(4) OVER (ORDER BY money DESC)                           AS M4
  FROM base
),
labeled AS (
  SELECT
    customer_id, last_dt, r_days, freq, money, R4, F4, M4,
    -- Тег 1-4
    (R4::text || '-' || F4::text || '-' || M4::text) AS rfm_tag,
    -- Человеческие ярлыки
    CASE R4 WHEN 1 THEN 'Спящий' WHEN 2 THEN 'Остывающий' WHEN 3 THEN 'Тёплый' ELSE 'Недавний' END AS r_name,
    CASE F4 WHEN 1 THEN 'Единичный' WHEN 2 THEN 'Редкий' WHEN 3 THEN 'Регулярный' ELSE 'Частый' END AS f_name,
    CASE M4 WHEN 1 THEN 'Низкая ценность' WHEN 2 THEN 'Средняя' WHEN 3 THEN 'Высокая' ELSE 'Премиум' END AS m_name
  FROM scored
)
SELECT
  customer_id, last_dt, r_days AS R, freq AS F, money AS M,
  R4 AS R_bin, F4 AS F_bin, M4 AS M_bin,
  rfm_tag,
  (r_name || ' · ' || f_name || ' · ' || m_name) AS rfm_name
FROM labeled
ORDER BY R_bin DESC, F_bin DESC, M_bin DESC;
