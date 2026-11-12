-- near-thesis-data / sql/bq_q1_transactions.sql
-- One row per UTC day, 1 November 2025 to 11 November 2026, from NEAR's public BigQuery dataset.
SELECT
  block_date,
  COUNT(*) AS txns,
  COUNT(DISTINCT signer_account_id) AS signers,
  COUNTIF(receiver_account_id = 'intents.near') AS txns_to_intents,
  COUNT(DISTINCT IF(receiver_account_id = 'intents.near', signer_account_id, NULL)) AS signers_to_intents,
  SUM(receipt_conversion_tokens_burnt) / 1e24 AS conversion_burnt_near
FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
WHERE block_date BETWEEN '2025-11-01' AND '2026-11-11'
GROUP BY block_date
ORDER BY block_date
