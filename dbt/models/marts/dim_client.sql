select c.client_cd, c.client_nom, c.client_ville, c.client_pays,
       i.type_indexation, i.base_pct, i.indice_reference, i.part_gasoil, i.date_reference, i.date_application,
       i.sur_facture, i.a_la_baisse, i.applique, i.commentaire as commentaire_indexation
from {{ ref('stg_tms__client') }} c
left join {{ ref('stg_tms__client_indexation') }} i using (client_cd)
