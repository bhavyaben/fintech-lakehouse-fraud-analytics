
select 
customer_id,
first_name,
last_name,
email,
phone,
signup_date,
risk_segment,
_source_file,
_ingested_at
from {{source('silver','customers')}}