with source as (
    select * from {{ source('raw', 'fact_market_prices') }}
),

deduped as (
    select
        upper(trim(ticker)) as ticker,
        price_date,
        round(open, 4) as open,
        round(high, 4) as high,
        round(low, 4) as low,
        round(close, 4) as close,
        volume,
        row_number() over (
            partition by upper(trim(ticker)), price_date
            order by _loaded_at desc
        ) as _row_num
    from source
    where ticker is not null
      and price_date is not null
      -- yfinance occasionally returns a placeholder row with all-null OHLCV
      -- and zero volume (observed once in 250k+ rows, e.g. an unsettled
      -- current-day row) — drop rather than propagate a null close downstream.
      and close is not null
)

select
    ticker,
    price_date,
    open,
    high,
    low,
    close,
    volume
from deduped
where _row_num = 1
