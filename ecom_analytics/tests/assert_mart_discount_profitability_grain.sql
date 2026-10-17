select
    category,
    discount_band
from {{ ref('mart_discount_profitability') }}
group by
    category,
    discount_band
having count(*) > 1