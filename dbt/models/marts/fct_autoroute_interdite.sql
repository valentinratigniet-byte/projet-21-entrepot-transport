select a.*, j.evenement_id is not null as est_justifie, j.justification, j.commentaire,
       case when j.evenement_id is not null then 'Justifié' else 'Non justifié' end as justifie
from {{ ref('stg_telem__autoroute_interdite') }} a
left join {{ ref('stg_sp__justif_autoroute') }} j using (evenement_id)
