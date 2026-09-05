select account_id,
customer_id,
account_type,
status as account_status,
open_date,
close_date,
_source_file,
_ingested_at,
_status_flag,
effective_start_date,
effective_end_date,
is_current
from {{ source('silver', 'accounts')}}