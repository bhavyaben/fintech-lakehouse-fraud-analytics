select
    cast(transaction_timestamp as date) as transaction_date,
    merchant_category,
    channel,
    count(*) as transaction_count,
    sum(amount) as transaction_volume,
    sum(case when is_fraud then 1 else 0 end) as fraudulent_transactions,
    sum(case when is_fraud then amount else 0 end) as fraud_exposure,
    sum(case when is_fraud then 1 else 0 end) / nullif(count(*),0) as fraud_rate
from {{ ref('fact_transactions') }}
group by
    cast(transaction_timestamp as date),
    merchant_category,
    channel