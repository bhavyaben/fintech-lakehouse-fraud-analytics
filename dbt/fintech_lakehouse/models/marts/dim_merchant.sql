select 
    merchant_id,
    category,
    mcc_code,
    risk_score,
    is_foreign
from {{ref("stg_merchants")}}