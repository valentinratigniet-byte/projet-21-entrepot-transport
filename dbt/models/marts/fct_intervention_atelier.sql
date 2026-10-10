select o.*, coalesce(f.compte_dans_sous_traitance, true) as compte_dans_sous_traitance,
       o.raison in ('COR', 'DEP') as est_panne
from {{ ref('stg_tms__atelier_ot') }} o
left join {{ ref('ref_famille_atelier') }} f using (famille)
