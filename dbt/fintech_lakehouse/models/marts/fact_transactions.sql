{{
  config(
    materialized = 'incremental',
    unique_key = 'transaction_id'
    )
}}

select 
    transaction_id,
    account_id,
    merchant_id,
    transaction_type,
    amount,
    channel,
    transaction_timestamp,
    status,
    is_fraud,
    merchant_category,
    merchant_risk_score,
    merchant_is_foreign
from {{ ref('int_transactions_enriched') }}

{% if is_incremental() %}
where transaction_timestamp > 
    (select max(transaction_timestamp) from {{this}})
{% endif %}