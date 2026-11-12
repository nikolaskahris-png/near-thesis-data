-- near-thesis-data / sql/bq_q4_intents_call_outcomes.sql
-- Did the calls to intents.near succeed? Each call's receipt joined to its execution outcome, by kind of caller.
WITH ra AS (
  SELECT
    receipt_id,
    IF(block_date <= '2026-10-31', 'october', 'november') AS period,
    CASE
      WHEN receipt_predecessor_account_id = 'intents.near' THEN 'intents_itself'
      WHEN receipt_predecessor_account_id = 'escrow.ai.near' THEN 'near_ai_escrow'
      WHEN ENDS_WITH(receipt_predecessor_account_id, '.omft.near')
        OR receipt_predecessor_account_id IN ('wrap.near', 'nbtc.bridge.near', 'v2_1.omni.hot.tg', 'token.sweat',
          '17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1') THEN 'token_contracts'
      ELSE 'everyone_else'
    END AS kind
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
SELECT period, kind, IFNULL(eo.status, '(no outcome found)') AS status, COUNT(*) AS calls
FROM ra LEFT JOIN eo USING (receipt_id)
GROUP BY period, kind, status
ORDER BY period DESC, kind, status
