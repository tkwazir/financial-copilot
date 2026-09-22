with source as (
    select * from {{ source('raw', 'fact_transactions') }}
),

deduped as (
    select
        trim(transaction_id) as transaction_id,
        trim(account_id) as account_id,
        round(amount, 2) as amount,
        timestamp,
        lower(trim(merchant_category)) as merchant_category,
        trim(location) as location,
        is_flagged,
        row_number() over (partition by trim(transaction_id) order by timestamp) as _row_num
    from source
    where transaction_id is not null
      and account_id is not null
      and amount >= 0
)

select
    transaction_id,
    account_id,
    amount,
    timestamp,
    merchant_category,
    location,
    is_flagged
from deduped
where _row_num = 1
