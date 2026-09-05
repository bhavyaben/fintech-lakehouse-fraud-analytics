
select 
    customer_id,
    first_name,
    last_name,
    email,
    phone,
    signup_date,
    risk_segment
from {{ ref('stg_customers') }}