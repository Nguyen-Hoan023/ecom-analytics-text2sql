select
    antecedent_product_code,
    consequent_product_code
from {{ ref('mart_market_basket_associations') }}
group by
    antecedent_product_code,
    consequent_product_code
having count(*) > 1