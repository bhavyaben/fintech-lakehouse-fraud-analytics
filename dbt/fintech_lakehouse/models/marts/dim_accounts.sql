select account_id,
customer_id,
account_type,
account_status,
open_date,
close_date,
effective_start_date,
effective_end_date,
is_current
from {{ref("stg_accounts")}}