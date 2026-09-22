with source as (
    select * from {{ source('raw', 'dim_accounts') }}
),

deduped as (
    select
        trim(account_id) as account_id,
        lower(trim(customer_segment)) as customer_segment,
        trim(home_location) as home_location,
        round(avg_transaction_amount, 2) as avg_transaction_amount,
        row_number() over (partition by trim(account_id) order by account_id) as _row_num
    from source
    where account_id is not null
)

select account_id, customer_segment, home_location, avg_transaction_amount
from deduped
where _row_num = 1
