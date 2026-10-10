-- Périodes d'analyse : mois, années (à date pour l'année en cours), et 'total'. Bornées à as_of (= TODAY() figé).
with mois as (
    select distinct date_trunc('month', date_jour) as d0 from {{ ref('dim_date') }}
    where date_jour between date '2023-01-01' and {{ as_of() }}
)
select strftime(d0, '%Y-%m') as periode, 'mois' as type_periode, cast(d0 as date) as d0,
       least(cast(last_day(d0) as date), {{ as_of() }}) as d1
from mois
union all
select cast(year(d0) as varchar), 'annee', make_date(year(d0), 1, 1), least(make_date(year(d0), 12, 31), {{ as_of() }})
from mois group by year(d0)
union all
select 'total', 'total', date '2000-01-01', {{ as_of() }}
