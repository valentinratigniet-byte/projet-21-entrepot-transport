select p.periode, count(*) filter (where d.est_jour_ouvre) as jours_ouvres
from {{ ref('int_periode') }} p
join {{ ref('dim_date') }} d on d.date_jour between p.d0 and p.d1
group by p.periode
