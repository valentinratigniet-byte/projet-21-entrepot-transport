-- Aucun voyage ne doit être perdu ou dupliqué par les imports successifs (CDC + recouvrements)
select count(distinct cast(voyage_id as integer)) - (select count(*) from {{ ref('fct_voyage') }}) as ecart
from {{ source('tms', 'voyage') }}
having ecart <> 0
