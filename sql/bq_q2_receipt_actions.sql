-- near-thesis-data / sql/bq_q2_receipt_actions.sql
-- One row per UTC day, 1 November 2025 to 11 November 2026: actions executed on chain.
SELECT
  block_date,
  COUNT(*) AS actions,
  COUNTIF(action_kind = 'FUNCTION_CALL' AND receipt_receiver_account_id = 'intents.near') AS intents_calls,
  COUNT(DISTINCT IF(receipt_receiver_account_id = 'intents.near', receipt_predecessor_account_id, NULL)) AS intents_callers,
  COUNTIF(action_kind = 'DEPLOY_CONTRACT') AS deploys,
  COUNT(DISTINCT IF(action_kind = 'DEPLOY_CONTRACT', receipt_receiver_account_id, NULL)) AS contracts_deployed,
  COUNTIF(action_kind = 'CREATE_ACCOUNT') AS accounts_created,
  COUNTIF(is_delegate_action) AS delegate_actions,
  COUNT(DISTINCT IF(is_delegate_action, signer_account_id, NULL)) AS delegate_signers,
  COUNT(DISTINCT receipt_predecessor_account_id) AS predecessors
FROM `bigquery-public-data.crypto_near_mainnet_us.receipt_actions`
WHERE block_date BETWEEN '2025-11-01' AND '2026-11-11'
GROUP BY block_date
ORDER BY block_date
