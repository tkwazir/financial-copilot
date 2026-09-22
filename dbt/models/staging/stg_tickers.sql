with source as (
    select * from {{ source('raw', 'dim_tickers') }}
),

deduped as (
    select
        upper(trim(ticker)) as ticker,
        trim(company_name) as company_name,
        trim(sector) as sector,
        row_number() over (partition by upper(trim(ticker)) order by ticker) as _row_num
    from source
    where ticker is not null
)

select ticker, company_name, sector
from deduped
where _row_num = 1
