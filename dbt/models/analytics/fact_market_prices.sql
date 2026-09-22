select
    p.ticker,
    p.price_date,
    p.open,
    p.high,
    p.low,
    p.close,
    p.volume
from {{ ref('stg_market_prices') }} p
