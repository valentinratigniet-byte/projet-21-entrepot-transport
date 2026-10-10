-- Grain de mart_kpi : un seul chiffre par (domaine, kpi, période)
select domaine, kpi, periode, count(*) as n
from {{ ref('mart_kpi') }}
group by all
having count(*) > 1
