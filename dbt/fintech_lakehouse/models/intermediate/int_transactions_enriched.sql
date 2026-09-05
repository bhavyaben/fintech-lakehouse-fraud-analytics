

select
    t.transaction_id,
    t.account_id,
    t.merchant_id,
    t.transaction_type,
    t.amount,
    t.channel,
    t.transaction_timestamp,
    t.status,
    t.is_fraud,
    m.category as merchant_category,
    m.risk_score as merchant_risk_score,
    m.is_foreign as merchant_is_foreign
from {{ ref('stg_transactions') }} t
left join {{ ref('stg_merchants') }} m
    on t.merchant_id = m.merchant_id