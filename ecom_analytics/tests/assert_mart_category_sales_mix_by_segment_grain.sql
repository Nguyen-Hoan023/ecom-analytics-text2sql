select
    segment,
    category
from {{ ref('mart_category_sales_mix_by_segment') }}
group by
    segment,
    category
having count(*) > 1