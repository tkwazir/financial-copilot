select
    t.transaction_id,
    t.account_id,
    t.amount,
    t.timestamp,
    t.merchant_category,
    t.location,
    t.is_flagged
from {{ ref('stg_transactions') }} t
