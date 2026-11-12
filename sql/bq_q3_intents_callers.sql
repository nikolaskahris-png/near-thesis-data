-- near-thesis-data / sql/bq_q3_intents_callers.sql
-- Who calls intents.near: the 20 accounts with the most calls in 2-31 October 2026, everyone else in one row.
WITH c AS (
  SELECT
    receipt_predecessor_account_id AS caller,
    COUNTIF(block_date BETWEEN '2026-10-02' AND '2026-10-31') AS calls_oct,
    COUNTIF(block_date BETWEEN '2026-11-01' AND '2026-11-11') AS calls_nov
  FROM `bigquery-public-data.crypto_near_mainnet_us.receipt_actions`
  WHERE block_date BETWEEN '2026-10-02' AND '2026-11-11'
    AND action_kind = 'FUNCTION_CALL'
    AND receipt_receiver_account_id = 'intents.near'
  GROUP BY caller
), r AS (
  SELECT *, ROW_NUMBER() OVER (ORDER BY calls_oct DESC, caller) AS rk FROM c
)
SELECT
  MIN(rk) AS rank,
  IF(rk <= 20, caller, '(all other accounts)') AS caller,
  SUM(calls_oct) AS calls_oct,
  SUM(calls_nov) AS calls_nov,
  COUNT(*) AS accounts
FROM r
GROUP BY 2
ORDER BY rank
