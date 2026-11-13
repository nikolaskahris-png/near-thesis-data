-- near-thesis-data / sql/bq_q5_intents_calls_by_path.sql
-- Calls to intents.near split by path, method and outcome (fix for review K3-D, M1):
--   relay    = top-level execute_intents transactions that intents.near signs with its own FunctionCall keys
--              (users' and solvers' signed intents, submitted by the relay)
--   callback = receipts intents.near sends to itself that are not a top-level transaction
--   escrow / token / other = calls whose predecessor is that account
WITH t AS (
  SELECT converted_into_receipt_id, signer_account_id
  FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
  WHERE block_date BETWEEN '2026-10-01' AND '2026-11-11'
    AND receiver_account_id = 'intents.near'
), ra AS (
  SELECT
    receipt_id,
    IF(block_date <= '2026-10-31', 'october', 'november') AS period,
    receipt_predecessor_account_id AS predecessor,
    JSON_VALUE(args, '$.method_name') AS method
  FROM `bigquery-public-data.crypto_near_mainnet_us.receipt_actions`
  WHERE block_date BETWEEN '2026-10-02' AND '2026-11-11'
    AND action_kind = 'FUNCTION_CALL'
    AND receipt_receiver_account_id = 'intents.near'
), eo AS (
  SELECT receipt_id, status
  FROM `bigquery-public-data.crypto_near_mainnet_us.execution_outcomes`
  WHERE block_date BETWEEN '2026-10-02' AND '2026-11-12'
    AND executor_account_id = 'intents.near'
)
SELECT
  ra.period,
  CASE
    WHEN t.signer_account_id = 'intents.near' THEN 'relay'
    WHEN ra.predecessor = 'intents.near' THEN 'callback'
    WHEN ra.predecessor = 'escrow.ai.near' THEN 'near_ai_escrow'
    WHEN t.converted_into_receipt_id IS NOT NULL THEN 'other_signed_tx'
    ELSE 'other_contract'
  END AS path,
  IFNULL(ra.method, '(none)') AS method,
  IFNULL(eo.status, '(no outcome found)') AS status,
  COUNT(*) AS calls,
  COUNT(DISTINCT ra.predecessor) AS predecessors
FROM ra
LEFT JOIN t ON t.converted_into_receipt_id = ra.receipt_id
LEFT JOIN eo USING (receipt_id)
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 2, 5 DESC
