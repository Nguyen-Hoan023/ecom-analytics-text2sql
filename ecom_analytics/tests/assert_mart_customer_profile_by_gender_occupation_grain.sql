select
    gender,
    occupation
from {{ ref('mart_customer_profile_by_gender_occupation') }}
group by
    gender,
    occupation
having count(*) > 1