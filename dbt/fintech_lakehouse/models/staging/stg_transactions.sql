


select
    transaction_id,
    account_id,
    merchant_id,
    type as transaction_type,
    amount,
    channel,
    timestamp as transaction_timestamp,
    status,
    is_fraud
from {{ source('silver', 'transactions') }}