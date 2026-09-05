

select 
merchant_id,
category,
mcc_code,
risk_score,
is_foreign,
_source_file,
_ingested_at
from {{ source('silver','merchants')}}