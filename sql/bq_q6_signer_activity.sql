-- near-thesis-data / sql/bq_q6_signer_activity.sql
-- One row per UTC day, 1 November 2025 to 11 November 2026: how transactions spread over the accounts that sign them.
-- "Light" signers sent at most 10 transactions that day: accounts that act at a person's pace. Users whose
-- transactions a relayer signs (meta transactions) are not signers here, so this undercounts people.
WITH d AS (
  SELECT block_date, signer_account_id, COUNT(*) AS n
  FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
  WHERE block_date BETWEEN '2025-11-01' AND '2026-11-11'
  GROUP BY block_date, signer_account_id
), r AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY block_date ORDER BY n DESC, signer_account_id) AS rk FROM d
)
SELECT
  block_date,
  COUNT(*) AS signers,
  SUM(n) AS txns,
  SUM(IF(rk <= 10, n, 0)) AS txns_top10,
  SUM(IF(rk <= 100, n, 0)) AS txns_top100,
  COUNTIF(n <= 10) AS signers_light,
  SUM(IF(n <= 10, n, 0)) AS txns_light,
  COUNTIF(n > 1000) AS signers_heavy
FROM r
GROUP BY block_date
ORDER BY block_date
